"""Planner orchestration for the two Tools: the PAC and the Rebalancer.

Two service functions, ``plan_pac_allocation`` and ``plan_rebalancing``
(B3 of project 67): validate the request, normalize it, and either return a
failure result or run the plan and project it onto the wire. Both run one
body, ``_plan`` and ``plan_exact_scenario``; the product is chosen in one
place, a ``_Product`` that names the wire classes and the projection of the
solution.

The pipeline, and the reason each hop exists:

    normalize -> build_exact_policy_view -> compile -> SCIP
              -> evaluate_exact_candidate replay -> proof -> planner_report

SCIP is the only production search engine, and its own status is the proof
(D-X1, developer decision of 2026-09-24): every stage closed ``optimal`` is
``optimal_proven``, a first stage closed ``infeasible`` is
``infeasibility_proven``, and a limit is ``not_proven`` with the best plan
found, or with none. The exhaustive oracle is a test instrument
(``backend/test_scripts``); production cannot reach it.

One check stands between SCIP and ``infeasibility_proven``: doing nothing is
a plan too. If the exact replay accepts it, SCIP's verdict is contradicted,
and ``SolverInfeasibilityContradictedError`` is raised instead
(``_no_incumbent_result``).

``evaluate_exact_candidate`` is **always** on the path, and its verdict is
authoritative. SCIP's incumbent is a floating proposal that has to survive
exact arithmetic before a single number of it is published. The one deficit
the replay tolerates is rounding (QX1-b, developer decision of 2026-09-25): a
plan whose postings, rounded against the plan, leave a cash pool (broker x
currency) at most N minor units short, N being the pool's postings that carry
a quantum, is published with one top-up per such pool — "this broker/currency
needs D more".
``evaluator.rounding_top_ups`` decides. Any other rejection raises
``ExactReplayRejectedError``, which the Tool reports as ``execution_failed``:
publishing an unverified plan is the one outcome this package exists to
prevent, and a SCIP plan the replay rejects is a defect, not a result. One
rejection is answered «no plan» instead: the plan the solver held for want of
another, already refused by its own replay, when the cascade ends on it (R1-A
of project 67, ``_refused_plan``; logged).

Both functions are exported. The Rebalancer plans «Invest only» until C1:
its request refuses «Invest and sell» and any sale route at the schema
(S1), so a sale never reaches an engine that does not model it yet.

Tool registration (``ToolService``/``ToolOperationPolicy``) is **not** done
here; this module ships service functions only, and
``tool_plugins/pac_allocator/plugin.py`` owns the dispatch.

``plan_pac_allocation`` (and ``plan_rebalancing``) is deliberately **not** re-exported from the package
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

import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from backend.app.config import planner as planner_config
from backend.app.logging_config import get_logger
from backend.app.schemas.pac_allocator.evidence import InfeasibilityProvenProof, NotProvenProof, OptimalProvenProof, ProofMargin, RebalancerOptimalProvenProof, SolverStatusWitness
from backend.app.schemas.pac_allocator.issues import PlannerIssue
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, RebalancerPlannerRequest
from backend.app.schemas.pac_allocator.results import (
    PacPlannerInvalidResult,
    PacPlannerNeedsInputResult,
    PacPlannerReadyIncumbentResult,
    PacPlannerReadyInfeasibleResult,
    PacPlannerReadyNoIncumbentResult,
    PacPlannerReadyNoOpResult,
    PacPlannerResult,
    PacPlannerUnsupportedResult,
    PlannerResultSnapshot,
    RebalancerPlannerInvalidResult,
    RebalancerPlannerNeedsInputResult,
    RebalancerPlannerReadyIncumbentResult,
    RebalancerPlannerReadyInfeasibleResult,
    RebalancerPlannerReadyNoIncumbentResult,
    RebalancerPlannerReadyNoOpResult,
    RebalancerPlannerResult,
    RebalancerPlannerUnsupportedResult,
)
from backend.app.schemas.pac_allocator.solutions import DeploymentUnavailable, PacIncumbentSolution, PacNoOpSolution, RebalancerIncumbentSolution, RebalancerNoOpSolution
from backend.app.services.pac_allocator import plan_sequence, rebalancer_report
from backend.app.services.pac_allocator import planner_report as report
from backend.app.services.pac_allocator.compiler import CompiledProgram, compile_policy_program
from backend.app.services.pac_allocator.evaluation.errors import ExactEvaluatorError, ExactReplayRejectedError
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, cash_limit_overshoots, evaluate_do_nothing, evaluate_exact_candidate, rounding_top_ups
from backend.app.services.pac_allocator.evaluation.limits import LimitEntry, limited_entries
from backend.app.services.pac_allocator.evaluation.solver_view import solver_view_objectives
from backend.app.services.pac_allocator.issues import bounds_unsatisfiable_issue, cash_limit_exceeded_by_rounding_issue, solver_numerical_error_issue
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    Checkpoint,
    ExactEvaluation,
    ExactObjectiveCode,
    ExactPlannerScenario,
    ExactPolicyView,
    ExactRoundingTopUp,
    check_budget,
)
from backend.app.services.pac_allocator.normalize import normalize_pac_plan, normalize_rebalancer_plan
from backend.app.services.pac_allocator.numeric import ExactRatio, post_ceiling
from backend.app.services.pac_allocator.progress import ProgressReporter, report_phase
from backend.app.services.pac_allocator.proof import (
    PROOF_NOT_CONFIRMED_REASON,
    InfeasibilityProvenConclusion,
    OptimalProvenConclusion,
    PlanConclusion,
    SeededRunVote,
    SolverStatusWitnessFacts,
    UnprovenConclusion,
    conclude_with_solver,
    merge_seeded_runs,
    seeded_margin,
)
from backend.app.services.pac_allocator.seed_runs import fresh_seeds, run_seeds
from backend.app.services.pac_allocator.solver import DEFAULT_SOLVER_TIME_BUDGET_SECONDS, SolverRunResult, solve_policy_program

__all__ = ["plan_pac_allocation", "plan_rebalancing"]

logger = get_logger(__name__)

#: R1-A of project 67: the line of a search that ended holding only a plan the exact replay refuses (``_refused_plan``).
REFUSED_PLAN_EVENT = "Planner held only a plan the exact replay refuses"

_PRIMARY_SOLUTION_ID = "solution:primary"

# Phase-1 deployment answer. `deployment_omitted` states "we did not compute
# this", which is true: no second deploy-the-remainder optimization runs here.
# `primary_is_deployment` would assert an equivalence never established, which
# would be a claim rather than a report.
_DEPLOYMENT = DeploymentUnavailable(kind="unavailable", reason_code="allocation.deployment_omitted")


class SolverInfeasibilityContradictedError(ExactEvaluatorError):
    """SCIP reported the scenario infeasible, but doing nothing passes the exact replay.

    Doing nothing is itself a plan. If exact arithmetic accepts it, the
    scenario has a plan, and SCIP's verdict is wrong: its float arithmetic
    lost precision, as it can with amounts of around ten billion units of a
    currency. Publishing ``infeasibility_proven`` would state something false,
    so the error goes to the Tool, which reports ``execution_failed``, as it
    does for ``ExactReplayRejectedError``. The message names no amounts.
    """


@dataclass(frozen=True, slots=True)
class _Search:
    """What the search stage found, before any of it is trusted."""

    candidate: CandidateActionVector | None
    solver: SolverRunResult
    program: CompiledProgram | None = None


@dataclass(frozen=True, slots=True)
class _Product:
    """What differs between the two Tools, in one place: the wire classes of every result state and solution, the scenario
    basis, the solution's projection and what «no operation» means. Everything else is the shared body."""

    needs_input: type
    invalid: type
    unsupported: type
    no_op: type
    incumbent: type
    infeasible: type
    no_incumbent: type
    no_op_solution: type
    incumbent_solution: type
    basis: Callable[[ExactPlannerScenario, ExactEvaluation], object]
    solution_parts: Callable[[ExactPlannerScenario, ExactPolicyView, ExactEvaluation, tuple[ExactRoundingTopUp, ...], SolverRunResult], dict]
    is_no_op: Callable[[ExactEvaluation], bool]


