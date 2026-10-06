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

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction

import pytest
from pyscipopt import Model as ScipModel

from backend.app.services.pac_allocator import compiler as compiler_module
from backend.app.services.pac_allocator import planner_report as PR
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import CandidateActionVector, ExactEvaluation, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.proof import OptimalProvenConclusion, conclude_with_solver
from backend.app.services.pac_allocator.solver import (
    DEFAULT_SOLVER_TIME_BUDGET_SECONDS,
    ENGINE_NAME,
    SolverRunResult,
    SolverStageReport,
    solve_policy_program,
)
from backend.test_scripts.test_services._pac_exhaustive_oracle import run_exhaustive_oracle
from backend.test_scripts.test_services._pac_synthetic_requests import V, make, scenario_of
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


# --------------------------------------------------------------------------
# Robustness: a stage pin never sits below the exact value, SCIP's bounds are
# checked against the exact replay, a limit leaves the tail running, and
# stage 1 keeps a reserve to resume on.
# Solver robustness slice, 2026-10.
# --------------------------------------------------------------------------

_INTEGRAL_OBJECTIVE_CODES = frozenset({"route_priority", "active_order_rows"})
_BOUND_TOLERANCE = Fraction(1, 10**6)


def _argument(args: tuple, kwargs: dict, position: int, keyword: str, default: object = None) -> object:
    """One call argument, whether it came by position or by keyword."""
    if keyword in kwargs:
        return kwargs[keyword]
    return args[position] if len(args) > position else default


@dataclass
class _ScipLever:
    """What one instrumented SCIP run did, and how the lever bends it.

    Nothing is counted before `arm()`, called once `compile_policy_program`
    has returned: the compiler's own calls are not part of the cascade. `log`
    holds the mutating calls only, in call order; the getters are bent, never
    logged. The stage index is the number of `setObjective` calls minus one.

    `pins` maps a code to the right-hand side SCIP stores for `pin:<code>`.
    That is the pin itself only for `fixed_l2`, whose expression has no
    constant term: SCIP moves a constant to the right (on `two_asset_pac`,
    `shortfall`'s `_rhs` is its pin minus 100).
    """

    target_stage: int | None = None
    shift: Callable[[float], float] | None = None
    fake_optimize_calls: frozenset[int] = frozenset()
    armed: bool = False
    objectives: int = 0
    optimize_calls: int = 0
    log: list[tuple] = field(default_factory=list)
    pins: dict[str, float] = field(default_factory=dict)

    def arm(self) -> None:
        self.armed = True

    def record(self, *entry: object) -> None:
        if self.armed:
            self.log.append(entry)

    @property
    def stage_index(self) -> int:
        return self.objectives - 1

    def bends_bounds(self) -> bool:
        return self.shift is not None and self.stage_index == self.target_stage

    def fakes_a_limit(self) -> bool:
        """From the end of a listed `optimize()` call to the start of the next."""
        return self.optimize_calls in self.fake_optimize_calls


class _LeverModel(ScipModel):
    """A `pyscipopt.Model` that reports to a `_ScipLever` and obeys it.

    The Cython `Model`'s instance methods are read-only, so a subclass is the
    only way in. Every override hands the full `*args, **kwargs` to `super()`
    and returns its result: a lever that bends nothing changes nothing SCIP
    does. `_install_scip_lever` binds `_lever` on a per-test subclass.
    """

    _lever: _ScipLever

    def setObjective(self, *args: object, **kwargs: object) -> object:
        if self._lever.armed:
            self._lever.objectives += 1
            self._lever.record("setObjective", self._lever.stage_index)
        return super().setObjective(*args, **kwargs)

    def optimize(self, *args: object, **kwargs: object) -> object:
        if self._lever.armed:
            self._lever.optimize_calls += 1
            self._lever.record("optimize", self._lever.optimize_calls)
        return super().optimize(*args, **kwargs)

    def freeTransform(self, *args: object, **kwargs: object) -> object:
        self._lever.record("freeTransform")
        return super().freeTransform(*args, **kwargs)

    def setParam(self, *args: object, **kwargs: object) -> object:
        self._lever.record("setParam", _argument(args, kwargs, 0, "name"), _argument(args, kwargs, 1, "value"))
        return super().setParam(*args, **kwargs)

    def addCons(self, *args: object, **kwargs: object) -> object:
        name = str(_argument(args, kwargs, 1, "name", ""))
        if self._lever.armed and name.startswith("pin:"):
            self._lever.pins[name[4:]] = _argument(args, kwargs, 0, "cons")._rhs
            self._lever.record("addCons", name)
        return super().addCons(*args, **kwargs)

    def getPrimalbound(self, *args: object, **kwargs: object) -> object:
        value = super().getPrimalbound(*args, **kwargs)
        return self._lever.shift(value) if self._lever.bends_bounds() else value

    def getDualbound(self, *args: object, **kwargs: object) -> object:
        value = super().getDualbound(*args, **kwargs)
        return self._lever.shift(value) if self._lever.bends_bounds() else value

    def getStatus(self, *args: object, **kwargs: object) -> object:
        return "timelimit" if self._lever.fakes_a_limit() else super().getStatus(*args, **kwargs)

    def getNSols(self, *args: object, **kwargs: object) -> object:
        return 0 if self._lever.fakes_a_limit() else super().getNSols(*args, **kwargs)


