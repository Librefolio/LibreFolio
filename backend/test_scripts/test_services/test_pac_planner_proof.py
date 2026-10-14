"""Contract tests for the proof-semantics layer of the PAC/Rebalancer planner.

`proof.py` decides the third of three independent dimensions of a ready
result: incumbent validation is `evaluator.py`'s job, the floating solver
report is `solver.py`'s, and the *conclusion about the discrete domain* is
this module's — and only this module's.

Since D-X1 SCIP is the only production search engine, and its own status is
the proof. The properties these tests lock down:

* **The proof is SCIP's status, and one function reads it.**
  `conclude_with_solver` is the module's only public callable:
  `optimal_proven` when every stage of the cascade — the canonical `tie:*`
  stages included — closed `optimal` with no anomaly; `infeasibility_proven`
  when the run is exactly the first, still-global stage closed `infeasible`;
  `not_proven` for everything else: a limit, an anomaly, any other shape.
* **A proof is never transferred to a candidate SCIP did not return.** An
  optimum is proven only for SCIP's own candidate — publish another, or none,
  and the conclusion downgrades; an infeasibility only while SCIP returned
  nothing and nothing is published.
* **Witnesses are sealed.** A `SolverStatusWitnessFacts` built outside
  `conclude_with_solver` raises `ProofForgeryError`, checked for its exact
  type (a guard that throws the wrong type is worse than no guard), and so
  does a run that would prove something about objectives other than the ones
  the caller named.
* `UnprovenConclusion` is a frozen dataclass whose `kind` is a single-valued
  `Literal`: it has no field that could ever hold a proof.

The runs are real (`build_exact_policy_view` -> `compile_policy_program` ->
`solve_policy_program`) on the sibling suites' scenario fixtures, and each
fixture confirms its run's state before anything is concluded from it. The
shapes a healthy SCIP does not produce on demand — a tie stage cut by a
limit, an infeasible stage on a later ordinal, an anomaly — are
`dataclasses.replace` variants of those real runs, each changing one named
fact, so every downgrade is attributable to the fact the test names.

These are pure in-process tests (`isolation="pure"`): no server, no database,
no clock assertions, no sleeps, no network. SCIP floats are never compared
exactly: a perfect run is recognised by `status == "finished"` and
`scip_status == "optimal"`, never by a gap equality.
"""

from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Callable

import pytest

from backend.app.services.pac_allocator import proof
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view
from backend.app.services.pac_allocator.models import CandidateActionVector, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.proof import (
    NOT_PROVEN_REASON,
    InfeasibilityProvenConclusion,
    OptimalProvenConclusion,
    ProofForgeryError,
    SolverStatusWitnessFacts,
    UnprovenConclusion,
    conclude_with_solver,
)
from backend.app.services.pac_allocator.solver import SolverRunResult, SolverStageReport, solve_policy_program
from backend.test_scripts.test_services.test_pac_planner_evaluator import R, _candidate, _pac_scenario
from backend.test_scripts.test_services.test_pac_planner_oracle import _two_asset_pac_scenario

# The one legitimate reach into a module-private. A *valid* sealed witness can
# only be cut with the very seal that production code is structurally forbidden
# from touching, so the forgery cases that must get past the seal to reach the
# guard behind it read it here. That production code cannot reach this object
# is exactly the property the seal cases assert; a test may, precisely because
# it is probing the witness's own guards rather than manufacturing proof
# evidence at a call site.
_SEAL = proof._WITNESS_SEAL

# Canonical tie-break stages carry a decision id, not an objective code: they
# must close like every other stage, but no witness names them.
_TIE_STAGE_PREFIX = "tie:"

# Everything `proof.py` exports today. An export list that grows again is a
# road to a proof that bypasses the one function reading SCIP's status.
_PUBLIC_API = (
    "NOT_PROVEN_REASON",
    "InfeasibilityProvenConclusion",
    "OptimalProvenConclusion",
    "PlanConclusion",
    "ProofForgeryError",
    "ProvenConclusion",
    "SolverStatusWitnessFacts",
    "UnprovenConclusion",
    "conclude_with_solver",
)