@dataclass(frozen=True, slots=True)
class PlanReport:
    """A plan's wire result and what the wire cannot carry yet.

    ``limited_entries`` is the internal list of M20 (A3, project 67): the entries that carry a limit, when the result is
    ``ready_infeasible`` and the request has at least one limit; empty otherwise, and always empty with ``ready_no_incumbent``
    (a search that ran out of time says nothing about the limits). Contract 2.0.0 (A4) turns it into
    ``allocation.bounds_unsatisfiable``; until then the wire result is the one of 1.0.0.
    """

    result: PacPlannerResult | RebalancerPlannerResult
    limited_entries: tuple[LimitEntry, ...] = ()


def plan_pac_allocation(
    request: PacPlannerRequest,
    *,
    checkpoint: Checkpoint | None = None,
    solver_time_budget_seconds: float | None = None,
    progress: ProgressReporter | None = None,
) -> PacPlannerResult:
    """Plan a PAC allocation and return a wire result.

    Never raises on a planning outcome: an infeasible scenario and an exhausted
    budget are *results*, each with its own ``result_state``. A genuine
    contract violation propagates, and so do two defects of the search, which
    are not outcomes to answer with: ``ExactReplayRejectedError``, a SCIP plan
    the exact replay rejects for more than rounding (save the one the solver
    held for want of another, answered «no plan», R1-A), and
    ``SolverInfeasibilityContradictedError``, an infeasibility verdict on a
    scenario where doing nothing is a valid plan.

    ``solver_time_budget_seconds`` is the engine window the caller has already
    claimed. It matters more than it looks: the lexicographic cascade is what
    makes the answer unique, so a budget that truncates it at a different stage
    on a slower machine yields a *different plan for the same input*. Leaving it
    ``None`` keeps ``solver.py``'s own default, which is only correct for a
    caller that has no window to claim — every Tool caller has one.
    """
    return _plan(request, normalize_pac_plan, _PAC, checkpoint=checkpoint, solver_time_budget_seconds=solver_time_budget_seconds, progress=progress)


def plan_rebalancing(
    request: RebalancerPlannerRequest,
    *,
    checkpoint: Checkpoint | None = None,
    solver_time_budget_seconds: float | None = None,
    solver_window_seconds: float | None = None,
    progress: ProgressReporter | None = None,
    seeds: tuple[int, ...] | None = None,
) -> RebalancerPlannerResult:
    """Plan a rebalancing and return a wire result: ``plan_pac_allocation``'s body, with the Rebalancer's product.

    The same promises: a planning outcome is a result, never an exception; the same two defects of the search propagate;
    ``solver_time_budget_seconds`` is one run's limit and ``solver_window_seconds`` the whole window of its turns (lot
    TURNI; None: the limit itself). The basis publishes the request's fidelity as the request
    wrote it (a level, a custom ``λ``, «Target first»), which the exact scenario keeps only as ``λ``. ``seeds`` fixes the
    three runs' seeds (lot SEEDS, ``plan_exact_scenario``); None draws them.
    """
    product = _rebalancer_product(request.target_fidelity)
    return _plan(request, normalize_rebalancer_plan, product, checkpoint=checkpoint, solver_time_budget_seconds=solver_time_budget_seconds, solver_window_seconds=solver_window_seconds, progress=progress, seeds=seeds)


