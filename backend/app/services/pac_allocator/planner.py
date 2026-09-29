"""PAC planner v2 orchestration.

One service function, ``plan_pac_allocation``: validate the request,
normalize it, and either return a failure result or run the plan and project
it onto the wire.

The pipeline, and the reason each hop exists:

    normalize -> build_exact_policy_view -> compile -> SCIP
              -> evaluate_exact_candidate replay -> proof -> planner_report

SCIP is the only production search engine, and its own status is the proof
(D-X1, developer decision of 2026-09-24): every stage closed ``optimal`` is
``optimal_proven``, a first stage closed ``infeasible`` is
``infeasibility_proven``, and a limit is ``not_proven`` with the best plan
found, or with none. The exhaustive oracle is a test instrument
(``backend/test_scripts``); production cannot reach it.

``evaluate_exact_candidate`` is **always** on the path, and its verdict is
authoritative. SCIP's incumbent is a floating proposal that has to survive
exact arithmetic before a single number of it is published. The one deficit
the replay tolerates is rounding (QX1-b, developer decision of 2026-09-25): a
plan whose HALF_UP postings leave a cash pool (broker x currency) at most N
minor units short, N being the pool's postings that carry a quantum, is
published with one top-up per such pool — "this broker/currency needs D more".
``evaluator.rounding_top_ups`` decides. Any other rejection raises
``ExactReplayRejectedError``, which the Tool reports as ``execution_failed``:
publishing an unverified plan is the one outcome this package exists to
prevent, and a SCIP plan the replay rejects is a defect, not a result.

Only ``plan_pac_allocation`` is exported. ``plan_rebalancing`` deliberately
does not exist: every Rebalancer policy and the SELL verifier are deferred,
and a function that exists but always fails is worse than an absent one —
it invites wiring, whereas an absent one fails at import in the exact place
the missing work is obvious.

Tool registration (``ToolService``/``ToolOperationPolicy``) is **not** done
here; this module ships service functions only, and
``tool_plugins/pac_allocator.py`` owns the dispatch.

``plan_pac_allocation`` is deliberately **not** re-exported from the package
``__init__``, and that absence is load-bearing rather than an oversight. The
import chain is ``planner -> compiler -> pyscipopt`` (``compiler.py`` imports
``Model`` at module level, because unlike ``constraints``/``objectives`` it
actually instantiates one). Re-exporting it would drag SCIP into every
consumer of the package at import time, for a solver most of them never call.

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
    SolverStatusWitness,
)
from backend.app.services.pac_allocator import planner_report as report
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate, rounding_top_ups
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    Checkpoint,
    ExactEvaluation,
    ExactObjectiveCode,
    ExactPlannerScenario,
    ExactPolicyView,
    ExactRoundingTopUp,
    check_budget,
)
from backend.app.services.pac_allocator.normalize import normalize_pac_plan
from backend.app.services.pac_allocator.proof import (
    InfeasibilityProvenConclusion,
    OptimalProvenConclusion,
    PlanConclusion,
    SolverStatusWitnessFacts,
    UnprovenConclusion,
    conclude_with_solver,
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
    solver: SolverRunResult


def plan_pac_allocation(
    request: PacPlannerRequest,
    *,
    checkpoint: Checkpoint | None = None,
    solver_time_budget_seconds: float | None = None,
) -> PacPlannerResult:
    """Plan a PAC allocation and return a wire result.

    Never raises on a planning outcome: an infeasible scenario and an exhausted
    budget are *results*, each with its own ``result_state``. A genuine
    contract violation propagates, and so does ``ExactReplayRejectedError``: a
    SCIP plan the exact replay rejects for more than rounding is a defect, not
    an outcome to answer with.

    ``solver_time_budget_seconds`` is the engine window the caller has already
    claimed. It matters more than it looks: the lexicographic cascade is what
    makes the answer unique, so a budget that truncates it at a different stage
    on a slower machine yields a *different plan for the same input*. Leaving it
    ``None`` keeps ``solver.py``'s own default, which is only correct for a
    caller that has no window to claim — every Tool caller has one.
    """
    check_budget(checkpoint)
    normalized = normalize_pac_plan(request)
    snapshot = PlannerResultSnapshot(snapshot_id=request.snapshot.snapshot_id, request_fingerprint=request.snapshot.snapshot_id)

    if not normalized.ready or normalized.normalized is None:
        return _failure_result(normalized.availability, snapshot, list(normalized.issues))

    scenario = normalized.normalized
    view = build_exact_policy_view(scenario, purpose="primary")
    check_budget(checkpoint)

    search = _search(scenario, view, checkpoint=checkpoint, solver_time_budget_seconds=solver_time_budget_seconds)
    issues = list(normalized.issues)

    if search.candidate is None:
        return _no_incumbent_result(scenario, view, search, issues)

    # The single non-negotiable hop: nothing is published that exact
    # arithmetic has not re-derived from the candidate itself. Its verdict is
    # final: a rounding deficit within the threshold comes back as top-ups,
    # any other rejection raises.
    evaluation = evaluate_exact_candidate(scenario, view, search.candidate, checkpoint=checkpoint)
    top_ups = rounding_top_ups(scenario, evaluation)

    conclusion = _conclude(view, search, published=search.candidate)
    check_budget(checkpoint)
    return _ready_result(scenario, view, search, evaluation, conclusion, issues, top_ups)


def _search(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    *,
    checkpoint: Checkpoint | None,
    solver_time_budget_seconds: float | None = None,
) -> _Search:
    """Compile the view and run SCIP, the only production search engine (D-X1).

    There is no other route and no size threshold: the exhaustive oracle is a
    test instrument that production cannot reach, and SCIP's cost grows with
    the number of decisions, not with the size of the domain (see
    ``planner_report.build_stop_reason``). SCIP's candidate stays a proposal
    until the Decimal replay accepts it, and its statuses become a proof only
    through ``proof.conclude_with_solver``.
    """
    program = compile_policy_program(scenario, view)
    solver = solve_policy_program(
        program,
        checkpoint=checkpoint,
        **({} if solver_time_budget_seconds is None else {"time_budget_seconds": solver_time_budget_seconds}),
    )
    return _Search(candidate=solver.candidate, solver=solver)


def _objective_codes(view: ExactPolicyView) -> tuple[ExactObjectiveCode, ...]:
    """The view's objectives in cascade order, as ``build_objective_results`` publishes them."""
    return tuple(ref.code for ref in sorted(view.objectives, key=lambda ref: ref.ordinal))