def _install_scip_lever(monkeypatch: pytest.MonkeyPatch, **settings: object) -> _ScipLever:
    """Make `compile_policy_program` build lever-instrumented models; return the lever."""
    lever = _ScipLever(**settings)

    class LeverModel(_LeverModel):
        _lever = lever

    monkeypatch.setattr(compiler_module, "Model", LeverModel)
    return lever


def _lever_run(monkeypatch: pytest.MonkeyPatch, scenario: ExactPlannerScenario, **settings: object) -> tuple[ExactPolicyView, SolverRunResult, _ScipLever]:
    """Compile a fresh instrumented model, arm the lever, run the cascade on a 30 s budget."""
    lever = _install_scip_lever(monkeypatch, **settings)
    view = build_exact_policy_view(scenario, purpose="primary")
    program = compile_policy_program(scenario, view)
    assert isinstance(program.model, _LeverModel), "the lever must instrument the model the solver runs"
    lever.arm()
    return view, solve_policy_program(program, time_budget_seconds=30.0), lever


def _objective_codes(view: ExactPolicyView) -> tuple[str, ...]:
    return tuple(objective.code for objective in sorted(view.objectives, key=lambda objective: objective.ordinal))


def _oracle_best(scenario: ExactPlannerScenario, view: ExactPolicyView) -> tuple[CandidateActionVector, dict[str, object]]:
    """The oracle's optimum, and its exact objective values by code."""
    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.best_candidate is not None
    assert oracle.best_evaluation is not None
    values, _tie_quanta = _lexicographic_key(view, oracle.best_evaluation)
    return oracle.best_candidate, dict(zip(_objective_codes(view), values, strict=True))


def _time_limits(lever: _ScipLever) -> list[tuple[int, float]]:
    """`(log index, value)` of every `limits/time` the run handed SCIP, in order."""
    return [(index, entry[2]) for index, entry in enumerate(lever.log) if entry[:2] == ("setParam", "limits/time")]


def _bound_contradiction(stage: SolverStageReport, exact: Fraction, target_count: int) -> str | None:
    """SCIP's bounds for one finished named stage against the exact value of its objective.

    Integral stages: `ceil(dual - 1e-6) <= v <= round(primal)`. Continuous
    stages: `dual - tol <= v <= primal + tol`, `tol = 1e-6 * max(1, |bound|)`,
    widened by `n * 1e-6` for `fixed_l2` (`n` target weights). `None` when
    they agree.
    """
    assert stage.primal is not None and stage.dual is not None, stage
    if stage.objective_code in _INTEGRAL_OBJECTIVE_CODES:
        low, high = Fraction(math.ceil(Fraction(stage.dual) - _BOUND_TOLERANCE)), Fraction(round(stage.primal))
    else:
        primal, dual = Fraction(stage.primal), Fraction(stage.dual)
        widening = target_count * _BOUND_TOLERANCE if stage.objective_code == "fixed_l2" else Fraction(0)
        low = dual - _BOUND_TOLERANCE * max(1, abs(dual)) - widening
        high = primal + _BOUND_TOLERANCE * max(1, abs(primal)) + widening
    if low <= exact <= high:
        return None
    return f"{stage.objective_code}: exact {exact} outside [{float(low)!r}, {float(high)!r}] (primal {stage.primal!r}, dual {stage.dual!r})"