def _plan(request, normalize, product: _Product, *, checkpoint: Checkpoint | None, solver_time_budget_seconds: float | None, solver_window_seconds: float | None = None, progress: ProgressReporter | None = None, seeds: tuple[int, ...] | None = None):
    """The one body of both service functions: normalize, then a failure result or the plan. ``progress`` hears the phases
    (V2, ``progress.py``); a failure stops at ``validate``, the phase it is born in."""
    check_budget(checkpoint)
    report_phase(progress, "validate")
    normalized = normalize(request)
    # A failure has no exact scenario, so no scenario fingerprint: the field is empty, never the snapshot identifier (§6).
    snapshot = PlannerResultSnapshot(snapshot_id=request.snapshot.snapshot_id, request_fingerprint="")

    if not normalized.ready or normalized.normalized is None:
        return _failure_result(normalized.availability, snapshot, list(normalized.issues), product)

    return plan_exact_scenario(normalized.normalized, issues=tuple(normalized.issues), checkpoint=checkpoint, solver_time_budget_seconds=solver_time_budget_seconds, solver_window_seconds=solver_window_seconds, product=product, progress=progress, seeds=seeds).result


def plan_exact_scenario(
    scenario: ExactPlannerScenario,
    *,
    issues: tuple[PlannerIssue, ...] = (),
    checkpoint: Checkpoint | None = None,
    solver_time_budget_seconds: float | None = None,
    solver_window_seconds: float | None = None,
    product: _Product | None = None,
    progress: ProgressReporter | None = None,
    seeds: tuple[int, ...] | None = None,
) -> PlanReport:
    """Plan an already normalized scenario: search, replay, publish, and say which limits a «no solution» concerns.

    ``plan_pac_allocation`` is this after normalization. It is also the way in for a scenario the request cannot yet build
    (entry limits, until contract 2.0.0). Whether the limits are the cause of an infeasible model is known without searching
    again, because without limits doing nothing is always a valid plan (M20), and the
    ``SolverInfeasibilityContradictedError`` guard keeps that honest.

    Lot ZB of project 67 (specification §16.16): the model is prudent (row 6's reserves, the margins of the limit rows), so
    when it closes infeasible the solver runs once more, on the wide model, which holds every plan the replay could
    accept. Its «infeasible» is published as proven. Its plan is published, not proven, even when the rounding ends a cash
    cell beyond its limit by at most one minor unit per rounded posting, with a note on that cell
    (``allocation.cash_limit_exceeded_by_rounding``); the limit is read once the rounding top-ups are added (lot ZB-c), so
    a cell the top-up brings back inside its band carries the top-up alone. A plan the replay refuses beyond that is «no
    plan found», not proven.

    Lot SEEDS of project 67 (specification §16.11, §16.16): the Rebalancer plans three times, each run the whole path
    above with its own seed, in parallel (``seed_runs``), and publishes the run ``proof.merge_seeded_runs`` chooses: the
    lowest plan, «proven» only when two runs closed on it. ``seeds`` fixes them; None takes the test configuration's or
    three fresh random ones. One seed, or none (the PAC, which keeps SCIP's own), is one run, as before.

    Lot TURNI of project 67 (specification §16.22): ``solver_time_budget_seconds`` is one run's limit and
    ``solver_window_seconds`` the whole window its turns live in; a run that starts later has the smaller of its limit and
    the time left in the window (``seed_runs``). None for the window is the limit itself: a later run has the time left.
    """
    product = product or (_rebalancer_product(None) if scenario.product == "rebalancer" else _PAC)
    report_phase(progress, "model")
    view = build_exact_policy_view(scenario, purpose="primary")
    check_budget(checkpoint)
    run_seeds_of = _seeds_for(scenario, seeds)
    if len(run_seeds_of) < 2:
        return _single_run(scenario, view, issues, checkpoint, solver_time_budget_seconds, product, progress, seed=run_seeds_of[0] if run_seeds_of else None).report
    budget = DEFAULT_SOLVER_TIME_BUDGET_SECONDS if solver_time_budget_seconds is None else solver_time_budget_seconds

    def one_run(seed: int, forward: ProgressReporter | None, run_budget: float) -> _RunOutcome:
        # ``run_budget`` is this run's own limit: the whole limit in its turn, or what the window has left (lot TURNI).
        return _single_run(scenario, view, issues, None, run_budget, product, forward, seed=seed)

    # «Impossible» needs two runs: after one, the next starts even with no time left (lot SEEDS-c).
    runs = run_seeds(one_run, seeds=run_seeds_of, time_budget_seconds=budget, window_seconds=solver_window_seconds, checkpoint=checkpoint, progress=progress, start_next_after=_answered_impossible)
    report_phase(progress, "verify")
    check_budget(checkpoint)
    published = _merged_report(runs, scenario)
    report_phase(progress, "report")
    return published


@dataclass(frozen=True, slots=True)
class _RunOutcome:
    """One run of ``plan_exact_scenario``'s path, and what the merge of the seeded runs reads of it (lot SEEDS)."""

    report: PlanReport
    origin: Literal["prudent", "wide", "none"] = "none"
    closed: bool = False
    value: Fraction | None = None
    band: Fraction = Fraction(0)
    #: Lot MG: the prudent model's first-stage lower bound (SCIP's dual) in the unit of ``value``, None without one; and the
    #: stage's scale, SCIP's unit over that one (1 for a score in euros, 1/F for «Target first»).
    bound: Fraction | None = None
    scale: Fraction = Fraction(1)
    #: R1-A: the run's search ended holding only a plan the exact replay refuses, answered «no plan» (``_refused_plan``).
    refused: bool = False