# The shape of a real anomaly: the solver's own message for an unexpected status.
_ANOMALY = "stage 'shortfall' (ordinal 2) ended with unexpected solver status 'unknown'"


# --------------------------------------------------------------------------
# Real runs (never hand-built stubs), and one-fact variants of them
# --------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Run:
    """A real SCIP run, the view it ran on, and that view's objective codes in
    cascade order — exactly what the planner hands `conclude_with_solver`."""

    view: ExactPolicyView
    result: SolverRunResult
    objective_codes: tuple[str, ...]


def _real_run(scenario: ExactPlannerScenario, **kwargs: object) -> _Run:
    """Compile and solve a fresh model — a genuine `SolverRunResult`, never a
    stub. A fresh `compile_policy_program` per call keeps every solve on its
    own `Model` (the PySCIPOpt reuse trap the sibling suites document).
    """
    view = build_exact_policy_view(scenario, purpose="primary")
    result = solve_policy_program(compile_policy_program(scenario, view), **kwargs)
    objective_codes = tuple(ref.code for ref in sorted(view.objectives, key=lambda ref: ref.ordinal))
    return _Run(view=view, result=result, objective_codes=objective_codes)


def _is_tie(stage: SolverStageReport) -> bool:
    return stage.objective_code.startswith(_TIE_STAGE_PREFIX)


def _only_stage(result: SolverRunResult) -> SolverStageReport:
    (stage,) = result.stages
    return stage


def _with_stage(result: SolverRunResult, stage_id: str, **changes: object) -> SolverRunResult:
    """`result` with the one stage whose id is `stage_id` changed.

    ``finished_stage_count`` is recounted so the variant stays a coherent run;
    nothing else moves.
    """
    assert [stage.stage for stage in result.stages].count(stage_id) == 1, stage_id
    stages = tuple(dataclasses.replace(stage, **changes) if stage.stage == stage_id else stage for stage in result.stages)
    return dataclasses.replace(result, stages=stages, finished_stage_count=sum(stage.status == "finished" for stage in stages))


def _second_stage_not_reached(run: _Run) -> SolverStageReport:
    """The row the solver used to append after an infeasible first stage: the
    second objective, on the incumbent face, never reached."""
    code = run.objective_codes[1]
    return dataclasses.replace(_only_stage(run.result), stage=code, objective_code=code, ordinal=2, status="unfinished", scope="incumbent_face", scip_status="not_reached")


def _perturbed(candidate: CandidateActionVector, decision_id: str) -> CandidateActionVector:
    """`candidate` with one decision moved by one quantum, staying nonnegative.

    Only the quanta change — not the candidate id, not the view id — so a
    downgrade can be attributed to the plan alone.
    """
    decisions = tuple(dataclasses.replace(decision, quanta=decision.quanta - 1 if decision.quanta > 0 else decision.quanta + 1) if decision.decision_id == decision_id else decision for decision in candidate.decisions)
    return dataclasses.replace(candidate, decisions=decisions)


@pytest.fixture(scope="module")
def perfect_run() -> _Run:
    """SCIP closes every stage of `_two_asset_pac_scenario` optimal, the tie-breaks included."""
    run = _real_run(_two_asset_pac_scenario())
    result = run.result
    assert (result.outcome, result.anomaly) == ("incumbent", None)
    assert result.candidate is not None and result.candidate.decisions
    assert result.stages and all(stage.status == "finished" and stage.scip_status == "optimal" for stage in result.stages), result.stages
    assert any(_is_tie(stage) for stage in result.stages), "the perfect run must include canonical tie-break stages"
    return run


@pytest.fixture(scope="module")
def infeasible_run() -> _Run:
    """A required minimum of 50 on a route capped at 10: SCIP closes the first, global stage infeasible."""
    run = _real_run(_pac_scenario(required=R(50), route_cap=R(10)))
    result = run.result
    assert (result.outcome, result.anomaly, result.candidate) == ("reported_infeasible", None, None)
    assert [(stage.ordinal, stage.scope, stage.status, stage.scip_status) for stage in result.stages] == [(1, "global", "infeasible", "infeasible")]
    assert len(run.objective_codes) >= 2, "the view must name later objectives the infeasible run never reached"
    return run


