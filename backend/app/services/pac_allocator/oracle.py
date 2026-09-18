"""Exhaustive oracle for small-domain exact PAC/Rebalancer policy views.

Enumerates every admissible discrete candidate for one `ExactPolicyView`,
replays each candidate through `evaluate_exact_candidate` (the same exact
Decimal/`ExactRatio` accounting used everywhere else in this package), and
returns the lexicographically best feasible candidate together with the
counts needed to build a wire `ExhaustiveOracleWitness`.

This module has **zero SCIP/solver dependency** by design — see
`LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/
plan-phase00Step3PacRebalancerSolverPolicies.prompt.md` §16.5 step 1. It
gives an honest `optimal_proven`/`infeasible_proven` result on small toy
scenarios before any compiler/solver exists, and later cross-checks a
solver incumbent on domains small enough to enumerate exhaustively. Whether
and when that cross-check happens is `proof.py`'s decision (not yet
built): this module only reports facts (candidate counts, the best
candidate/evaluation found) and never assembles a wire proof itself.

The lexicographic comparison follows
`plan-phase00PacRebalancerPolicies.prompt.md` §1.2-1.3 exactly: sequential
`argmin` per objective stage in ascending ordinal order, then the
precomputed canonical tie-break vector — never a weighted scalar, never an
economic epsilon.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product as _cartesian_product

from backend.app.services.pac_allocator.evaluator import (
    ExactEvaluatorError,
    evaluate_exact_candidate,
)
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    Checkpoint,
    DecisionAccess,
    ExactEvaluation,
    ExactObjectiveCode,
    ExactPlannerScenario,
    ExactPolicyView,
    ObjectiveRef,
    check_budget,
)

__all__ = [
    "MAX_EXHAUSTIVE_ORACLE_CANDIDATES",
    "OracleDomainTooLargeError",
    "OracleResult",
    "estimate_oracle_domain_size",
    "run_exhaustive_oracle",
]

# Internal safety constant, deliberately not wire-visible (Step3 plan
# §16.7 Q3): callers decide what "too large" means for them (fall back to
# solver-only, report `not_proven`) — this module only refuses to
# enumerate past this point so it can never hang the process on a
# real-sized scenario.
MAX_EXHAUSTIVE_ORACLE_CANDIDATES = 200_000


class OracleDomainTooLargeError(ExactEvaluatorError):
    """Raised when a policy view's discrete domain exceeds the safety cap."""


@dataclass(frozen=True, slots=True)
class OracleResult:
    """Exhaustive-search outcome for one `ExactPolicyView`.

    `best_candidate`/`best_evaluation` are `None` iff `feasible_candidates`
    is zero, i.e. the view is exhaustively proven infeasible.
    `objective_codes` is ordered by ascending stage ordinal, matching the
    order `ExhaustiveOracleWitness.objective_codes` expects on the wire.
    """

    view_id: str
    enumerated_candidates: int
    feasible_candidates: int
    objective_codes: tuple[ExactObjectiveCode, ...]
    best_candidate: CandidateActionVector | None
    best_evaluation: ExactEvaluation | None


def _decision_value_range(access: DecisionAccess) -> tuple[int, ...]:
    """Return every quanta value the oracle must try for one decision.

    `disabled` and `frozen_exact` decisions are already fixed by the policy
    view (e.g. a `deployment` view freezes funding/FX/SELL) — trying any
    other value would only manufacture `CANDIDATE_*` contract conflicts, so
    the oracle enumerates a single point for them instead of the full
    `[lower_quanta, upper_quanta]` span that `mutable`/`additive_only`
    decisions use.
    """
    if access.mode == "disabled":
        return (0,)
    if access.mode == "frozen_exact":
        if access.frozen_quanta is None:
            raise OracleDomainTooLargeError(f"frozen_exact decision {access.decision_id!r} is missing frozen_quanta")
        return (access.frozen_quanta,)
    return tuple(range(access.lower_quanta, access.upper_quanta + 1))


def estimate_oracle_domain_size(view: ExactPolicyView) -> int:
    """Return the exact candidate count `run_exhaustive_oracle` would try.

    Callers use this to decide, before calling `run_exhaustive_oracle`,
    whether a view's domain is small enough to attempt. That routing
    decision is internal (never a wire-visible contract) — see plan
    §16.7 Q3.
    """
    size = 1
    for access in view.decisions:
        size *= len(_decision_value_range(access))
    return size