class SeededRunsFailedError(RuntimeError):
    """Lot SEEDS: no run of the Rebalancer's three could be published (all failed, or a single «impossible» stood alone:
    the contract cannot publish an infeasible run as «no plan», lot SEEDS-b). The Tool reports it as ``execution_failed``,
    retryable; the message names no amounts."""


def _answered_impossible(outcome: _RunOutcome) -> bool:
    return outcome.report.result.result_state == "ready_infeasible"


def _seeds_for(scenario: ExactPlannerScenario, seeds: tuple[int, ...] | None) -> tuple[int, ...]:
    """The runs' seeds: none for the PAC (one run, SCIP's own seed); the caller's, the test configuration's, or three fresh
    random ones for the Rebalancer."""
    if scenario.product != "rebalancer":
        return ()
    if seeds is not None:
        return seeds
    fixed = planner_config.planner_fixed_seeds()
    return fresh_seeds() if fixed is None else fixed


def _margin_money(margin: Fraction, scale: Fraction, quantum: Fraction) -> Fraction:
    """Lot MG: a margin in the first stage's unit, in the valuation currency (SCIP's unit: euros for a score, D/F for
    «Target first»), posted up to the currency's minor unit, never zero: a margin at most zero reads one minor unit."""
    money = margin * scale
    if money <= 0:
        return quantum
    posted = post_ceiling(ExactRatio(money.numerator, money.denominator), ExactRatio(quantum.numerator, quantum.denominator)).posted
    return Fraction(posted.numerator, posted.denominator)


def _merged_report(runs, scenario: ExactPlannerScenario) -> PlanReport:
    """Publish the run ``proof.merge_seeded_runs`` chooses, its own «proven» downgraded when no second run confirms it, and a
    plan not proven with its margin (lot MG) when two runs bound it."""
    votes = []
    for run in runs:
        outcome = run.result
        if run.failure is not None or outcome is None:
            votes.append(SeededRunVote(seed=run.seed, failed=True))
            continue
        infeasible = outcome.report.result.result_state == "ready_infeasible"
        votes.append(SeededRunVote(seed=run.seed, origin=outcome.origin, closed=outcome.closed, infeasible=infeasible, value=outcome.value, band=outcome.band, bound=outcome.bound))
    verdict = merge_seeded_runs(votes)
    margin = seeded_margin(votes, verdict)
    # No amount on the line (lot LOGS of project 67): a run's value and bound, and the margin, are money of the user's
    # portfolio. Which run closed, and how long each took, is what a diagnosis of the seeds reads.
    logger.info(
        "Rebalancer seeded runs",
        runs=[{"seed": vote.seed, "origin": vote.origin, "closed": vote.closed, "infeasible": vote.infeasible, "refused": run.result is not None and run.result.refused, "seconds": run.seconds, "failure": run.failure} for vote, run in zip(votes, runs, strict=True)],
        state=verdict.state,
        chosen=None if verdict.index is None else votes[verdict.index].seed,
        downgrade=verdict.downgrade,
    )
    if verdict.index is None:
        raise SeededRunsFailedError(f"no run of the Rebalancer could be published ({verdict.state})")
    outcome = runs[verdict.index].result
    chosen = outcome.report
    if not verdict.downgrade and margin is None:
        return chosen
    result = chosen.result
    reason = PROOF_NOT_CONFIRMED_REASON if verdict.downgrade else result.proof.reason_code
    quantum = next(item.minor_unit for item in scenario.currency_specs if item.currency == scenario.valuation_currency)
    money = None if margin is None else _margin_money(margin, outcome.scale, Fraction(quantum.numerator, quantum.denominator))
    proof = NotProvenProof(kind="not_proven", reason_code=reason, margin=None if money is None else ProofMargin(amount=format(Decimal(money.numerator) / Decimal(money.denominator), "f"), currency=scenario.valuation_currency))
    return PlanReport(result=type(result).model_validate(result.model_dump() | {"proof": proof.model_dump()}), limited_entries=chosen.limited_entries)