@pytest.fixture(scope="module")
def limited_run() -> _Run:
    """No time at all: SCIP closes no stage, so nothing is found."""
    run = _real_run(_two_asset_pac_scenario(), time_budget_seconds=0.0)
    result = run.result
    assert (result.outcome, result.anomaly, result.candidate) == ("no_incumbent", None, None)
    assert result.stages and all(stage.status == "unfinished" for stage in result.stages), result.stages
    return run


# --------------------------------------------------------------------------
# 1. The public surface
# --------------------------------------------------------------------------


def test_not_proven_reason_is_the_single_phase_one_wire_code() -> None:
    assert NOT_PROVEN_REASON == "allocation.exact_proof_not_established"
    assert UnprovenConclusion().reason_code == NOT_PROVEN_REASON


def test_public_surface_is_exactly_the_solver_status_api() -> None:
    """`proof.py` exports today's API and nothing more, and
    `conclude_with_solver` is its only public callable: there is no second
    road to a proof.
    """
    assert sorted(proof.__all__) == sorted(_PUBLIC_API)
    assert all(hasattr(proof, name) for name in proof.__all__)
    public_functions = {name for name, obj in inspect.getmembers(proof, inspect.isfunction) if obj.__module__ == proof.__name__ and not name.startswith("_")}
    assert public_functions == {"conclude_with_solver"}


# --------------------------------------------------------------------------
# 2. What each real outcome concludes
# --------------------------------------------------------------------------


def test_perfect_solver_run_proves_optimal_over_the_view_objectives(perfect_run: _Run) -> None:
    """Every stage closed `optimal` and the published plan is SCIP's own
    candidate ⇒ `optimal_proven`, from `solver_status`, tie-break closed.

    The witness names the view's objectives in ascending ordinal: the stages
    SCIP ran minus the canonical tie-breaks, which must close but are not
    objectives.
    """
    result = perfect_run.result
    conclusion = conclude_with_solver(result, objective_codes=perfect_run.objective_codes, published=result.candidate)

    assert isinstance(conclusion, OptimalProvenConclusion)
    assert conclusion.kind == "optimal_proven"
    assert conclusion.proof_source == "solver_status"
    assert conclusion.tie_break_closed is True
    assert conclusion.witness.objective_codes == perfect_run.objective_codes
    assert conclusion.witness.objective_codes == tuple(stage.objective_code for stage in sorted(result.stages, key=lambda stage: stage.ordinal) if not _is_tie(stage))
    assert not any(code.startswith(_TIE_STAGE_PREFIX) for code in conclusion.witness.objective_codes)


def test_each_real_outcome_concludes_only_what_scip_established(perfect_run: _Run, infeasible_run: _Run, limited_run: _Run) -> None:
    """The outcome table, on three real runs whose states the fixtures confirm.

    ====================================  ================  ====================
    run                                   published         conclusion
    ====================================  ================  ====================
    incumbent, every stage optimal        SCIP's candidate  optimal_proven
    reported_infeasible, first stage      nothing           infeasibility_proven
    no_incumbent, budget exhausted        nothing           not_proven
    ====================================  ================  ====================
    """
    optimal = conclude_with_solver(perfect_run.result, objective_codes=perfect_run.objective_codes, published=perfect_run.result.candidate)
    assert isinstance(optimal, OptimalProvenConclusion)

    infeasible = conclude_with_solver(infeasible_run.result, objective_codes=infeasible_run.objective_codes, published=None)
    assert isinstance(infeasible, InfeasibilityProvenConclusion)
    assert (infeasible.kind, infeasible.proof_source) == ("infeasibility_proven", "solver_status")
    # The witness names the first objective of the view, which is the stage SCIP closed.
    assert infeasible.witness.objective_codes == (infeasible_run.objective_codes[0],)
    assert infeasible.witness.objective_codes == (_only_stage(infeasible_run.result).objective_code,)

    unproven = conclude_with_solver(limited_run.result, objective_codes=limited_run.objective_codes, published=None)
    assert isinstance(unproven, UnprovenConclusion)
    assert (unproven.kind, unproven.reason_code) == ("not_proven", NOT_PROVEN_REASON)


