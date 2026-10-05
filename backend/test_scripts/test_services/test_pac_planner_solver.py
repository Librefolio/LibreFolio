"""Contract tests for the lexicographic SCIP search adapter (Step 3, Stage 3).

`solver.py` takes a `CompiledProgram` (from `compiler.py`) and runs the
cascade `fixed_l2 -> shortfall -> route_priority -> explicit_cost ->
active_order_rows -> canonical tie-breaks` as a genuine lexicographic search:
solve stage *k*, freeze its optimum as a hard constraint, then solve stage
*k+1* on that face. It never decides anything about proof -- `proof.py` does,
reading the statuses this module reports -- and it returns a candidate plus
floating facts that are never authoritative for a number: the only source of
truth for feasibility and for every published figure is the Decimal-exact
`evaluate_exact_candidate` replay.

The keystone here is `test_solver_incumbent_equals_exhaustive_oracle_optimum`
(item B1): a parametrized gate asserting that, for every toy fixture, the
solver's incumbent equals the exhaustive oracle's proven optimum *exactly* --
same decision quanta and the same full lexicographic key (the tuple of exact
objective values in ascending-ordinal order, plus `canonical_tie_quanta`).
The exhaustive oracle is a test instrument
(`backend/test_scripts/test_services/_pac_exhaustive_oracle.py`, with no
production role since D-X1): it has zero SCIP dependency and enumerates the
whole discrete domain, so it is independent ground truth. Adding a fixture to
`_ORACLE_AGREEMENT_FIXTURES` automatically extends the gate. From here on
"solver green" means "oracle-agreement green".

Scope, as everywhere else in this package: PAC `proportional` policy,
`primary` purpose only. Every fixture is small enough for the oracle to
enumerate in a fraction of a second (the coarse funding/FX case, which is the
fixture that caught the Step3 §16.11 HALF_UP ledger defect, has 585
candidates, the QX1-a example 501, the exact FX-credit tie case 240; the rest
are in the tens). Fixtures with a *binding* fee cap are no longer excluded
from the agreement gate: since QX1-a (found 2026-09-24) the fee epigraph
models the cap exactly (`constraints.py`), so a capped route that makes the
solver prefer another candidate is a disagreement like any other, and the
gate polices it.

These are pure in-process tests (`isolation="pure"`): no server, no database,
no clock assertions, no network. Three ready-made scenario fixtures are imported
from the sibling oracle suite (`_two_asset_pac_scenario`,
`_coarse_funding_fx_scenario`, `_credit_tie_fx_scenario`), exactly the way that
module imports its own primitives from `test_pac_planner_evaluator.py`.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import CandidateActionVector, ExactEvaluation, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.solver import (
    DEFAULT_SOLVER_TIME_BUDGET_SECONDS,
    ENGINE_NAME,
    SolverRunResult,
    SolverStageReport,
    solve_policy_program,
)
from backend.test_scripts.test_services._pac_exhaustive_oracle import run_exhaustive_oracle
from backend.test_scripts.test_services.test_pac_planner_evaluator import ZERO, R, _pac_scenario
from backend.test_scripts.test_services.test_pac_planner_oracle import _coarse_funding_fx_scenario, _credit_tie_fx_scenario, _two_asset_pac_scenario

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
    is an independent re-implementation of the same key the exhaustive oracle
    uses -- it does not import the oracle's `_lexicographic_key`.
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
    """A proportional fee with a floor but *no* cap, so only the floor and
    linear rows of the fee epigraph are in play (the capped shapes are the
    QX1-a fixtures below) and `explicit_cost` genuinely discriminates between
    candidates.
    """
    return _pac_scenario(price=R(10), fee_rate=R(1, 10), fee_floor=R(5), fee_cap=None, route_cap=R(6), cash=R(1000))


def _execution_margin_scenario() -> ExactPlannerScenario:
    """A BUY execution margin, so `explicit_cost`'s execution-margin-loss term
    is nonzero and the cascade has to weigh it.
    """
    return _pac_scenario(price=R(10), margin=R(1, 20), route_cap=R(6))


def _fee_floor_above_linear_upper_scenario() -> ExactPlannerScenario:
    """X2 (found 2026-09-24): 0.19% with a EUR1.50 minimum on EUR100 of cash.
    At the route's own upper bound (10 units, EUR100) the linear fee is only
    EUR0.19, and the fee epigraph sized its Big-M from `rate *
    notional_upper` alone -- so the minimum made the whole model infeasible,
    order on or off, while the exact replay buys 9 units (EUR90 + EUR1.50).
    """
    return _pac_scenario(price=R(10), cash=R(100), fee_rate=R(19, 10000), fee_floor=R(3, 2), route_cap=R(100))


def _small_route_cap_fee_floor_scenario() -> ExactPlannerScenario:
    """X2 through a small per-title cap instead of a small budget: EUR10000 of
    cash, but a 20-unit cap keeps `notional_upper` at EUR200, and 0.19% of it
    (EUR0.38) is still below the EUR1.50 minimum.
    """
    return _pac_scenario(price=R(10), cash=R(10000), fee_rate=R(19, 10000), fee_floor=R(3, 2), route_cap=R(20))


def _flat_minimum_fee_scenario() -> ExactPlannerScenario:
    """X2 in a common real-world shape: a flat EUR2 minimum on a zero rate,
    so `rate * notional_upper` is zero and any minimum at all sits above it.
    """
    return _pac_scenario(price=R(10), cash=R(100), fee_floor=R(2), route_cap=R(100))


def _fee_cap_binds_scenario() -> ExactPlannerScenario:
    """QX1-a (found 2026-09-24): 10% capped at EUR1 on EUR95 of cash. The
    exact replay buys 9 units (EUR90 + EUR1); the fee epigraph ignored the
    cap and priced them at the linear EUR9, EUR99 against EUR95, so the
    solver stopped at 8.
    """
    return _pac_scenario(price=R(10), cash=R(95), fee_rate=R(1, 10), fee_cap=R(1), route_cap=R(100))


def _fee_fixed_floor_cap_scenario() -> ExactPlannerScenario:
    """QX1-a with every term of the fee in play: EUR0.50 fixed plus 10% with a
    EUR0.50 minimum, capped at EUR1.50, on EUR97 of cash. The replay buys 9
    units (EUR90 + EUR2); the model priced them at EUR0.50 + EUR9, EUR99.50
    against EUR97, and stopped at 8.
    """
    return _pac_scenario(price=R(10), cash=R(97), fixed_fee=R(1, 2), fee_rate=R(1, 10), fee_floor=R(1, 2), fee_cap=R(3, 2), route_cap=R(100))


def _fee_cap_binds_qx1a_example_scenario() -> ExactPlannerScenario:
    """The QX1-a example the developer approved: EUR50,050 at EUR100 a unit,
    0.19% capped at EUR18. The replay buys 500 units (EUR50,000 + EUR18); the
    model priced them at the linear EUR95, EUR50,095 against EUR50,050, and
    stopped at 499. 501 candidates, still a fraction of a second for the
    oracle.
    """
    return _pac_scenario(price=R(100), cash=R(50050), fee_rate=R(19, 10000), fee_cap=R(18), route_cap=R(1000))


def _fee_cap_never_binds_scenario() -> ExactPlannerScenario:
    """Control for the QX1-a fixtures: the EUR95 and the 10% of
    `fee_cap_binds`, but a EUR50 cap the route never reaches (the linear fee
    tops out at EUR9 on 9 units). Model and replay agree on 8 units (EUR80 +
    EUR8) whether the cap is modelled or not.
    """
    return _pac_scenario(price=R(10), cash=R(95), fee_rate=R(1, 10), fee_cap=R(50), route_cap=R(100))


def _exact_credit_tie_fx_scenario() -> ExactPlannerScenario:
    """Option A (R13): an exact FX-credit tie decides the optimum. 5 EUR at
    3/2 with no spread is exactly 7.5 USD, a HALF_UP tie that posts 8, and
    those 8 USD buy the 4th unit at 2 USD; without the round-up only 3 fit.
    The oracle suite derives that optimum by hand. Zero fee and a whole-USD
    price: a credit tie is reachable, no debit tie is. 240 candidates.
    """
    return _credit_tie_fx_scenario(price=R(2), cap=R(4))


_ORACLE_AGREEMENT_FIXTURES = [
    pytest.param(_two_asset_pac_scenario, id="two_asset_pac"),
    pytest.param(_coarse_funding_fx_scenario, id="coarse_funding_fx"),  # the fixture that caught the Step3 §16.11 defect
    pytest.param(_single_buy_scenario, id="single_buy"),
    pytest.param(_proportional_fee_no_cap_scenario, id="proportional_fee_no_cap"),
    pytest.param(_execution_margin_scenario, id="execution_margin"),
    # X2: fee minimum above `rate * notional_upper`. Every amount is whole cents, so no HALF_UP tie is reachable.
    pytest.param(_fee_floor_above_linear_upper_scenario, id="fee_floor_above_linear_upper"),
    pytest.param(_small_route_cap_fee_floor_scenario, id="small_route_cap_fee_floor"),
    pytest.param(_flat_minimum_fee_scenario, id="flat_minimum_fee"),
    # QX1-a: a fee cap that binds inside the route's range. Every amount is whole cents, so no HALF_UP tie is reachable.
    pytest.param(_fee_cap_binds_scenario, id="fee_cap_binds"),
    pytest.param(_fee_fixed_floor_cap_scenario, id="fee_fixed_floor_cap"),
    pytest.param(_fee_cap_binds_qx1a_example_scenario, id="fee_cap_binds_qx1a_example"),
    pytest.param(_fee_cap_never_binds_scenario, id="fee_cap_never_binds"),  # control: a cap the route never reaches
    # Option A: an exact FX-credit tie is reachable and no debit tie is, so the optima must coincide exactly. The
    # allowance for SCIP beating the oracle covers DEBIT ties only (X3 rejected): at a credit tie the model may post
    # either neighbour, but whatever the lower one admits the true round-up admits too, so the feasible sets agree.
    pytest.param(_exact_credit_tie_fx_scenario, id="credit_tie_fx"),
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
    settings that survive the whole run plus the overall `time_budget`, and
    the tolerances read back from SCIP itself (`feasibility == 1e-6`,
    `integrality == 1e-9` by default), not values this module made up.

    `limits/time` is deliberately *not* among them: it is re-armed before
    every stage with that stage's remaining slice, so a single top-level
    value would report a configuration no stage ever ran with.
    """
    _view, result = _run(_two_asset_pac_scenario())

    assert result.engine == ENGINE_NAME == "SCIP"
    assert result.version  # non-empty engine version string

    setting_by_name = {setting.name: setting.value for setting in result.settings}
    assert setting_by_name.get("time_budget") == f"{DEFAULT_SOLVER_TIME_BUDGET_SECONDS:g}"
    # Re-adding a top-level `limits/time` would resurrect the false witness:
    # no stage ever runs with the total budget, only with its own slice.
    assert "limits/time" not in setting_by_name
    assert "limits/nodes" not in setting_by_name  # no node limit was requested

    assert result.tolerances.feasibility == 1e-6
    assert result.tolerances.integrality == 1e-9