def _single_run(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    issues: tuple[PlannerIssue, ...],
    checkpoint: Checkpoint | None,
    solver_time_budget_seconds: float | None,
    product: _Product,
    progress: ProgressReporter | None,
    *,
    seed: int | None = None,
) -> _RunOutcome:
    """One run of the path ``plan_exact_scenario`` describes: the prudent model, the wide one if needed, the replay, the
    result; with ``seed`` set on SCIP and published, or SCIP's own."""
    started = time.monotonic()
    search = _search(scenario, view, checkpoint=checkpoint, solver_time_budget_seconds=solver_time_budget_seconds, progress=progress, seed=seed)
    issue_list = list(issues)
    if search.candidate is None and search.solver.outcome == "reported_infeasible":
        # Lot ZB (specification §16.16): the model is prudent, so its «infeasible» says nothing about the request; the wide
        # model's does.
        budget = DEFAULT_SOLVER_TIME_BUDGET_SECONDS if solver_time_budget_seconds is None else solver_time_budget_seconds
        outer = _search(scenario, view, checkpoint=checkpoint, solver_time_budget_seconds=max(budget - (time.monotonic() - started), budget / 10), progress=progress, outer=True, seed=seed)
        if outer.candidate is not None:
            evaluation = evaluate_exact_candidate(scenario, view, outer.candidate, checkpoint=checkpoint)
            try:
                # A cash limit missed by the plan's rounding, at most one minor unit per rounded posting, is a note.
                # Lot ZB-c: the limits are read on the cash once the top-ups are added, so the top-ups come first.
                top_ups = rounding_top_ups(scenario, evaluation, tolerated=frozenset({"ENTRY_VALUE_WITHIN_LIMITS"}))
                overshoots = cash_limit_overshoots(scenario, evaluation, top_ups)
            except ExactReplayRejectedError:
                # The wide model admits plans the replay refuses: this one is «no plan found», never a failure.
                outer = _Search(candidate=None, solver=outer.solver, program=outer.program)
            else:
                # A plan of the wide model is published; ``proof.py`` says nothing proves it the best.
                issue_list.extend(cash_limit_exceeded_by_rounding_issue(item.broker_id, item.currency, _fixed_decimal(item.amount)) for item in overshoots)
                _note_solver_error(outer, issue_list)
                report_phase(progress, "verify")
                conclusion = _conclude(view, outer, published=outer.candidate)
                check_budget(checkpoint)
                report_phase(progress, "report")
                published = PlanReport(result=_ready_result(scenario, view, outer, evaluation, conclusion, issue_list, top_ups, product))
                return _RunOutcome(report=published, origin="wide", value=_first_stage_value(scenario, view, evaluation))
        search = outer
    _note_solver_error(search, issue_list)

    if search.candidate is None:
        report_phase(progress, "verify")
        result = _no_incumbent_result(scenario, view, search, issue_list, product, progress)
        # Only a proven «no solution» names the limits; a search that ran out of time says nothing about them.
        return _RunOutcome(report=PlanReport(result=result, limited_entries=limited_entries(scenario) if isinstance(result, product.infeasible) else ()))

    # The single non-negotiable hop: nothing is published that exact
    # arithmetic has not re-derived from the candidate itself. Its verdict is
    # final: a rounding deficit within the threshold comes back as top-ups,
    # any other rejection raises, save one: the plan the solver itself held for
    # want of another, refused by its replay already (R1-A of project 67).
    report_phase(progress, "verify")
    evaluation = evaluate_exact_candidate(scenario, view, search.candidate, checkpoint=checkpoint)
    try:
        top_ups = rounding_top_ups(scenario, evaluation)
    except ExactReplayRejectedError as exc:
        if search.solver.held_unpublishable_at is None:
            raise
        return _refused_plan(scenario, view, search, exc, issue_list, product, progress)

    conclusion = _conclude(view, search, published=search.candidate)
    check_budget(checkpoint)
    report_phase(progress, "report")
    published = PlanReport(result=_ready_result(scenario, view, search, evaluation, conclusion, issue_list, top_ups, product))
    bound, scale = _first_stage_bound(search)
    return _RunOutcome(report=published, origin="prudent", closed=isinstance(conclusion, OptimalProvenConclusion), value=_first_stage_value(scenario, view, evaluation), band=_first_stage_band(search), bound=bound, scale=scale)


def _refused_plan(scenario: ExactPlannerScenario, view: ExactPolicyView, search: _Search, error: ExactReplayRejectedError, issues: list[PlannerIssue], product: _Product, progress: ProgressReporter | None) -> _RunOutcome:
    """R1-A of project 67: the search ended holding only the plan it kept for want of another, which the exact replay
    refuses. That is «no plan» (not proven, the stop reason the stages give), as the wide model already answers, never a
    failure: the review's «execution_failed» on a valid draft. One log line says what was refused, a WARNING when stage 1
    stopped at a limit, an ERROR when it closed (then the prudent model's own optimum is refused, a defect of the model).
    The replay's message names rules, cells and pools, never amounts (``evaluator.rounding_top_ups``). A seeded run of the
    Rebalancer logs it in its own process; the merge's line carries the run as ``refused``."""
    stage_one_closed = bool(search.solver.stages) and search.solver.stages[0].status == "finished"
    log = logger.error if stage_one_closed else logger.warning
    log(REFUSED_PLAN_EVENT, error_type=type(error).__qualname__, reason=str(error), stage_ordinal=search.solver.held_unpublishable_at, stage_one_closed=stage_one_closed)
    result = _no_incumbent_result(scenario, view, _Search(candidate=None, solver=search.solver, program=search.program), issues, product, progress)
    return _RunOutcome(report=PlanReport(result=result), refused=True)


def _first_stage_value(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation) -> Fraction:
    """The published plan's first objective, valued exactly as the solver sees it (``evaluation.solver_view``): the number
    the seeded runs compare (the consultant's definition of 17/11)."""
    code = _objective_codes(view)[0]
    value = solver_view_objectives(scenario, view, evaluation)[code]
    return Fraction(value.numerator, value.denominator)


def _first_stage_bound(search: _Search) -> tuple[Fraction | None, Fraction]:
    """Lot MG: the first stage's lower bound (SCIP's dual, None when it is not finite) in the unit of
    ``_first_stage_value``, and the stage's scale."""
    if not search.solver.stages:
        return None, Fraction(1)
    first = search.solver.stages[0]
    scale = Fraction(first.scale)
    return (None if first.dual is None else Fraction(first.dual) / scale), scale


def _first_stage_band(search: _Search) -> Fraction:
    """How far below the truth SCIP's first-stage value may sit (its quadratic rows), in the unit of
    ``_first_stage_value``: SCIP minimizes ``scale ×`` the exact value, so its band is divided by the scale."""
    if search.program is None or not search.program.objective_stages:
        return Fraction(0)
    stage = search.program.objective_stages[0]
    return Fraction(stage.band) / stage.scale