def test_stage_pin_never_sits_below_the_exact_value_of_its_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    """A finished stage is pinned at `max(primal, exact)`, `exact` being its
    own candidate's replayed value: SCIP's float may not cut off the optimum.

    The lever makes SCIP report `fixed_l2` a thousandth low (499.5 for a true
    500). A pin at that primal leaves the next face empty; a pin at the exact
    value lets the cascade run on to the oracle's plan. The proof is not
    asserted: the bound check is right to flag the shifted primal.
    """
    scenario = _two_asset_pac_scenario()
    view, result, lever = _lever_run(monkeypatch, scenario, target_stage=0, shift=lambda value: value * 0.999)
    best_candidate, best = _oracle_best(scenario, view)
    assert (result.stages[0].stage, best["fixed_l2"]) == ("fixed_l2", R(500)), "PREMISE: stage 1 is fixed_l2, exact optimum 500"

    assert "fixed_l2" in lever.pins, lever.log
    assert Fraction(lever.pins["fixed_l2"]) >= 500, f"fixed_l2 pinned at {lever.pins['fixed_l2']!r}, below its exact value 500"
    broken = [(stage.stage, stage.status, stage.scip_status) for stage in result.stages if stage.status == "infeasible" or stage.scip_status in {"infeasible", "not_reached"}]
    assert broken == []
    assert result.candidate is not None
    assert _quanta(result.candidate) == _quanta(best_candidate)


def test_an_integral_stage_scip_misreports_is_pinned_exactly_and_never_proven(monkeypatch: pytest.MonkeyPatch) -> None:
    """An integral stage is pinned at `max(round(primal), exact)`, and a
    primal the exact replay contradicts is an anomaly that withholds the proof.

    The lever makes SCIP report `route_priority` one unit low (primal and
    dual). The order of the assertions is the order of the fixes: the exact
    pin lets every stage finish (1) but alone would still prove the run
    optimal; only the bound check raises the anomaly (2) that refuses the
    proof (3). Every stage did finish, so the stop is `completed` (4).
    """
    scenario = _two_asset_pac_scenario()
    view, result, _lever = _lever_run(monkeypatch, scenario, target_stage=2, shift=lambda value: value - 1)
    objective_codes = list(_objective_codes(view))
    _best_candidate, best = _oracle_best(scenario, view)
    assert objective_codes[2] == "route_priority", f"PREMISE: stage 3 is route_priority, got {objective_codes}"
    assert best["route_priority"] >= 1, f"PREMISE: the oracle's best route_priority is at least 1, got {best['route_priority']}"

    assert all(stage.status == "finished" for stage in result.stages), [(stage.stage, stage.status, stage.scip_status) for stage in result.stages]
    assert result.anomaly is not None
    conclusion = conclude_with_solver(result, objective_codes=objective_codes, published=result.candidate)
    assert not isinstance(conclusion, OptimalProvenConclusion), conclusion
    assert PR.build_stop_reason(result) == "completed"


@pytest.mark.parametrize("build_scenario", _ORACLE_AGREEMENT_FIXTURES)
def test_finished_stage_bounds_bracket_the_exact_replay(build_scenario: Callable[[], ExactPlannerScenario]) -> None:
    """On every oracle-agreement fixture, SCIP's dual and primal for each
    finished named stage bracket the exact value of that stage's objective on
    the published candidate, and the run carries no anomaly.

    The false-positive guard of the bound check: an honest SCIP run must pass
    it untouched, so the check can never withhold a proof SCIP earned. Tie
    stages carry no named objective and are not checked.
    """
    scenario = build_scenario()
    view, result = _run(scenario)
    assert result.outcome == "incumbent"
    assert result.candidate is not None
    evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    assert (evaluation.candidate_valid, evaluation.feasible) == (True, True)

    ref_id_by_code = {objective.code: objective.ref_id for objective in view.objectives}
    value_by_ref_id = {objective.ref_id: objective.value for objective in evaluation.objectives}
    named = [stage for stage in result.stages if stage.status == "finished" and not stage.stage.startswith("tie:")]
    assert named, [(stage.stage, stage.status) for stage in result.stages]
    exact_values = [value_by_ref_id[ref_id_by_code[stage.objective_code]] for stage in named]
    contradictions = [_bound_contradiction(stage, Fraction(exact.numerator, exact.denominator), len(scenario.target_weights)) for stage, exact in zip(named, exact_values, strict=True)]
    assert [item for item in contradictions if item is not None] == []
    assert result.anomaly is None