# --------------------------------------------------------------------------
# 3. The unproven conclusion cannot hold a proof
# --------------------------------------------------------------------------


def test_unproven_conclusion_has_no_field_that_can_hold_a_proof() -> None:
    """`UnprovenConclusion` is structurally incapable of expressing a proof:
    its only fields are `reason_code` and `kind`, and none of the
    proof-bearing fields the proven conclusions carry exist here.
    """
    field_names = set(UnprovenConclusion.__dataclass_fields__)
    assert field_names == {"reason_code", "kind"}
    assert not field_names & {"witness", "proof_source", "tie_break_closed", "objective_codes"}

    conclusion = UnprovenConclusion()
    assert conclusion.kind == "not_proven"


def test_unproven_conclusion_is_frozen() -> None:
    """Frozen: it cannot be mutated into holding a proof kind after the fact."""
    conclusion = UnprovenConclusion()
    with pytest.raises(dataclasses.FrozenInstanceError):
        conclusion.kind = "optimal_proven"


# --------------------------------------------------------------------------
# 4. Every forgery path, checked for its exact exception type
# --------------------------------------------------------------------------

_FORGERIES = (
    pytest.param(lambda: SolverStatusWitnessFacts(objective_codes=("fixed_l2",)), "may only be built from a real solver run", id="witness_missing_seal"),
    pytest.param(lambda: SolverStatusWitnessFacts(objective_codes=("fixed_l2",), seal=object()), "may only be built from a real solver run", id="witness_wrong_seal"),
    pytest.param(lambda: SolverStatusWitnessFacts(objective_codes=(), seal=_SEAL), "at least one objective stage", id="witness_empty_codes"),
    pytest.param(lambda: SolverStatusWitnessFacts(objective_codes=("fixed_l2", "fixed_l2"), seal=_SEAL), "must be unique", id="witness_duplicate_codes"),
    pytest.param(lambda: InfeasibilityProvenConclusion(witness=SolverStatusWitnessFacts(objective_codes=("fixed_l2", "shortfall"), seal=_SEAL)), "exactly the first objective stage", id="infeasibility_naming_two_codes"),
)


@pytest.mark.parametrize(("forge", "reason"), _FORGERIES)
def test_forging_a_witness_raises_proof_forgery_error(forge: Callable[[], object], reason: str) -> None:
    """Each guard raises `ProofForgeryError` — exactly that type, not a
    subclass nor an incidental `ValueError` — and for its own reason, so no
    case passes on a neighbour's guard. The two-code infeasibility is built
    on a validly sealed witness: the witness is sound, the claim it would back
    is not.
    """
    with pytest.raises(ProofForgeryError, match=reason) as raised:
        forge()
    assert type(raised.value) is ProofForgeryError


# --------------------------------------------------------------------------
# 5. Optimal only when every stage closed — the tie-breaks included
# --------------------------------------------------------------------------

_OPEN_STAGE = (
    pytest.param({"status": "unfinished", "scip_status": "timelimit"}, id="cut_by_the_time_limit"),
    pytest.param({"status": "unfinished"}, id="status_unfinished"),
    pytest.param({"scip_status": "timelimit"}, id="scip_status_not_optimal"),
)


@pytest.mark.parametrize("opening", _OPEN_STAGE)
def test_optimal_requires_every_stage_closed_tie_breaks_included(perfect_run: _Run, opening: dict[str, str]) -> None:
    """Leave any single stage open and the optimum is not proven.

    Each stage of the perfect run is reopened in turn — a canonical `tie:*`
    stage exactly like a normative one, because an open tie-break leaves the
    published candidate one optimum among several, not the canonical one —
    while SCIP's candidate is still the one published, so the open stage is
    the only fact that changed. Both SCIP facts are read: a stage is closed
    only when it is `finished` *and* SCIP's status for it is `optimal`.
    """
    result = perfect_run.result
    reopened: dict[str, list[str]] = {"tie": [], "normative": []}
    for stage in result.stages:
        variant = _with_stage(result, stage.stage, **opening)
        conclusion = conclude_with_solver(variant, objective_codes=perfect_run.objective_codes, published=variant.candidate)
        assert isinstance(conclusion, UnprovenConclusion), f"stage {stage.stage!r} left open, yet {conclusion!r}"
        reopened["tie" if _is_tie(stage) else "normative"].append(stage.stage)
    assert reopened["tie"] and reopened["normative"], reopened