def _note_solver_error(search: _Search, issues: list[PlannerIssue]) -> None:
    """Lot SE: SCIP failed inside a stage after a plan was held (``solver._optimize``); the wire names it."""
    if any(stage.scip_status == "solver_error" for stage in search.solver.stages):
        issues.append(solver_numerical_error_issue())


def _fixed_decimal(value: ExactRatio) -> str:
    """An exact amount with a finite decimal expansion, as the wire's ``PlannerFixedDecimal`` writes it."""
    return format(Decimal(value.numerator) / Decimal(value.denominator), "f")


def _search(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    *,
    checkpoint: Checkpoint | None,
    solver_time_budget_seconds: float | None = None,
    progress: ProgressReporter | None = None,
    outer: bool = False,
    seed: int | None = None,
) -> _Search:
    """Compile the view and run SCIP, the only production search engine (D-X1).

    There is no other route and no size threshold: the exhaustive oracle is a
    test instrument that production cannot reach, and SCIP's cost grows with
    the number of decisions, not with the size of the domain — and far faster
    when several brokers sell the same asset (see
    ``planner_report.build_stop_reason``). SCIP's candidate stays a proposal
    until the Decimal replay accepts it, and its statuses become a proof only
    through ``proof.conclude_with_solver``.
    """
    program = compile_policy_program(scenario, view, outer=True) if outer else compile_policy_program(scenario, view)
    solver = solve_policy_program(
        program,
        checkpoint=checkpoint,
        progress=progress,
        seed=seed,
        **({} if solver_time_budget_seconds is None else {"time_budget_seconds": solver_time_budget_seconds}),
    )
    return _Search(candidate=solver.candidate, solver=solver, program=program)


def _objective_codes(view: ExactPolicyView) -> tuple[ExactObjectiveCode, ...]:
    """The view's objectives in cascade order, as ``build_objective_results`` publishes them."""
    return tuple(ref.code for ref in sorted(view.objectives, key=lambda ref: ref.ordinal))


def _conclude(view: ExactPolicyView, search: _Search, *, published: CandidateActionVector | None) -> PlanConclusion:
    """Decide the proof, which only ``proof.py`` may do.

    ``published`` is the candidate this result publishes — SCIP's, after the
    Decimal replay accepted it — or ``None`` when nothing is published.
    """
    return conclude_with_solver(search.solver, objective_codes=_objective_codes(view), published=published, outer_model=search.program is not None and search.program.outer)


def _ready_result(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    search: _Search,
    evaluation: ExactEvaluation,
    conclusion: PlanConclusion,
    issues: list[PlannerIssue],
    top_ups: tuple[ExactRoundingTopUp, ...],
    product: _Product,
):
    common = _common_ready_fields(scenario, view, search, evaluation, issues, product)
    proof = _wire_proof(conclusion, rebalancer=product.incumbent is RebalancerPlannerReadyIncumbentResult)
    parts = product.solution_parts(scenario, view, evaluation, top_ups, search.solver)

    # The no-op decision is made *before* choosing the solution model, not
    # after: an incumbent solution requires at least one step while a no-op
    # solution requires every action list to be empty, so the two are
    # mutually exclusive shapes over the same projected rows rather than one
    # being convertible into the other.
    if product.is_no_op(evaluation):
        return product.no_op(result_state="ready_no_op", outcome="no_op", proof=proof, primary_solution=product.no_op_solution(**parts), deployment=_DEPLOYMENT, **common)
    return product.incumbent(result_state="ready_incumbent", outcome="incumbent_found", proof=proof, primary_solution=product.incumbent_solution(**parts), deployment=_DEPLOYMENT, **common)


def _no_incumbent_result(scenario: ExactPlannerScenario, view: ExactPolicyView, search: _Search, issues: list[PlannerIssue], product: _Product, progress: ProgressReporter | None = None):
    """No publishable plan: SCIP proved there is none, or found none in time.

    ``ready_infeasible`` needs an ``InfeasibilityProvenProof``, and only
    ``proof.conclude_with_solver`` can conclude one: SCIP closed the first,
    still-global stage ``infeasible``. Its ``stop_reason`` is ``completed``
    because the search ended on that verdict, and ``build_stop_reason``
    already says so — an infeasible stage is not an unfinished one.

    That verdict is checked before it is published. The do-nothing plan is
    evaluated here anyway, for the scenario basis; if exact arithmetic finds
    it valid and feasible, the scenario does have a plan, and
    ``SolverInfeasibilityContradictedError`` is raised instead.

    Everything else is ``ready_no_incumbent`` with ``not_proven``: a limit that
    left no solution. A SCIP plan the Decimal replay rejects lands here only
    when the solver held it for want of another (R1-A, ``_refused_plan``);
    otherwise it is published with its rounding top-ups, or
    ``plan_pac_allocation`` raises ``ExactReplayRejectedError``.
    """
    evaluation = evaluate_do_nothing(scenario, view)
    conclusion = _conclude(view, search, published=None)
    if isinstance(conclusion, InfeasibilityProvenConclusion) and evaluation.candidate_valid and evaluation.feasible:
        raise SolverInfeasibilityContradictedError("the solver reported the scenario infeasible, but the do-nothing plan passes the exact replay")

    if isinstance(conclusion, InfeasibilityProvenConclusion):
        # M20: a proven «no solution» with limits in the request names every entry that carries one; no second search says which is the cause.
        issues = [*issues, *(bounds_unsatisfiable_issue(entry.kind, entry.asset_id if entry.kind == "asset" else f"{entry.broker_id}:{entry.currency}") for entry in limited_entries(scenario))]
    report_phase(progress, "report")
    common = _common_ready_fields(scenario, view, search, evaluation, issues, product)
    if isinstance(conclusion, InfeasibilityProvenConclusion):
        return product.infeasible(result_state="ready_infeasible", outcome="infeasible_proven", proof=_wire_infeasibility(conclusion), **common)

    return product.no_incumbent(result_state="ready_no_incumbent", outcome="no_incumbent", proof=NotProvenProof(kind="not_proven", reason_code=UnprovenConclusion().reason_code), **common)


