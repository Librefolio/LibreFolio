"""Proof semantics for the PAC/Rebalancer planner (Step 3, Stage 4).

This module decides the *third* of the three independent dimensions in Proof
Semantics A (Step3 §16.3): incumbent validation (``decimal_verified``) is
``evaluator.py``'s job, floating solver evidence (status/bounds/gaps) is
``solver.py``'s, and the mathematical conclusion about the discrete domain is
this module's — and only this module's.

The non-negotiable structural rule is that a floating SCIP status is **never**
promoted to a proof on its own: only an exhaustive-oracle result or (later) a
score-lattice-closure witness can do that. That rule is enforced *by
construction* here, not by caller discipline:

* The conclusion types are disjoint frozen dataclasses whose ``kind`` is a
  single-valued ``Literal``. An ``UnprovenConclusion`` is not merely expected
  to avoid saying ``optimal_proven`` — it has no field that can hold it.
* ``conclude_without_proof`` takes a ``SolverRunResult`` and its return type is
  ``UnprovenConclusion``. **There is no function in this module that maps
  solver evidence to a proven conclusion.** The unsafe transition is not
  guarded, it is absent: you cannot call what does not exist.
* Every proven conclusion carries a mandatory witness, and the witness types
  are *sealed* — their ``__post_init__`` rejects any construction that did not
  come through this module's own oracle/conflict readers. So even a caller who
  reaches past the public functions and builds the dataclass directly gets a
  ``ProofForgeryError`` rather than a fabricated proof.

Phase 1 scope (Step3 §16.5): ``optimal_proven`` and ``infeasibility_proven``
via the exhaustive oracle, ``infeasibility_proven`` via a deterministic
conflict, and ``not_proven`` for everything else. ``gap_bounded`` is
deliberately **not** implemented: it requires a safe dual bound, and this build
has no way to derive one that is sound rather than merely plausible — emitting
it from SCIP's floating dual would be exactly the promotion this module exists
to prevent. ``score_lattice_closure`` is likewise out of scope until
``solver.py`` and ``oracle.py`` are cross-validated on a wider corpus.

Per Step3 §16.7 Q2, phase 1 reuses the generic
``allocation.exact_proof_not_established`` reason for every unproven outcome —
time limit, node limit and an oracle domain too large all collapse onto it
rather than inventing wire codes before telemetry justifies them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    ExactEvaluation,
    ExactObjectiveCode,
)
from backend.app.services.pac_allocator.oracle import OracleResult
from backend.app.services.pac_allocator.solver import SolverRunResult

__all__ = [
    "NOT_PROVEN_REASON",
    "DeterministicConflictWitnessFacts",
    "ExhaustiveOracleWitnessFacts",
    "InfeasibilityProvenConclusion",
    "OptimalProvenConclusion",
    "PlanConclusion",
    "ProofForgeryError",
    "ProvenConclusion",
    "UnprovenConclusion",
    "conclude_infeasible_from_conflicts",
    "conclude_with_oracle",
    "conclude_without_proof",
]

# Generic phase-1 reason code (Step3 §16.7 Q2). Kept as a module constant so
# the single wire value this build may emit is stated once.
NOT_PROVEN_REASON = "allocation.exact_proof_not_established"

# Module-private construction seal. A witness is the key that unlocks a proven
# conclusion, so the key may only be cut here. This object never leaves the
# module, which is what makes forging a witness impossible rather than merely
# discouraged.
_WITNESS_SEAL = object()


class ProofForgeryError(RuntimeError):
    """Raised when a witness is constructed outside this module's readers.

    Not a validation error about user data: reaching this means code tried to
    manufacture proof evidence directly, which would let a floating result
    masquerade as a mathematical one.
    """


@dataclass(frozen=True, slots=True)
class ExhaustiveOracleWitnessFacts:
    """Facts backing an exhaustive-enumeration proof.

    Only ``_witness_from_oracle`` can build one. A returned ``OracleResult`` is
    inherently complete — ``run_exhaustive_oracle`` raises
    ``OracleDomainTooLargeError`` rather than truncating — so holding one of
    these really does mean the whole discrete domain was visited.
    """

    enumerated_candidates: int
    feasible_candidates: int
    objective_codes: tuple[ExactObjectiveCode, ...]
    seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.seal is not _WITNESS_SEAL:
            raise ProofForgeryError("ExhaustiveOracleWitnessFacts may only be built from a real OracleResult via this module")
        if self.enumerated_candidates < 1:
            raise ProofForgeryError("an exhaustive witness must have enumerated at least one candidate")
        if not 0 <= self.feasible_candidates <= self.enumerated_candidates:
            raise ProofForgeryError("feasible candidates must not exceed enumerated candidates")
        if len(set(self.objective_codes)) != len(self.objective_codes):
            raise ProofForgeryError("oracle objective codes must be unique")


@dataclass(frozen=True, slots=True)
class DeterministicConflictWitnessFacts:
    """Facts backing an infeasibility proved by contract conflicts alone.

    This needs no search at all: the exact evaluator rejected the candidate on
    named constraint codes, which is a mathematical statement about the
    scenario, not a solver observation.
    """

    issue_codes: tuple[str, ...]
    summary_code: str
    seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.seal is not _WITNESS_SEAL:
            raise ProofForgeryError("DeterministicConflictWitnessFacts may only be built from a real ExactEvaluation via this module")
        if not self.issue_codes:
            raise ProofForgeryError("a deterministic conflict witness needs at least one issue code")
        if len(set(self.issue_codes)) != len(self.issue_codes):
            raise ProofForgeryError("conflict issue codes must be unique")
        if self.summary_code not in self.issue_codes:
            raise ProofForgeryError("the conflict summary code must be one of the listed issue codes")


@dataclass(frozen=True, slots=True)
class OptimalProvenConclusion:
    """``optimal_proven``. Unreachable without an oracle witness: ``witness``
    has no default, and its type cannot be built outside this module.
    """

    witness: ExhaustiveOracleWitnessFacts
    kind: Literal["optimal_proven"] = "optimal_proven"
    proof_source: Literal["exhaustive_oracle"] = "exhaustive_oracle"
    tie_break_closed: Literal[True] = True

    def __post_init__(self) -> None:
        if self.witness.feasible_candidates == 0:
            raise ProofForgeryError("an optimality proof requires at least one feasible candidate")
        if not self.witness.objective_codes:
            raise ProofForgeryError("an optimality proof must cover at least one objective stage")


@dataclass(frozen=True, slots=True)
class InfeasibilityProvenConclusion:
    """``infeasibility_proven`` from either legal source. Note there is no
    constructor path from a SCIP ``infeasible`` status: ``solver.py`` reports
    that as ``reported_infeasible``, floating vocabulary that this module
    cannot consume into a proof.
    """

    witness: ExhaustiveOracleWitnessFacts | DeterministicConflictWitnessFacts
    kind: Literal["infeasibility_proven"] = "infeasibility_proven"

    @property
    def proof_source(self) -> Literal["exhaustive_oracle", "deterministic_conflict"]:
        return "exhaustive_oracle" if isinstance(self.witness, ExhaustiveOracleWitnessFacts) else "deterministic_conflict"

    def __post_init__(self) -> None:
        if isinstance(self.witness, ExhaustiveOracleWitnessFacts) and self.witness.feasible_candidates != 0:
            raise ProofForgeryError("an oracle infeasibility proof cannot carry a feasible candidate")


@dataclass(frozen=True, slots=True)
class UnprovenConclusion:
    """``not_proven``. The honest outcome for every floating or limited search.

    ``kind`` is a single-valued ``Literal`` on a frozen dataclass, so this type
    is structurally incapable of expressing a proven claim — there is nothing
    to set and nothing to forget to set.
    """

    reason_code: str = NOT_PROVEN_REASON
    kind: Literal["not_proven"] = "not_proven"


type ProvenConclusion = OptimalProvenConclusion | InfeasibilityProvenConclusion
type PlanConclusion = ProvenConclusion | UnprovenConclusion


def _witness_from_oracle(oracle: OracleResult) -> ExhaustiveOracleWitnessFacts:
    return ExhaustiveOracleWitnessFacts(
        enumerated_candidates=oracle.enumerated_candidates,
        feasible_candidates=oracle.feasible_candidates,
        objective_codes=oracle.objective_codes,
        seal=_WITNESS_SEAL,
    )


def _published_quanta(candidate: CandidateActionVector) -> dict[str, int]:
    return {decision.decision_id: decision.quanta for decision in candidate.decisions}


def conclude_without_proof(solver: SolverRunResult) -> UnprovenConclusion:
    """The only conclusion obtainable from solver evidence alone.

    Deliberately ignores ``solver`` entirely beyond accepting it: there is no
    field of a floating run — not ``outcome == "incumbent"``, not a zero gap,
    not ``scip_status == "optimal"`` on every stage — that may influence
    whether something is proven. Taking the argument documents *what was
    searched* at the call site while the return type guarantees what it can
    conclude.
    """
    return UnprovenConclusion()


def conclude_with_oracle(oracle: OracleResult, *, published: CandidateActionVector | None) -> PlanConclusion:
    """Conclude from a completed exhaustive enumeration.

    Returns ``infeasibility_proven`` when the oracle found no feasible
    candidate at all, ``optimal_proven`` when ``published`` is exactly the
    candidate the oracle proved best, and ``not_proven`` otherwise.

    That last case is the one worth being careful about: the oracle proves a
    statement about *its own* optimum, not about whatever candidate the caller
    happens to publish. Publishing a different candidate — a solver incumbent
    that disagrees, say — makes the proof inapplicable, so it is downgraded
    rather than transferred. Downgrading is always sound; transferring would
    not be.
    """
    if oracle.feasible_candidates == 0:
        if oracle.best_candidate is not None:
            raise ProofForgeryError("oracle reported no feasible candidates yet returned a best candidate")
        return InfeasibilityProvenConclusion(witness=_witness_from_oracle(oracle))

    if published is None or oracle.best_candidate is None:
        return UnprovenConclusion()
    if _published_quanta(published) != _published_quanta(oracle.best_candidate):
        return UnprovenConclusion()
    return OptimalProvenConclusion(witness=_witness_from_oracle(oracle))


def conclude_infeasible_from_conflicts(evaluation: ExactEvaluation, *, summary_code: str | None = None) -> PlanConclusion:
    """Conclude infeasibility from the exact evaluator's own contract conflicts.

    Needs no search: these are named constraint violations the Decimal
    evaluator derived directly. Returns ``not_proven`` when the evaluation
    carries no conflicts, rather than inventing one.
    """
    issue_codes = tuple(dict.fromkeys(evaluation.conflict_codes))
    if not issue_codes:
        return UnprovenConclusion()
    chosen_summary = summary_code if summary_code is not None else issue_codes[0]
    if chosen_summary not in issue_codes:
        raise ProofForgeryError(f"summary code {chosen_summary!r} is not among the evaluation's conflicts")
    witness = DeterministicConflictWitnessFacts(issue_codes=issue_codes, summary_code=chosen_summary, seal=_WITNESS_SEAL)
    return InfeasibilityProvenConclusion(witness=witness)


def describe_conclusion(conclusion: PlanConclusion) -> Mapping[str, object]:
    """A small, stable projection for logs and diagnostics.

    Intentionally not a wire model: assembling the ``ReadyPlanProof`` union is
    Stage 5's job, and doing it here would give this module a second reason to
    change.
    """
    described: dict[str, object] = {"kind": conclusion.kind}
    if isinstance(conclusion, UnprovenConclusion):
        described["reason_code"] = conclusion.reason_code
        return described
    described["proof_source"] = conclusion.proof_source
    if isinstance(conclusion.witness, ExhaustiveOracleWitnessFacts):
        described["enumerated_candidates"] = conclusion.witness.enumerated_candidates
        described["feasible_candidates"] = conclusion.witness.feasible_candidates
    else:
        described["issue_codes"] = list(conclusion.witness.issue_codes)
    return described