# --------------------------------------------------------------------------
# 6. Infeasibility only on a single, first, global stage
# --------------------------------------------------------------------------

_NOT_A_FIRST_STAGE_VERDICT = (
    pytest.param(lambda run: _with_stage(run.result, _only_stage(run.result).stage, ordinal=2), id="ordinal_two"),
    pytest.param(lambda run: _with_stage(run.result, _only_stage(run.result).stage, scope="incumbent_face"), id="incumbent_face"),
    pytest.param(lambda run: dataclasses.replace(run.result, stages=(*run.result.stages, _second_stage_not_reached(run))), id="second_stage_appended"),
    pytest.param(lambda run: _with_stage(run.result, _only_stage(run.result).stage, scip_status="timelimit"), id="scip_status_not_infeasible"),
    pytest.param(lambda run: _with_stage(run.result, _only_stage(run.result).stage, status="unfinished"), id="status_not_infeasible"),
)


@pytest.mark.parametrize("variant", _NOT_A_FIRST_STAGE_VERDICT)
def test_infeasibility_is_proven_only_by_a_single_first_global_stage(infeasible_run: _Run, variant: Callable[[_Run], SolverRunResult]) -> None:
    """SCIP's `infeasible` is a verdict on the scenario only on the first,
    still-global stage, and only when that stage is the whole run: a later
    stage runs on a face earlier pins carved, so its emptiness says nothing
    about the scenario. Every other shape is `not_proven`, never a forgery —
    downgrading is always sound.
    """
    control = conclude_with_solver(infeasible_run.result, objective_codes=infeasible_run.objective_codes, published=None)
    assert isinstance(control, InfeasibilityProvenConclusion)

    conclusion = conclude_with_solver(variant(infeasible_run), objective_codes=infeasible_run.objective_codes, published=None)
    assert isinstance(conclusion, UnprovenConclusion)


# --------------------------------------------------------------------------
# 7. A limit or an anomaly is never a proof
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("run_name", "changes", "publish_scip_candidate"),
    [
        pytest.param("perfect_run", {"anomaly": _ANOMALY}, True, id="anomaly_on_a_perfect_run"),
        pytest.param("infeasible_run", {"anomaly": _ANOMALY}, False, id="anomaly_on_an_infeasible_run"),
        pytest.param("limited_run", {}, False, id="no_incumbent_budget_exhausted"),
        pytest.param("perfect_run", {"outcome": "no_incumbent"}, True, id="no_incumbent_over_closed_stages"),
    ],
)
def test_a_limit_or_an_anomaly_is_never_a_proof(request: pytest.FixtureRequest, run_name: str, changes: dict[str, str], publish_scip_candidate: bool) -> None:
    """An anomaly voids what the statuses would otherwise prove, on either kind
    of run; and a run that found nothing proves nothing — whether a budget
    stopped it, or its outcome says so over otherwise closed stages.
    """
    run: _Run = request.getfixturevalue(run_name)
    variant = dataclasses.replace(run.result, **changes)
    published = variant.candidate if publish_scip_candidate else None

    conclusion = conclude_with_solver(variant, objective_codes=run.objective_codes, published=published)
    assert isinstance(conclusion, UnprovenConclusion)
    assert conclusion.reason_code == NOT_PROVEN_REASON


# --------------------------------------------------------------------------
# 8. A proof is never transferred to a candidate SCIP did not return
# --------------------------------------------------------------------------


