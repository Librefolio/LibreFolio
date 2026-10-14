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
from typing import Literal

from backend.app.services.pac_allocator.models import CandidateActionVector, ExactObjectiveCode
from backend.app.services.pac_allocator.solver import SolverRunResult

__all__ = [
    "NOT_PROVEN_REASON",
    "InfeasibilityProvenConclusion",
    "OptimalProvenConclusion",
    "PlanConclusion",
    "ProofForgeryError",
    "ProvenConclusion",
    "SolverStatusWitnessFacts",
    "UnprovenConclusion",
    "conclude_with_solver",
]

# Generic reason code (Step3 §16.7 Q2). Kept as a module constant so the
# single wire value this build may emit is stated once.
NOT_PROVEN_REASON = "allocation.exact_proof_not_established"

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
      transferred to a candidate SCIP did not return.
    * ``not_proven`` — everything else. Downgrading is always sound.

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

    if solver.outcome != "incumbent" or solver.anomaly is not None or not solver.stages:
        return UnprovenConclusion()
    if any(stage.status != "finished" or stage.scip_status != "optimal" for stage in solver.stages):
        return UnprovenConclusion()
    if published is None or solver.candidate is None or _quanta(published) != _quanta(solver.candidate):
        return UnprovenConclusion()
    normative = tuple(stage.objective_code for stage in solver.stages if not stage.objective_code.startswith(_TIE_STAGE_PREFIX))
    if normative != expected:
        raise ProofForgeryError(f"SCIP closed the stages {list(normative)}, but the view's objectives are {list(expected)}")
    return OptimalProvenConclusion(witness=_witness(expected))