def _common_ready_fields(scenario, view, search: _Search, evaluation: ExactEvaluation, issues: list[PlannerIssue], product: _Product) -> dict:
    return {
        "operation": "plan",
        "availability": "ready",
        "snapshot": report.build_result_snapshot(scenario, view),
        "catalogs": report.build_planner_catalogs(scenario),
        "provenance": report.build_planner_provenance(scenario),
        "scenario_basis": product.basis(scenario, evaluation),
        "stop_reason": report.build_stop_reason(search.solver),
        "solver_evidence": report.build_solver_evidence(scenario, view, search.solver),
        "issues": issues,
    }


def _executable_steps(scenario: ExactPlannerScenario, ledger_rows: list, top_up_rows: list, funding_actions: list, transfers: list, conversions: list, order_rows: list) -> tuple[list, list, list, list]:
    """Number the plan's steps in an order the balances can follow (contract §6.3, specification §15 n. 7; F4a of project
    67): the builders number in a fixed order of kinds, this renumbers from the ledger's initial balances
    (``plan_sequence``), keeps each section ascending as the schema wants, and checks the invariant on the result: replayed
    in its numbers, the plan never takes a balance below zero and ends at the ledger's final balances. A plan no order can
    pay raises ``PlanNotExecutableError``: a defect, never a plan to publish. A rounding top-up is cash the user adds to its
    cell for the plan to execute (``PlannerRoundingTopUp``): it counts from the start, and the cell ends at zero instead of
    the ledger's negative balance."""
    cells = {cash.cash_id: (cash.broker_id, cash.selected.currency) for cash in scenario.existing_cash}
    added = {(row.broker_id, row.currency): Fraction(Decimal(row.amount)) for row in top_up_rows}
    initial = {(row.broker_id, row.currency): Fraction(Decimal(row.initial_selected)) + added.get((row.broker_id, row.currency), Fraction(0)) for row in ledger_rows}
    final = {(row.broker_id, row.currency): Fraction(Decimal(row.final_physical)) + added.get((row.broker_id, row.currency), Fraction(0)) for row in ledger_rows}
    flows = plan_sequence.step_flows(funding_actions, transfers, conversions, order_rows, cells)
    number = {flow.key: position for position, flow in enumerate(plan_sequence.executable_order(initial, flows), start=1)}

    def renumber(rows: list, key: str) -> list:
        renumbered = [row.model_copy(update={"sequence": number[getattr(row, key)]}) if getattr(row, key) in number else row for row in rows]
        numbered = sorted((row for row in renumbered if row.sequence is not None), key=lambda row: row.sequence)
        return numbered + [row for row in renumbered if row.sequence is None]

    funding_actions, transfers, conversions, order_rows = renumber(funding_actions, "action_id"), renumber(transfers, "transfer_id"), renumber(conversions, "conversion_id"), renumber(order_rows, "order_id")
    plan_sequence.assert_executable(initial, plan_sequence.step_flows(funding_actions, transfers, conversions, order_rows, cells), final)
    return funding_actions, transfers, conversions, order_rows


def _build_solution_parts(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation, top_ups: tuple[ExactRoundingTopUp, ...], _solver: SolverRunResult | None = None) -> dict:
    """Assemble the primary solution.

    One ``_SequenceAllocator`` is shared across funding, manual conversions
    and order rows — not one per section. The schema wants ids and sequences
    unique across the sections *and* each section internally ascending;
    separate counters would collide on row one, and a single dense counter
    satisfies both at once. The builders number in a fixed order (funding, the conversions the user performs, the orders);
    ``_executable_steps`` then renumbers the steps in an order the balances can follow.
    """
    sequence = report._SequenceAllocator()
    ledger_rows = report.build_ledger_rows(evaluation)
    top_up_rows = report.build_rounding_top_ups(scenario, top_ups)
    funding_actions = report.build_funding_actions(scenario, evaluation, sequence)
    conversions = report.build_conversions(scenario, evaluation, sequence)
    order_rows = report.build_order_rows(scenario, evaluation, sequence)
    funding_actions, _, conversions, order_rows = _executable_steps(scenario, ledger_rows, top_up_rows, funding_actions, [], conversions, order_rows)
    return {
        "solution_id": _PRIMARY_SOLUTION_ID,
        "solution_kind": "primary",
        "validation": "decimal_verified",
        "asset_rows": report.build_asset_rows(scenario, evaluation),
        "cash_rows": report.build_cash_rows(scenario, evaluation),
        "funding_actions": funding_actions,
        "conversions": conversions,
        "order_rows": order_rows,
        "ledger_rows": ledger_rows,
        "rounding_top_ups": top_up_rows,
        "exposure_rows": report.build_exposure_rows(scenario, evaluation),
        "accounting": report.build_accounting(scenario, evaluation),
        "costs": report.build_costs(scenario, evaluation),
        "plan_accounts": report.build_plan_accounts(scenario, evaluation),
        "objectives": report.build_objective_results(scenario, view, evaluation),
    }