def test_a_proof_is_never_transferred_to_a_candidate_scip_did_not_return(perfect_run: _Run, infeasible_run: _Run) -> None:
    """A proof is about the run's own candidate, and nobody else's.

    SCIP's optimum holds for exactly the quanta SCIP returned: move any single
    decision by one quantum — nothing else changed, not even the id — and the
    optimum is no longer proven; publish nothing and there is no plan it could
    be proven about. SCIP's infeasibility holds only while nothing is
    published: a plan published against the verdict contradicts it.
    """
    result = perfect_run.result
    codes = perfect_run.objective_codes
    assert isinstance(conclude_with_solver(result, objective_codes=codes, published=result.candidate), OptimalProvenConclusion)

    for decision in result.candidate.decisions:
        perturbed = _perturbed(result.candidate, decision.decision_id)
        conclusion = conclude_with_solver(result, objective_codes=codes, published=perturbed)
        assert isinstance(conclusion, UnprovenConclusion), decision.decision_id

    assert isinstance(conclude_with_solver(result, objective_codes=codes, published=None), UnprovenConclusion)

    plan = _candidate(infeasible_run.view, {}, candidate_id="published-against-the-verdict")
    conclusion = conclude_with_solver(infeasible_run.result, objective_codes=infeasible_run.objective_codes, published=plan)
    assert isinstance(conclusion, UnprovenConclusion)


def test_infeasible_verdict_alongside_a_candidate_is_not_proven(infeasible_run: _Run) -> None:
    """No fabricated proof: an infeasible verdict that comes back with a
    candidate contradicts itself, so it proves nothing — whether or not that
    candidate is then published. The verdict alone, nothing found and nothing
    published, is the only shape that proves infeasibility.
    """
    result = infeasible_run.result
    codes = infeasible_run.objective_codes
    assert isinstance(conclude_with_solver(result, objective_codes=codes, published=None), InfeasibilityProvenConclusion)

    candidate = _candidate(infeasible_run.view, {}, candidate_id="returned-with-the-verdict")
    contradicted = dataclasses.replace(result, candidate=candidate)
    for published in (None, candidate):
        conclusion = conclude_with_solver(contradicted, objective_codes=codes, published=published)
        assert isinstance(conclusion, UnprovenConclusion), published


# --------------------------------------------------------------------------
# 9. Objective codes that disagree with SCIP's stages are a forgery
# --------------------------------------------------------------------------

_MISNAMED_OBJECTIVES = (
    pytest.param("perfect_run", lambda codes: tuple(reversed(codes)), "SCIP closed the stages", id="optimal_codes_reordered"),
    pytest.param("perfect_run", lambda codes: codes[:-1], "SCIP closed the stages", id="optimal_codes_missing_one"),
    pytest.param("perfect_run", lambda codes: (*codes, "turnover"), "SCIP closed the stages", id="optimal_codes_with_an_extra"),
    pytest.param("infeasible_run", lambda codes: (*codes[1:], codes[0]), "infeasible, but the first objective is", id="infeasible_first_code_differs"),
    pytest.param("infeasible_run", lambda codes: (), "infeasible, but the first objective is None", id="infeasible_no_objective_codes"),
)


@pytest.mark.parametrize(("run_name", "misname", "reason"), _MISNAMED_OBJECTIVES)
def test_objective_codes_disagreeing_with_scip_stages_are_a_forgery(request: pytest.FixtureRequest, run_name: str, misname: Callable[[tuple[str, ...]], tuple[str, ...]], reason: str) -> None:
    """A run that would prove something, named against objectives other than
    the stages SCIP closed (reordered, one missing, one extra, a different
    first code, or none at all), is not downgraded: it raises. The view and the
    compiled cascade disagree about what was optimized, so any conclusion would
    be a claim SCIP never made — `ProofForgeryError`, exact type, and for this
    reason.
    """
    run: _Run = request.getfixturevalue(run_name)
    codes = misname(run.objective_codes)
    assert codes != run.objective_codes

    # SCIP's own candidate on the optimal run; nothing on the infeasible one.
    published = run.result.candidate
    with pytest.raises(ProofForgeryError, match=reason) as raised:
        conclude_with_solver(run.result, objective_codes=codes, published=published)
    assert type(raised.value) is ProofForgeryError