def test_a_limited_first_stage_leaves_the_tail_running_on_its_face() -> None:
    """When stage 1 stops on a limit holding a candidate, its face is pinned
    and every later stage still runs: `unfinished`, on the incumbent face,
    with its own SCIP observations -- never `not_reached`.

    `node_limit=1` stops stage 1 of the synthetic 5x2 grid at `nodelimit`
    with a candidate. The tail may only keep or improve that candidate
    lexicographically (`<=`: a strict gain depends on SCIP's heuristics), and
    the node limit that stopped stage 1 is the stop.
    """
    scenario, view = scenario_of(make(**V["5x2"]))
    assert _objective_codes(view) == ("fixed_l2", "shortfall", "route_priority", "explicit_cost", "active_order_rows"), f"PREMISE: {_objective_codes(view)}"
    result = solve_policy_program(compile_policy_program(scenario, view), time_budget_seconds=30.0, node_limit=1)

    assert (result.stages[0].status, result.stages[0].scip_status) == ("unfinished", "nodelimit"), result.stages[0]
    for stage in result.stages[1:]:
        observed = (stage.stage, stage.status, stage.scope, stage.scip_status, stage.primal)
        assert stage.status == "unfinished", observed
        assert stage.scope == "incumbent_face", observed
        assert stage.scip_status != "not_reached", observed
        assert stage.primal is not None, observed

    assert result.outcome == "incumbent"
    assert result.candidate is not None
    evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    assert (evaluation.candidate_valid, evaluation.feasible) == (True, True)
    assert result.anomaly is None
    values, _tie_quanta = _lexicographic_key(view, evaluation)
    assert values <= (R(17425, 4), R(65, 2), R(13), R(3187, 400), R(8)), values
    assert PR.build_stop_reason(result) == "node_limit"


def test_stage_one_reserve_is_a_tenth_of_the_budget_capped_at_three_seconds() -> None:
    """Stage 1 keeps `min(3 s, 10% of the budget)` back, to resume on."""
    from backend.app.services.pac_allocator.solver import stage_one_reserve_seconds  # noqa: PLC0415 — added by S3

    assert stage_one_reserve_seconds(30.0) == 3.0
    assert stage_one_reserve_seconds(3.5) == pytest.approx(0.35)


def test_stage_one_time_limit_holds_the_reserve_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stage 1's `limits/time` is the remaining budget minus the reserve:
    about 27 s of a 30 s budget, never the whole 30.
    """
    _view, _result, lever = _lever_run(monkeypatch, _two_asset_pac_scenario())
    time_limits = _time_limits(lever)
    assert time_limits, lever.log
    assert 26.0 <= time_limits[0][1] <= 27.0, time_limits


def test_stage_one_resumes_once_on_its_reserve_when_its_limit_left_no_solution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stage 1 ending on a limit with no solution is resumed once on the same
    transformed problem: `limits/time` raised by the reserve, then a second
    `optimize()`, with no `freeTransform` and no new objective in between.

    The lever fakes the limit after the first `optimize()` only. SCIP really
    solved it, and resuming a solved model keeps its solutions, so the resume
    surfaces the incumbent.
    """
    _view, result, lever = _lever_run(monkeypatch, _two_asset_pac_scenario(), fake_optimize_calls=frozenset({1}))

    assert ("optimize", 2) in lever.log, f"stage 1 was not resumed: {lever.log}"
    first_call, second_call = lever.log.index(("optimize", 1)), lever.log.index(("optimize", 2))
    first_limit = [value for index, value in _time_limits(lever) if index < first_call][-1]
    between = lever.log[first_call + 1 : second_call]
    assert [entry[:2] for entry in between] == [("setParam", "limits/time")], between
    assert between[0][2] == pytest.approx(first_limit + 3.0, abs=0.5), (first_limit, between)
    assert result.outcome == "incumbent"


def test_stage_one_resume_that_finds_nothing_is_still_no_incumbent(monkeypatch: pytest.MonkeyPatch) -> None:
    """The resume happens once: still no solution after it is `no_incumbent`,
    exactly as without a resume, after two `optimize()` calls in total.
    """
    _view, result, lever = _lever_run(monkeypatch, _two_asset_pac_scenario(), fake_optimize_calls=frozenset({1, 2}))

    assert result.outcome == "no_incumbent"
    assert lever.optimize_calls == 2, lever.log
