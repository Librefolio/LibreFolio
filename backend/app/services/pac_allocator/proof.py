"""Proof semantics for the PAC/Rebalancer planner.

This module decides the *third* of the three independent dimensions of a
ready result: incumbent validation (``decimal_verified``) is
``evaluator.py``'s job, the floating solver report (statuses, bounds, gaps)
is ``solver.py``'s, and the conclusion about the discrete domain is this
module's — and only this module's.

SCIP is the only production search engine, and its own status is the proof
(D-X1, developer decision of 2026-09-24). Exactly three conclusions exist:

* ``optimal_proven`` — every stage of the cascade, the canonical tie-breaks
  included, closed ``optimal`` with no anomaly, and the published candidate
  is exactly the one SCIP returned;
* ``infeasibility_proven`` — the first, still-global stage closed
  ``infeasible``, and nothing is published;
* ``not_proven`` — everything else: a limit, an anomaly, or a published
  candidate that is not SCIP's.

A ``solver_status`` proof means what SCIP means by ``optimal`` and
``infeasible``: within the tolerances the wire evidence publishes
(``numerics/feastol``, ``limits/gap``). It never vouches for a number:
every published figure is re-derived in exact arithmetic by
``evaluate_exact_candidate``, and a candidate the replay rejects is never
published. The exhaustive oracle is a test instrument
(``backend/test_scripts``) that cross-checks SCIP and the evaluator on small
domains; production cannot reach it.

The rules are enforced *by construction*, not by caller discipline:

* The conclusion types are disjoint frozen dataclasses whose ``kind`` is a
  single-valued ``Literal``. An ``UnprovenConclusion`` has no field that
  could hold a proven claim.
* Every proven conclusion carries a mandatory witness, and the witness type
  is *sealed*: its ``__post_init__`` rejects any construction that did not
  come through ``conclude_with_solver``. A caller who reaches past it and
  builds the dataclass directly gets a ``ProofForgeryError``, not a proof.
* ``conclude_with_solver`` reads the proof out of the run itself: the
  statuses are SCIP's, the published candidate has to *be* SCIP's, and the
  objective codes the caller names have to *be* the stages SCIP ran.

Every unproven outcome reuses the generic
``allocation.exact_proof_not_established`` reason (Step3 §16.7 Q2): a time
limit, a node limit and an anomaly all collapse onto it rather than
inventing wire codes before telemetry justifies them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Literal

from backend.app.services.pac_allocator.models import CandidateActionVector, ExactObjectiveCode
from backend.app.services.pac_allocator.solver import BOUND_CHECK_TOLERANCE, SolverRunResult

__all__ = [
    "NOT_PROVEN_REASON",
    "PROOF_NOT_CONFIRMED_REASON",
    "WIDE_MODEL_REASON",
    "InfeasibilityProvenConclusion",
    "OptimalProvenConclusion",
    "PlanConclusion",
    "ProofForgeryError",
    "ProvenConclusion",
    "SeededRunVote",
    "SeededVerdict",
    "SolverStatusWitnessFacts",
    "UnprovenConclusion",
    "conclude_with_solver",
    "merge_seeded_runs",
    "seeded_margin",
    "seeded_runs_agree",
]

# Generic reason code (Step3 §16.7 Q2). Kept as a module constant so the
# single wire value this build may emit is stated once.
NOT_PROVEN_REASON = "allocation.exact_proof_not_established"
# Lot SEEDS of project 67 (specification §16.11, §16.16; the consultant's definitions of 17/11): a plan of the wide model
# (lot ZB), found counting the rounding in its favour because the limits leave no room for the reserve; and a run that
# proved its plan by itself while no second run closed on the same value.
WIDE_MODEL_REASON = "allocation.limits_leave_no_rounding_room"
PROOF_NOT_CONFIRMED_REASON = "allocation.proof_not_confirmed"
#: Two runs' values are «equal» within this many of the engine's whole band: the bound check's relative tolerance plus the
#: first stage's band (lot SEEDS-b, the consultant's answer of 17/11). Derived, not fitted: two plans, each within one band
#: of the same closure, are at most two bands apart. 0.16 cent on G5; it holds SCIP's spread among closures (7.2e-8 and
#: 1.4e-6 on the lane's battery) and leaves out a different plan 4.86e-6 above G5's optimum, which the earlier factor 5 let in.
SEED_AGREEMENT_FACTOR = 2

# Module-private construction seal. A witness is the key that unlocks a proven
# conclusion, so the key may only be cut here. This object never leaves the
# module, which is what makes forging a witness impossible rather than merely
# discouraged.
_WITNESS_SEAL = object()

# Canonical tie-break stages carry a decision id, not an objective code
# (``solver._objective_code``): they must close too, but no witness names them.
_TIE_STAGE_PREFIX = "tie:"


class ProofForgeryError(RuntimeError):
    """Raised when proof evidence is manufactured or contradicts its own run.

    Not a validation error about user data: reaching this means code tried to
    build a witness outside ``conclude_with_solver``, or named objectives the
    solver did not run — either would let a claim masquerade as SCIP's own
    verdict.
    """


@dataclass(frozen=True, slots=True)
class SolverStatusWitnessFacts:
    """The objective stages SCIP closed, in cascade order.

    Only ``conclude_with_solver`` can build one, and only after checking those
    stages against the run itself.
    """

    objective_codes: tuple[ExactObjectiveCode, ...]
    seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.seal is not _WITNESS_SEAL:
            raise ProofForgeryError("SolverStatusWitnessFacts may only be built from a real solver run via conclude_with_solver")
        if not self.objective_codes:
            raise ProofForgeryError("a solver-status witness must name at least one objective stage")
        if len(set(self.objective_codes)) != len(self.objective_codes):
            raise ProofForgeryError("solver-status witness objective codes must be unique")


@dataclass(frozen=True, slots=True)
class OptimalProvenConclusion:
    """``optimal_proven``: every stage closed at the optimum. Unreachable
    without a witness: ``witness`` has no default, and its type cannot be
    built outside this module.
    """

    witness: SolverStatusWitnessFacts
    kind: Literal["optimal_proven"] = "optimal_proven"
    proof_source: Literal["solver_status"] = "solver_status"
    tie_break_closed: Literal[True] = True


@dataclass(frozen=True, slots=True)
class InfeasibilityProvenConclusion:
    """``infeasibility_proven``: the first, still-global stage closed
    infeasible. Its witness names exactly that stage's objective.
    """

    witness: SolverStatusWitnessFacts
    kind: Literal["infeasibility_proven"] = "infeasibility_proven"
    proof_source: Literal["solver_status"] = "solver_status"

    def __post_init__(self) -> None:
        if len(self.witness.objective_codes) != 1:
            raise ProofForgeryError("an infeasibility proof names exactly the first objective stage")


@dataclass(frozen=True, slots=True)
class UnprovenConclusion:
    """``not_proven``. The honest outcome for every limited or anomalous search.

    ``kind`` is a single-valued ``Literal`` on a frozen dataclass, so this type
    is structurally incapable of expressing a proven claim — there is nothing
    to set and nothing to forget to set.
    """

    reason_code: str = NOT_PROVEN_REASON
    kind: Literal["not_proven"] = "not_proven"


type ProvenConclusion = OptimalProvenConclusion | InfeasibilityProvenConclusion
type PlanConclusion = ProvenConclusion | UnprovenConclusion


def _quanta(candidate: CandidateActionVector) -> dict[str, int]:
    return {decision.decision_id: decision.quanta for decision in candidate.decisions}


def _witness(objective_codes: tuple[ExactObjectiveCode, ...]) -> SolverStatusWitnessFacts:
    return SolverStatusWitnessFacts(objective_codes=objective_codes, seal=_WITNESS_SEAL)


def conclude_with_solver(
    solver: SolverRunResult,
    *,
    objective_codes: Sequence[ExactObjectiveCode],
    published: CandidateActionVector | None,
    outer_model: bool = False,
) -> PlanConclusion:
    """Read the proof out of a SCIP run.

    ``objective_codes`` are the view's objectives in cascade order.
    ``published`` is the candidate the result publishes — SCIP's, once the
    Decimal replay accepted it — or ``None`` when nothing is published.

    * ``infeasibility_proven`` — ``reported_infeasible``, no anomaly, nothing
      published, and the run is exactly one stage: ordinal 1, global, closed
      ``infeasible`` on the first objective.
    * ``optimal_proven`` — ``incumbent``, no anomaly, every stage (the
      canonical tie-breaks included) closed ``optimal``, and ``published``
      exactly SCIP's candidate. A proof about SCIP's optimum is never
      transferred to a candidate SCIP did not return. The Rebalancer's
      tie-breaks (``operation_count``, ``route_priority`` and its canonical
      vector, on one level: specifica §6.4) are the one exception: one left
      open, by a limit or by the exact comparison that rejected its plan
      (D4), does not downgrade the proof, which is about ``J`` or the «Target
      first» chain (§15 n. 10). The witness then names the stages that closed.
      The PAC's stages are never tie-breaks, so its rule is unchanged.
    * ``not_proven`` — everything else. Downgrading is always sound.

    ``outer_model`` (lot ZB of project 67): the run was on the outer model, solved because the prudent one closed
    infeasible (``planner.plan_exact_scenario``). It holds every plan the replay could accept, so its «infeasible» is the
    proof above. It is not the model the cascade optimizes, so nothing it returns is proven the best: its plans are
    ``not_proven`` whatever its stages say. The prudent model's own «infeasible» never reaches this function as a verdict:
    the planner always checks it on the outer model first.

    Raises ``ProofForgeryError`` when a run that would prove something did not
    run exactly the named objectives: the view and the compiled cascade would
    disagree about what was optimized.
    """
    expected = tuple(objective_codes)

    if solver.outcome == "reported_infeasible":
        if solver.anomaly is not None or published is not None or solver.candidate is not None or len(solver.stages) != 1:
            return UnprovenConclusion()
        (stage,) = solver.stages
        if stage.status != "infeasible" or stage.scip_status != "infeasible" or stage.ordinal != 1 or stage.scope != "global":
            return UnprovenConclusion()
        if not expected or stage.objective_code != expected[0]:
            raise ProofForgeryError(f"SCIP closed stage {stage.objective_code!r} infeasible, but the first objective is {expected[0] if expected else None!r}")
        return InfeasibilityProvenConclusion(witness=_witness((stage.objective_code,)))

    if outer_model:
        # Lot SEEDS: a plan of the wide model says why it is not proven; anything else of it says what it says today.
        return UnprovenConclusion(reason_code=WIDE_MODEL_REASON) if solver.outcome == "incumbent" and published is not None else UnprovenConclusion()
    if solver.outcome != "incumbent" or solver.anomaly is not None or not solver.stages:
        return UnprovenConclusion()
    if any((stage.status != "finished" or stage.scip_status != "optimal") and not stage.tie_break for stage in solver.stages):
        return UnprovenConclusion()
    if published is None or solver.candidate is None or _quanta(published) != _quanta(solver.candidate):
        return UnprovenConclusion()
    normative = tuple(stage.objective_code for stage in solver.stages if not stage.objective_code.startswith(_TIE_STAGE_PREFIX))
    if normative != expected:
        raise ProofForgeryError(f"SCIP closed the stages {list(normative)}, but the view's objectives are {list(expected)}")
    closed = tuple(stage.objective_code for stage in solver.stages if not stage.objective_code.startswith(_TIE_STAGE_PREFIX) and stage.status == "finished")
    return OptimalProvenConclusion(witness=_witness(closed))


@dataclass(frozen=True, slots=True)
class SeededRunVote:
    """What one of the Rebalancer's runs found, as the merge reads it (lot SEEDS of project 67).

    ``origin`` is the model of its published plan (``prudent``, ``wide``) or ``none`` without a plan; ``closed`` is its own
    verdict, ``optimal_proven``; ``infeasible`` its own «impossible, proven»; ``value`` its published plan's first stage
    valued exactly as the solver sees it (``evaluation.solver_view``); ``band`` that stage's band (its quadratic rows, how
    far below the truth SCIP's value may sit) in the unit of ``value``; ``failed`` a run that returned nothing.
    """

    seed: int
    origin: Literal["prudent", "wide", "none"] = "none"
    closed: bool = False
    infeasible: bool = False
    value: Fraction | None = None
    band: Fraction = Fraction(0)
    #: Its first stage's lower bound (SCIP's dual) in the unit of ``value``; None when the run has none (no plan, the wide
    #: model, a bound SCIP did not reach).
    bound: Fraction | None = None
    failed: bool = False


@dataclass(frozen=True, slots=True)
class SeededVerdict:
    """The merge's answer: the run to publish (its index), and whether its own «proven» must be downgraded to
    ``PROOF_NOT_CONFIRMED_REASON``. ``index`` is None when no run can be published as it is (``inconclusive``: a single
    «impossible» and nothing else; ``failed``: every run failed)."""

    index: int | None
    downgrade: bool = False
    state: Literal["plan", "infeasible", "no_plan", "inconclusive", "failed"] = "plan"


def seeded_runs_agree(a: Fraction, b: Fraction, lowest: Fraction, *, band: Fraction = Fraction(0)) -> bool:
    """Two runs' values are «equal»: |a − b| ≤ ``SEED_AGREEMENT_FACTOR`` × (the bound check's relative tolerance of the
    lowest value + the first stage's ``band``), the engine's whole band (lot SEEDS-b)."""
    # The tolerance as the decimal it is written as (1e-6), not as its nearest binary float.
    relative = Fraction(str(BOUND_CHECK_TOLERANCE)) * max(Fraction(1), abs(lowest))
    return abs(a - b) <= Fraction(SEED_AGREEMENT_FACTOR) * (relative + band)


def seeded_margin(votes: Sequence[SeededRunVote], verdict: SeededVerdict) -> Fraction | None:
    """Lot MG of project 67 (the developer's «ottimo locale (entro X)», the consultant's rule of 17/11): how far below the
    published plan the best plan can still be, in the first stage's unit: V − L.

    V is the published run's value. L is the **second-highest** of the runs' bounds that are usable, not above V beyond the
    agreement band (a bound above the plan is refuted by the plan itself): a bound counts when two searches say it, as the
    proof does. None for a proven plan, a plan of the wide model, no plan, or fewer than two usable bounds. The result may
    be at most zero (bounds just above V, inside the band): the caller posts it as one minor unit.
    """
    if verdict.index is None or verdict.state != "plan":
        return None
    chosen = votes[verdict.index]
    if chosen.origin != "prudent" or chosen.value is None or (chosen.closed and not verdict.downgrade):
        return None
    value = chosen.value
    usable = sorted((vote.bound for vote in votes if not vote.failed and vote.bound is not None and (vote.bound <= value or seeded_runs_agree(vote.bound, value, value, band=chosen.band))), reverse=True)
    return value - usable[1] if len(usable) >= 2 else None


def merge_seeded_runs(votes: Sequence[SeededRunVote]) -> SeededVerdict:
    """The developer's rule for three runs (specification §16.11, §16.16), with the consultant's merge of 17/11.

    The merge may only downgrade: a run's own «not proven» is never upgraded and keeps its reason; its own «proven» stays
    only when a second closed run is equal to it. A run that failed does not vote.

    1. Any plan of the prudent model: only those runs count. The lowest value wins. If at least two closed runs are equal
       to it, the published one is the lowest of them, proven; otherwise the run with the lowest value, downgraded if it
       had proven itself.
    2. Else any plan of the wide model: the lowest, never proven (its own reason says why).
    3. Else «impossible, proven» when at least two runs say so; else «no plan found» from a run that found none; a single
       «impossible» with nothing else to publish is inconclusive.

    Ties of value go to the lowest seed.
    """
    usable = [(index, vote) for index, vote in enumerate(votes) if not vote.failed]
    if not usable:
        return SeededVerdict(index=None, state="failed")
    order = lambda item: (item[1].value, item[1].seed)  # noqa: E731
    prudent = [item for item in usable if item[1].origin == "prudent" and item[1].value is not None]
    if prudent:
        lowest = min(vote.value for _, vote in prudent)
        band = max(vote.band for _, vote in prudent)
        agreeing = [item for item in prudent if item[1].closed and seeded_runs_agree(item[1].value, lowest, lowest, band=band)]
        if len(agreeing) >= 2:
            return SeededVerdict(index=min(agreeing, key=order)[0])
        index, vote = min(prudent, key=order)
        return SeededVerdict(index=index, downgrade=vote.closed)
    wide = [item for item in usable if item[1].origin == "wide" and item[1].value is not None]
    if wide:
        return SeededVerdict(index=min(wide, key=order)[0])
    infeasible = [item for item in usable if item[1].infeasible]
    if len(infeasible) >= 2:
        return SeededVerdict(index=min(infeasible, key=lambda item: item[1].seed)[0], state="infeasible")
    none = [item for item in usable if not item[1].infeasible]
    if none:
        return SeededVerdict(index=min(none, key=lambda item: item[1].seed)[0], state="no_plan")
    return SeededVerdict(index=None, state="inconclusive")