def _ordered_objective_refs(view: ExactPolicyView) -> tuple[ObjectiveRef, ...]:
    """Return `view.objectives` sorted by ascending ordinal.

    `ExactPolicyView.__post_init__` already enforces that `objectives`
    carries unique contiguous ordinals starting at one, but that check
    does not by itself guarantee storage order matches ordinal order —
    this sorts explicitly rather than trusting tuple position, so a future
    refactor of `_build_objective_refs` cannot silently break the
    lexicographic order used here.
    """
    return tuple(sorted(view.objectives, key=lambda ref: ref.ordinal))


def _lexicographic_key(
    evaluation: ExactEvaluation,
    ordered_ref_ids: tuple[str, ...],
) -> tuple[tuple, tuple[int, ...]]:
    """Build the total-order sort key: objective stages, then canonical tie.

    Every `ExactEvaluation` produced for the same view carries
    `canonical_tie_quanta` in the same decision order, so comparing those
    tuples lexicographically after the objective stages reproduces the
    `argmin_lex` pipeline exactly (never a weighted scalar).
    """
    values_by_ref_id = {item.ref_id: item.value for item in evaluation.objectives}
    stage_values = tuple(values_by_ref_id[ref_id] for ref_id in ordered_ref_ids)
    return stage_values, evaluation.canonical_tie_quanta


def run_exhaustive_oracle(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    *,
    checkpoint: Checkpoint | None = None,
    max_candidates: int = MAX_EXHAUSTIVE_ORACLE_CANDIDATES,
) -> OracleResult:
    """Enumerate every candidate for `view` and return the lexicographic best.

    Reuses `evaluate_exact_candidate` for every candidate — this module
    never re-derives feasibility or objective values independently, it only
    searches and compares already-trusted evaluations. Raises
    `OracleDomainTooLargeError` rather than enumerating past
    `max_candidates`; callers choose the fallback (this is deliberately not
    a silent truncation, which would corrupt the "exhaustive" guarantee the
    proof layer relies on).
    """
    check_budget(checkpoint)
    domain_size = estimate_oracle_domain_size(view)
    if domain_size > max_candidates:
        raise OracleDomainTooLargeError(f"policy view {view.view_id!r} has {domain_size} candidates, exceeding the exhaustive-oracle safety cap of {max_candidates}")

    ordered_refs = _ordered_objective_refs(view)
    ordered_ref_ids = tuple(ref.ref_id for ref in ordered_refs)
    ordered_codes = tuple(ref.code for ref in ordered_refs)

    # `view.decisions` is already canonically sorted by decision_id (an
    # `ExactPolicyView` invariant), so decision_ids/value_ranges preserve
    # that order and every candidate built below is canonical without an
    # extra sort.
    decision_ids = tuple(access.decision_id for access in view.decisions)
    value_ranges = tuple(_decision_value_range(access) for access in view.decisions)

    enumerated = 0
    feasible = 0
    best_key: tuple[tuple, tuple[int, ...]] | None = None
    best_candidate: CandidateActionVector | None = None
    best_evaluation: ExactEvaluation | None = None

    for combination in _cartesian_product(*value_ranges):
        check_budget(checkpoint)
        enumerated += 1
        candidate = CandidateActionVector(
            view_id=view.view_id,
            candidate_id=f"oracle:{view.view_id}:{enumerated}",
            decisions=tuple(CandidateDecision(decision_id=decision_id, quanta=quanta) for decision_id, quanta in zip(decision_ids, combination, strict=True)),
        )
        evaluation = evaluate_exact_candidate(scenario, view, candidate, checkpoint=checkpoint)
        if not evaluation.feasible:
            continue
        feasible += 1
        key = _lexicographic_key(evaluation, ordered_ref_ids)
        if best_key is None or key < best_key:
            best_key = key
            best_candidate = candidate
            best_evaluation = evaluation

    return OracleResult(
        view_id=view.view_id,
        enumerated_candidates=enumerated,
        feasible_candidates=feasible,
        objective_codes=ordered_codes,
        best_candidate=best_candidate,
        best_evaluation=best_evaluation,
    )
