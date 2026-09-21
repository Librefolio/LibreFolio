"""PAC planner v2 orchestration (Step 3, Stage 5b).

One service function, ``plan_pac_allocation``, shaped exactly like P1's
``analyze_pac_budget``: validate the request, normalize it, and either return
a failure result or run the plan and project it onto the wire.

The pipeline, and the reason each hop exists:

    normalize -> build_exact_policy_view -> oracle-or-solver
              -> evaluate_exact_candidate replay -> proof -> planner_report

``evaluate_exact_candidate`` is **always** on the path. Neither search is
trusted to report its own result: the oracle already replays every candidate
it enumerates, and the solver's incumbent is a floating proposal that has to
survive exact arithmetic before a single number of it is published. A
candidate that fails replay does not degrade into a warning — it produces
``ready_no_incumbent``, because publishing an unverified plan is the one
outcome this package exists to prevent.

Only ``plan_pac_allocation`` is exported. ``plan_rebalancing`` deliberately
does not exist: every Rebalancer policy and the SELL verifier are deferred,
and a function that exists but always fails is worse than an absent one —
it invites wiring, whereas an absent one fails at import in the exact place
the missing work is obvious.

Tool registration (``ToolService``/``ToolOperationPolicy``) is **not** done
here; this module ships service functions only, mirroring the existing P1
split where ``tool_plugins/pac_allocator.py`` owns the dispatch.

``plan_pac_allocation`` is deliberately **not** re-exported from the package
``__init__``, and that absence is load-bearing rather than an oversight. The
import chain is ``planner -> compiler -> pyscipopt`` (``compiler.py`` imports
``Model`` at module level, because unlike ``constraints``/``objectives`` it
actually instantiates one). Re-exporting here would therefore make every
consumer of the lightweight P1 analyses — ``analyze_pac_budget``,
``analyze_rebalancing`` — drag SCIP in at import time for a solver they never
call, and would silently falsify the package docstring's promise, *"Pure P1
allocation analyses. No solver, order, lookup, or persistence."*, which is
exactly the promise a reader relies on when deciding whether importing the
package is cheap.

Verified rather than asserted: importing ``backend.app.services.pac_allocator``
leaves ``pyscipopt`` absent from ``sys.modules``, while importing this module
puts it there. A subprocess test pins that property, because in-process the
module is already loaded by sibling tests and the assertion would be vacuous.
Import ``plan_pac_allocation`` from this module by path; do not "fix" the
missing package-level export.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.schemas.pac_allocator import (
    DeploymentUnavailable,
    ExhaustiveOracleWitness,
    InfeasibilityProvenProof,
    NotProvenProof,
    OptimalProvenProof,
    PacIncumbentSolution,
    PacNoOpSolution,
    PacPlannerInvalidResult,
    PacPlannerNeedsInputResult,
    PacPlannerReadyIncumbentResult,
    PacPlannerReadyInfeasibleResult,
    PacPlannerReadyNoIncumbentResult,
    PacPlannerReadyNoOpResult,
    PacPlannerRequest,
    PacPlannerResult,
    PacPlannerUnsupportedResult,
    PlannerIssue,
    PlannerResultSnapshot,
    SolverNotRunEvidence,
)
from backend.app.services.pac_allocator import planner_report as report
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    Checkpoint,
    ExactEvaluation,
    ExactPlannerScenario,
    ExactPolicyView,
    check_budget,
)
from backend.app.services.pac_allocator.normalize import normalize_pac_plan
from backend.app.services.pac_allocator.oracle import (
    MAX_EXHAUSTIVE_ORACLE_CANDIDATES,
    OracleDomainTooLargeError,
    estimate_oracle_domain_size,
    run_exhaustive_oracle,
)
from backend.app.services.pac_allocator.proof import (
    InfeasibilityProvenConclusion,
    OptimalProvenConclusion,
    PlanConclusion,
    UnprovenConclusion,
    conclude_with_oracle,
    conclude_without_proof,
)
from backend.app.services.pac_allocator.solver import SolverRunResult, solve_policy_program

__all__ = ["plan_pac_allocation"]

_PRIMARY_SOLUTION_ID = "solution:primary"

# Phase-1 deployment answer. `deployment_omitted` states "we did not compute
# this", which is true: no second deploy-the-remainder optimization runs here.
# `primary_is_deployment` would assert an equivalence never established, which
# would be a claim rather than a report.
_DEPLOYMENT = DeploymentUnavailable(kind="unavailable", reason_code="allocation.deployment_omitted")


@dataclass(frozen=True, slots=True)
class _Search:
    """What the search stage found, before any of it is trusted."""

    candidate: CandidateActionVector | None
    solver: SolverRunResult | None
    oracle_enumerated: bool
    oracle_result: object | None


def plan_pac_allocation(request: PacPlannerRequest, *, checkpoint: Checkpoint | None = None) -> PacPlannerResult:
    """Plan a PAC allocation and return a wire result.

    Never raises on a planning outcome: an infeasible scenario, an exhausted
    budget and a candidate that fails replay are all *results*, each with its
    own ``result_state``. Only a genuine contract violation propagates.
    """
    check_budget(checkpoint)
    normalized = normalize_pac_plan(request)
    snapshot = PlannerResultSnapshot(snapshot_id=request.snapshot.snapshot_id, request_fingerprint=request.snapshot.snapshot_id)

    if not normalized.ready or normalized.normalized is None:
        return _failure_result(normalized.availability, snapshot, list(normalized.issues))

    scenario = normalized.normalized
    view = build_exact_policy_view(scenario, purpose="primary")
    check_budget(checkpoint)

    search = _search(scenario, view, checkpoint=checkpoint)
    issues = list(normalized.issues)

    if search.candidate is None:
        return _no_incumbent_result(scenario, view, search, issues)

    # The single non-negotiable hop: nothing is published that exact
    # arithmetic has not re-derived from the candidate itself.
    evaluation = evaluate_exact_candidate(scenario, view, search.candidate, checkpoint=checkpoint)
    if not evaluation.feasible:
        # A search proposed something the exact domain rejects. That is not a
        # warning to attach to a published plan — there is no plan.
        return _no_incumbent_result(scenario, view, search, issues)

    conclusion = _conclude(search, evaluation)
    check_budget(checkpoint)
    return _ready_result(scenario, view, search, evaluation, conclusion, issues)


def _search(scenario: ExactPlannerScenario, view: ExactPolicyView, *, checkpoint: Checkpoint | None) -> _Search:
    """Try the exhaustive oracle first; fall back to the solver.

    The oracle is not merely another search: on a domain it can enumerate it
    returns a *proven* optimum, so trying it first is what makes
    ``optimal_proven`` reachable at all. When it settles the outcome the
    solver is **not run**, and the result carries
    ``SolverNotRunEvidence(reason="allocation.solver_not_required")`` — which
    is literally what that single-valued reason code exists for.

    Running the solver anyway would not merely be wasted work: an infeasible
    SCIP stage is necessarily ``unfinished`` (a finished stage must carry a
    finite primal, which an infeasible solve has none of), while
    ``PacPlannerReadyInfeasibleResult`` pins ``stop_reason="completed"`` and
    ``_validate_stop_evidence`` requires ``completed`` to mean *no* unfinished
    stage. So a redundant solver run made ``ready_infeasible`` unemittable and
    turned a perfectly ordinary infeasible scenario into a raised
    ``ValidationError``.

    What this deliberately gives up is a *diagnostic*, not a guarantee:
    production no longer has a competing solver incumbent that could disagree
    with the oracle. The oracle is exhaustive, so its answer is the answer,
    and a disagreeing solver would have signalled a modelling bug rather than
    a wrong published result. That cross-check still runs — in
    ``test_pac_planner_solver.py``'s oracle-agreement gate, which drives both
    engines directly and is where it caught the HALF_UP ledger defect.

    Routing is internal and never wire-visible: a domain above the cap simply
    falls back to the solver and an honest ``not_proven``.
    """
    if estimate_oracle_domain_size(view) <= MAX_EXHAUSTIVE_ORACLE_CANDIDATES:
        try:
            oracle_result = run_exhaustive_oracle(scenario, view, checkpoint=checkpoint)
        except OracleDomainTooLargeError:
            oracle_result = None
        if oracle_result is not None:
            return _Search(candidate=oracle_result.best_candidate, solver=None, oracle_enumerated=True, oracle_result=oracle_result)

    program = compile_policy_program(scenario, view)
    solver = solve_policy_program(program, checkpoint=checkpoint)
    return _Search(candidate=solver.candidate, solver=solver, oracle_enumerated=False, oracle_result=None)


def _conclude(search: _Search, evaluation: ExactEvaluation) -> PlanConclusion:
    """Decide the proof, which only ``proof.py`` may do.

    Note what is *not* consulted: no field of ``search.solver`` can promote
    anything. A fully-successful floating solve still yields ``not_proven``.
    """
    if search.oracle_enumerated and search.oracle_result is not None:
        return conclude_with_oracle(search.oracle_result, published=search.candidate)
    if search.solver is None:
        raise ValueError("a search with neither an oracle result nor a solver run cannot conclude anything")
    return conclude_without_proof(search.solver)


def _ready_result(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    search: _Search,
    evaluation: ExactEvaluation,
    conclusion: PlanConclusion,
    issues: list[PlannerIssue],
) -> PacPlannerResult:
    common = _common_ready_fields(scenario, view, search, evaluation, issues)
    proof = _wire_proof(conclusion)
    parts = _build_solution_parts(scenario, view, evaluation)

    # The no-op decision is made *before* choosing the solution model, not
    # after: `PacIncumbentSolution` requires at least one order row while
    # `PacNoOpSolution` requires every action list to be empty, so the two are
    # mutually exclusive shapes over the same projected rows rather than one
    # being convertible into the other.
    if _is_no_op(evaluation):
        return PacPlannerReadyNoOpResult(result_state="ready_no_op", outcome="no_op", proof=proof, primary_solution=PacNoOpSolution(**parts), deployment=_DEPLOYMENT, **common)
    return PacPlannerReadyIncumbentResult(result_state="ready_incumbent", outcome="incumbent_found", proof=proof, primary_solution=PacIncumbentSolution(**parts), deployment=_DEPLOYMENT, **common)


def _no_incumbent_result(scenario: ExactPlannerScenario, view: ExactPolicyView, search: _Search, issues: list[PlannerIssue]) -> PacPlannerResult:
    """No publishable plan: either nothing was found, or the domain was
    exhaustively proven to contain nothing feasible.

    ``ready_infeasible`` requires an ``InfeasibilityProvenProof``, so it is
    reachable **only** through the exhaustive oracle — a SCIP
    ``reported_infeasible`` structurally cannot reach it, which is the point.
    Its ``stop_reason`` is pinned to ``"completed"`` because a finished
    enumeration is the only thing that proved it.

    The ``deterministic_conflict`` proof source is deliberately **not**
    emitted in phase 1. ``DeterministicConflictWitness.issue_codes`` is typed
    ``list[PlannerIssueCode]`` — the frozen 80-value ``allocation.*`` wire
    universe — while ``ExactEvaluation.conflict_codes`` carries exact-domain
    constraint codes such as ``ORDER_REQUIRED_MIN``. Those are two different
    vocabularies, and no bridge should be invented between them: a
    normalization-time statement about *declared inputs* and an
    evaluation-time statement about a *candidate* are not the same claim, so
    a mapping table would manufacture an equivalence and publish it as a
    **witness** — precisely the class of thing ``proof.py`` exists to make
    unrepresentable. Extending the enum is not available either: it is frozen
    and ``RuntimeError``-guarded (``issues.py:48-50``). So proven
    infeasibility comes from the oracle alone, and everything else is
    honestly ``not_proven``.
    """
    evaluation = _zero_candidate_evaluation(scenario, view)
    common = _common_ready_fields(scenario, view, search, evaluation, issues)

    if search.oracle_enumerated and search.oracle_result is not None and search.oracle_result.feasible_candidates == 0:
        conclusion = conclude_with_oracle(search.oracle_result, published=None)
        if isinstance(conclusion, InfeasibilityProvenConclusion):
            return PacPlannerReadyInfeasibleResult(result_state="ready_infeasible", outcome="infeasible_proven", proof=_wire_infeasibility(conclusion), **{**common, "stop_reason": "completed"})

    return PacPlannerReadyNoIncumbentResult(result_state="ready_no_incumbent", outcome="no_incumbent", proof=NotProvenProof(kind="not_proven", reason_code=UnprovenConclusion().reason_code), **common)


def _common_ready_fields(scenario, view, search: _Search, evaluation: ExactEvaluation, issues: list[PlannerIssue]) -> dict:
    return {
        "operation": "plan",
        "availability": "ready",
        "snapshot": report.build_result_snapshot(scenario, view),
        "catalogs": report.build_planner_catalogs(scenario),
        "provenance": report.build_planner_provenance(scenario),
        "scenario_basis": report.build_scenario_basis(scenario, evaluation),
        # No solver run means nothing stopped early, so "completed" is the
        # only consistent stop_reason -- and `completed` + `not_run` is
        # exactly the combination `_validate_stop_evidence` allows.
        "stop_reason": "completed" if search.solver is None else report.build_stop_reason(search.solver),
        "solver_evidence": SolverNotRunEvidence(kind="not_run", reason="allocation.solver_not_required") if search.solver is None else report.build_solver_evidence(scenario, view, search.solver),
        "issues": issues,
    }


def _build_solution_parts(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation) -> dict:
    """Assemble the primary solution.

    One ``_SequenceAllocator`` is shared across funding, FX and order rows —
    not one per section. The schema wants ids and sequences unique across all
    three *and* each section internally ascending; three counters would
    collide on row one, and a single dense counter satisfies both at once.
    """
    sequence = report._SequenceAllocator()
    return {
        "solution_id": _PRIMARY_SOLUTION_ID,
        "solution_kind": "primary",
        "validation": "decimal_verified",
        "asset_rows": report.build_asset_rows(scenario, evaluation),
        "funding_actions": report.build_funding_actions(scenario, evaluation, sequence),
        "fx_actions": report.build_fx_actions(scenario, evaluation, sequence),
        "order_rows": report.build_order_rows(scenario, evaluation, sequence),
        "ledger_rows": report.build_ledger_rows(evaluation),
        "exposure_rows": report.build_exposure_rows(scenario, evaluation),
        "accounting": report.build_accounting(scenario, evaluation),
        "costs": report.build_costs(scenario, evaluation),
        "objectives": report.build_objective_results(scenario, view, evaluation),
    }


def _is_no_op(evaluation: ExactEvaluation) -> bool:
    return not evaluation.orders and not evaluation.funding_transfers and not evaluation.fx


def _zero_candidate_evaluation(scenario: ExactPlannerScenario, view: ExactPolicyView) -> ExactEvaluation:
    """Evaluate the do-nothing candidate.

    Needed even when no plan is publishable, because every ready result still
    carries a scenario basis, and because a deterministic conflict on the
    all-zero candidate is one of the two legal routes to a proven
    infeasibility.
    """
    candidate = CandidateActionVector(
        view_id=view.view_id,
        candidate_id="plan:zero",
        decisions=tuple(CandidateDecision(decision_id=access.decision_id, quanta=_baseline_quanta(access)) for access in view.decisions),
    )
    return evaluate_exact_candidate(scenario, view, candidate)


def _baseline_quanta(access) -> int:
    """The do-nothing quanta for one decision, guaranteed contract-valid.

    A blind ``0`` is *not* always valid: a ``frozen_exact`` decision with a
    nonzero ``frozen_quanta``, or any decision whose ``lower_quanta`` exceeds
    zero, would be rejected by the candidate contract. Using the decision's
    own frozen or baseline value is valid for any well-formed view, and for
    the all-mutable PAC-primary shape it is exactly zero anyway. Same
    reasoning as ``compiler.py``'s probe candidate; re-derived here rather
    than importing another module's private helper.
    """
    return access.frozen_quanta if access.mode == "frozen_exact" else access.baseline_quanta


def _wire_proof(conclusion: PlanConclusion):
    """Project a proof conclusion onto the wire union.

    ``gap_bounded`` is unreachable here on purpose: it needs a sound dual
    bound, and deriving one from SCIP's floating dual would be exactly the
    promotion ``proof.py`` exists to forbid.
    """
    if isinstance(conclusion, OptimalProvenConclusion):
        return OptimalProvenProof(
            kind="optimal_proven",
            proof_source="exhaustive_oracle",
            witness=_wire_oracle_witness(conclusion.witness),
            tie_break_closed=True,
        )
    return NotProvenProof(kind="not_proven", reason_code=conclusion.reason_code if isinstance(conclusion, UnprovenConclusion) else UnprovenConclusion().reason_code)


def _wire_infeasibility(conclusion: InfeasibilityProvenConclusion) -> InfeasibilityProvenProof:
    """Project an oracle-backed infeasibility proof.

    Only the ``exhaustive_oracle`` source is reachable here; see
    ``_no_incumbent_result`` for why ``deterministic_conflict`` is not emitted
    in phase 1.
    """
    if conclusion.proof_source != "exhaustive_oracle":
        raise ValueError(f"phase 1 publishes only oracle-backed infeasibility proofs; got {conclusion.proof_source!r}")
    return InfeasibilityProvenProof(kind="infeasibility_proven", proof_source="exhaustive_oracle", witness=_wire_oracle_witness(conclusion.witness))


def _wire_oracle_witness(witness) -> ExhaustiveOracleWitness:
    return ExhaustiveOracleWitness(
        kind="exhaustive_oracle",
        enumerated_candidates=witness.enumerated_candidates,
        feasible_candidates=witness.feasible_candidates,
        objective_codes=list(witness.objective_codes),
    )


def _failure_result(availability: str, snapshot: PlannerResultSnapshot, issues: list[PlannerIssue]) -> PacPlannerResult:
    """Return the failure result matching the normalizer's availability.

    The schema requires a failure result to carry an error issue whose kind
    matches its availability, so this never invents one: if normalization
    said ``invalid`` it also produced the controlling issue.
    """
    if availability == "needs_input":
        return PacPlannerNeedsInputResult(operation="plan", result_state="needs_input", availability="needs_input", snapshot=snapshot, issues=issues)
    if availability == "unsupported":
        return PacPlannerUnsupportedResult(operation="plan", result_state="unsupported", availability="unsupported", snapshot=snapshot, issues=issues)
    return PacPlannerInvalidResult(operation="plan", result_state="invalid", availability="invalid", snapshot=snapshot, issues=issues)