def test_solver_node_limit_is_reported_in_settings() -> None:
    """Passing `node_limit` applies `limits/nodes` and records it as evidence
    alongside the overall `time_budget`.
    """
    _view, result = _run(_two_asset_pac_scenario(), node_limit=1)

    setting_by_name = {setting.name: setting.value for setting in result.settings}
    assert setting_by_name.get("limits/nodes") == "1"
    assert setting_by_name.get("time_budget") == f"{DEFAULT_SOLVER_TIME_BUDGET_SECONDS:g}"


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
# B5: the first-stage infeasible verdict, and nothing after it
# --------------------------------------------------------------------------


def test_infeasible_scenario_reports_only_the_first_global_stage_as_infeasible() -> None:
    """A genuinely infeasible scenario (`ORDER_REQUIRED_MIN` above the route's
    reachable cap -- the same construction the oracle suite proves infeasible)
    closes the first, still-global stage `infeasible`: SCIP's verdict on the
    scenario itself, and the only stage that can deliver one.

    The run reports exactly that: `reported_infeasible`, one stage -- ordinal
    1, `global`, `infeasible` -- with no primal, no dual and no gap, because an
    infeasible solve has none, and nothing after it, because no face exists
    for a later stage to run on (no `not_reached` rows). Deciding that the
    verdict is a proof is `proof.py`'s job, not this module's.

    The exhaustive oracle corroborates, independently of SCIP, that the
    scenario has no feasible candidate, so the verdict is not a false claim.
    """
    scenario = _pac_scenario(required=R(5), route_cap=R(3))
    view, result = _run(scenario)

    assert result.outcome == "reported_infeasible"
    assert result.candidate is None
    assert result.anomaly is None
    assert result.finished_stage_count == 0

    assert len(result.stages) == 1, result.stages
    (stage,) = result.stages
    first_objective_code = next(objective.code for objective in view.objectives if objective.ordinal == 1)
    assert (stage.stage, stage.objective_code, stage.ordinal, stage.scope) == (first_objective_code, first_objective_code, 1, "global")
    assert (stage.status, stage.scip_status) == ("infeasible", "infeasible")
    assert (stage.primal, stage.dual, stage.absolute_gap, stage.relative_gap) == (None, None, None, None)
    assert not any(report.scip_status == "not_reached" for report in result.stages)

    # The verdict is corroborated by the exhaustive oracle -- it is not a
    # false infeasibility claim.
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