def _rebalancer_solution_parts(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation, top_ups: tuple[ExactRoundingTopUp, ...], solver: SolverRunResult) -> dict:
    """Assemble a Rebalancer solution (contract §6): the PAC's shared rows plus the items on ``F``, the transfers, the plan
    accounts and the score. One step counter, in an order the balances can follow (``_executable_steps``): an exchange
    before a transfer that spends its proceeds, a transfer before the exchange or purchase that spends what it brings. The
    tax parts are empty until a plan sells (C1, C2 of project 67)."""
    sequence = report._SequenceAllocator()
    ledger_rows = report.build_ledger_rows(evaluation)
    top_up_rows = report.build_rounding_top_ups(scenario, top_ups)
    funding_actions = report.build_funding_actions(scenario, evaluation, sequence)
    transfers = rebalancer_report.build_transfers(evaluation, sequence)
    conversions = report.build_conversions(scenario, evaluation, sequence)
    order_rows = report.build_order_rows(scenario, evaluation, sequence)
    funding_actions, transfers, conversions, order_rows = _executable_steps(scenario, ledger_rows, top_up_rows, funding_actions, transfers, conversions, order_rows)
    return {
        "solution_id": _PRIMARY_SOLUTION_ID,
        "solution_kind": "primary",
        "validation": "decimal_verified",
        "asset_rows": rebalancer_report.build_rebalancer_asset_rows(scenario, evaluation),
        "cash_rows": rebalancer_report.build_cash_item_rows(scenario, evaluation),
        "uninvested_row": rebalancer_report.build_uninvested_row(scenario, evaluation),
        "funding_actions": funding_actions,
        "conversions": conversions,
        "transfers": transfers,
        "order_rows": order_rows,
        "ledger_rows": ledger_rows,
        "rounding_top_ups": top_up_rows,
        "exposure_rows": rebalancer_report.build_rebalancer_exposure_rows(scenario, evaluation, top_ups),
        "accounting": report.build_accounting(scenario, evaluation),
        "costs": report.build_costs(scenario, evaluation),
        "plan_accounts": report.build_plan_accounts(scenario, evaluation),
        "score": rebalancer_report.build_score(scenario, view, evaluation, solver),
        "tax_basket_rows": [],
        "tax_scope_rows": [],
        "tax_reserves": [],
        "asset_type_tax_rows": [],
        "objectives": report.build_objective_results(scenario, view, evaluation),
    }


def _is_no_op(evaluation: ExactEvaluation) -> bool:
    return not evaluation.orders and not evaluation.funding_transfers and not evaluation.fx


def _is_rebalancer_no_op(evaluation: ExactEvaluation) -> bool:
    """A plan of transfers alone is not «no operation» (contract §6.3)."""
    return _is_no_op(evaluation) and not any(posting.family == "transfer_out" and posting.exact_amount > 0 for posting in evaluation.postings)


_PAC = _Product(
    needs_input=PacPlannerNeedsInputResult,
    invalid=PacPlannerInvalidResult,
    unsupported=PacPlannerUnsupportedResult,
    no_op=PacPlannerReadyNoOpResult,
    incumbent=PacPlannerReadyIncumbentResult,
    infeasible=PacPlannerReadyInfeasibleResult,
    no_incumbent=PacPlannerReadyNoIncumbentResult,
    no_op_solution=PacNoOpSolution,
    incumbent_solution=PacIncumbentSolution,
    basis=report.build_scenario_basis,
    solution_parts=_build_solution_parts,
    is_no_op=_is_no_op,
)


def _rebalancer_product(fidelity) -> _Product:
    """The Rebalancer's product; ``fidelity`` is the request's, published by the basis as the request wrote it. Without a
    request (a scenario built by hand) it is read back from the exact fidelity, «Balanced» for ``λ`` = 1."""

    def basis(scenario: ExactPlannerScenario, evaluation: ExactEvaluation):
        return rebalancer_report.build_rebalancer_scenario_basis(scenario, evaluation, fidelity if fidelity is not None else rebalancer_report.wire_fidelity(scenario.target_fidelity))

    return _Product(
        needs_input=RebalancerPlannerNeedsInputResult,
        invalid=RebalancerPlannerInvalidResult,
        unsupported=RebalancerPlannerUnsupportedResult,
        no_op=RebalancerPlannerReadyNoOpResult,
        incumbent=RebalancerPlannerReadyIncumbentResult,
        infeasible=RebalancerPlannerReadyInfeasibleResult,
        no_incumbent=RebalancerPlannerReadyNoIncumbentResult,
        no_op_solution=RebalancerNoOpSolution,
        incumbent_solution=RebalancerIncumbentSolution,
        basis=basis,
        solution_parts=_rebalancer_solution_parts,
        is_no_op=_is_rebalancer_no_op,
    )


def _wire_proof(conclusion: PlanConclusion, *, rebalancer: bool = False):
    """Project a published plan's conclusion onto the wire union; the Rebalancer's optimum has no ``tie_break_closed``."""
    if isinstance(conclusion, OptimalProvenConclusion) and rebalancer:
        return RebalancerOptimalProvenProof(kind="optimal_proven", proof_source="solver_status", witness=_wire_solver_witness(conclusion.witness))
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


def _failure_result(availability: str, snapshot: PlannerResultSnapshot, issues: list[PlannerIssue], product: _Product = None):
    """Return the failure result matching the normalizer's availability.

    The schema requires a failure result to carry an error issue whose kind
    matches its availability, so this never invents one: if normalization
    said ``invalid`` it also produced the controlling issue.
    """
    product = product or _PAC
    if availability == "needs_input":
        return product.needs_input(operation="plan", result_state="needs_input", availability="needs_input", snapshot=snapshot, issues=issues)
    if availability == "unsupported":
        return product.unsupported(operation="plan", result_state="unsupported", availability="unsupported", snapshot=snapshot, issues=issues)
    return product.invalid(operation="plan", result_state="invalid", availability="invalid", snapshot=snapshot, issues=issues)