def _conclude(view: ExactPolicyView, search: _Search, *, published: CandidateActionVector | None) -> PlanConclusion:
    """Decide the proof, which only ``proof.py`` may do.

    ``published`` is the candidate this result publishes — SCIP's, after the
    Decimal replay accepted it — or ``None`` when nothing is published.
    """
    return conclude_with_solver(search.solver, objective_codes=_objective_codes(view), published=published)


def _ready_result(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    search: _Search,
    evaluation: ExactEvaluation,
    conclusion: PlanConclusion,
    issues: list[PlannerIssue],
    top_ups: tuple[ExactRoundingTopUp, ...],
) -> PacPlannerResult:
    common = _common_ready_fields(scenario, view, search, evaluation, issues)
    proof = _wire_proof(conclusion)
    parts = _build_solution_parts(scenario, view, evaluation, top_ups)

    # The no-op decision is made *before* choosing the solution model, not
    # after: `PacIncumbentSolution` requires at least one order row while
    # `PacNoOpSolution` requires every action list to be empty, so the two are
    # mutually exclusive shapes over the same projected rows rather than one
    # being convertible into the other.
    if _is_no_op(evaluation):
        return PacPlannerReadyNoOpResult(result_state="ready_no_op", outcome="no_op", proof=proof, primary_solution=PacNoOpSolution(**parts), deployment=_DEPLOYMENT, **common)
    return PacPlannerReadyIncumbentResult(result_state="ready_incumbent", outcome="incumbent_found", proof=proof, primary_solution=PacIncumbentSolution(**parts), deployment=_DEPLOYMENT, **common)


def _no_incumbent_result(scenario: ExactPlannerScenario, view: ExactPolicyView, search: _Search, issues: list[PlannerIssue]) -> PacPlannerResult:
    """No publishable plan: SCIP proved there is none, or found none in time.

    ``ready_infeasible`` needs an ``InfeasibilityProvenProof``, and only
    ``proof.conclude_with_solver`` can conclude one: SCIP closed the first,
    still-global stage ``infeasible``. Its ``stop_reason`` is ``completed``
    because the search ended on that verdict, and ``build_stop_reason``
    already says so — an infeasible stage is not an unfinished one.

    Everything else is ``ready_no_incumbent`` with ``not_proven``: a limit that
    left no solution. A SCIP plan the Decimal replay rejects never lands here:
    it is published with its rounding top-ups, or ``plan_pac_allocation``
    raises ``ExactReplayRejectedError``.
    """
    evaluation = _zero_candidate_evaluation(scenario, view)
    common = _common_ready_fields(scenario, view, search, evaluation, issues)

    conclusion = _conclude(view, search, published=None)
    if isinstance(conclusion, InfeasibilityProvenConclusion):
        return PacPlannerReadyInfeasibleResult(result_state="ready_infeasible", outcome="infeasible_proven", proof=_wire_infeasibility(conclusion), **common)

    return PacPlannerReadyNoIncumbentResult(result_state="ready_no_incumbent", outcome="no_incumbent", proof=NotProvenProof(kind="not_proven", reason_code=UnprovenConclusion().reason_code), **common)


def _common_ready_fields(scenario, view, search: _Search, evaluation: ExactEvaluation, issues: list[PlannerIssue]) -> dict:
    return {
        "operation": "plan",
        "availability": "ready",
        "snapshot": report.build_result_snapshot(scenario, view),
        "catalogs": report.build_planner_catalogs(scenario),
        "provenance": report.build_planner_provenance(scenario),
        "scenario_basis": report.build_scenario_basis(scenario, evaluation),
        "stop_reason": report.build_stop_reason(search.solver),
        "solver_evidence": report.build_solver_evidence(scenario, view, search.solver),
        "issues": issues,
    }


def _build_solution_parts(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation, top_ups: tuple[ExactRoundingTopUp, ...]) -> dict:
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
        "rounding_top_ups": report.build_rounding_top_ups(scenario, top_ups),
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
    carries a scenario basis.
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
    """Project a published plan's conclusion onto the wire union."""
    if isinstance(conclusion, OptimalProvenConclusion):
        return OptimalProvenProof(
            kind="optimal_proven",
            proof_source="solver_status",
            witness=_wire_solver_witness(conclusion.witness),
            tie_break_closed=True,
        )
    return NotProvenProof(kind="not_proven", reason_code=conclusion.reason_code if isinstance(conclusion, UnprovenConclusion) else UnprovenConclusion().reason_code)


def _wire_infeasibility(conclusion: InfeasibilityProvenConclusion) -> InfeasibilityProvenProof:
    return InfeasibilityProvenProof(kind="infeasibility_proven", proof_source="solver_status", witness=_wire_solver_witness(conclusion.witness))


def _wire_solver_witness(witness: SolverStatusWitnessFacts) -> SolverStatusWitness:
    return SolverStatusWitness(kind="solver_status", objective_codes=list(witness.objective_codes))


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
