"""Contract tests for the proof-semantics layer of the PAC/Rebalancer planner.

`proof.py` (Step 3, Stage 4) decides the third of three independent
dimensions: incumbent validation is `evaluator.py`'s job, floating solver
evidence is `solver.py`'s, and the *mathematical conclusion about the
discrete domain* is this module's — and only this module's.

The headline property these tests exist to lock down is **unrepresentability**:
the unsafe transition from a floating/limit-terminated SCIP solve to a
`*_proven` outcome must be *absent by construction*, not merely un-taken. A
caller cannot promote a solver result even by mistake, because:

* `conclude_without_proof` is the only conclusion obtainable from solver
  evidence and its return type is `UnprovenConclusion`; there is no function
  that maps a `SolverRunResult` to a proven type (asserted here by annotation
  introspection, not by eyeballing).
* `UnprovenConclusion` is a frozen dataclass whose `kind` is a single-valued
  `Literal` — it has no field that could ever hold a proof kind.
* Every proven conclusion carries a *sealed* witness; forging either witness
  type outside this module raises `ProofForgeryError`, checked here for its
  exact exception type (a guard that throws the wrong type is worse than no
  guard).

Everything else is exercised against the *real* pipeline
(`build_exact_policy_view` -> `run_exhaustive_oracle` /
`compile_policy_program` -> `solve_policy_program`), reusing the sibling
suites' fixtures exactly the way they already share them — never hand-built
stubs. Candidate counts are read off the live `OracleResult` and the witness
is asserted to mirror them; no global count (585/151/16/11/…) is hardcoded.

These are pure in-process tests (`isolation="pure"`): no server, no database,
no clock assertions, no sleeps, no network. Exact domain values compare with
`==`; SCIP floats are never compared exactly (the "perfect solve" fixture is
proven perfect by `scip_status == "optimal"` / `status == "finished"`, never
by a float-gap equality).
"""

from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Callable

import pytest

from backend.app.services.pac_allocator import proof
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import ExactEvaluation, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.oracle import run_exhaustive_oracle
from backend.app.services.pac_allocator.proof import (
    NOT_PROVEN_REASON,
    DeterministicConflictWitnessFacts,
    ExhaustiveOracleWitnessFacts,
    InfeasibilityProvenConclusion,
    OptimalProvenConclusion,
    ProofForgeryError,
    UnprovenConclusion,
    conclude_infeasible_from_conflicts,
    conclude_with_oracle,
    conclude_without_proof,
    describe_conclusion,
)
from backend.app.services.pac_allocator.solver import SolverRunResult, solve_policy_program
from backend.test_scripts.test_services.test_pac_planner_evaluator import R, _candidate, _pac_scenario
from backend.test_scripts.test_services.test_pac_planner_oracle import _two_asset_pac_scenario

# The one legitimate reach into a module-private. A *valid* sealed witness can
# only be cut with the very seal that production code is structurally forbidden
# from touching, so the positive-invariant tests below must read it here. That
# production code cannot reach this object is exactly the property the forgery
# tests assert; a test may, precisely because it is asserting the shape of a
# real witness rather than manufacturing proof evidence at a call site.
_SEAL = proof._WITNESS_SEAL


# --------------------------------------------------------------------------
# Shared helpers (real pipeline, never hand-built stubs)
# --------------------------------------------------------------------------


def _primary_view(scenario: ExactPlannerScenario) -> ExactPolicyView:
    return build_exact_policy_view(scenario, purpose="primary")


def _real_solver_result(scenario: ExactPlannerScenario, **kwargs: object) -> SolverRunResult:
    """Compile and solve a fresh model — a genuine `SolverRunResult`, never a
    stub. A fresh `compile_policy_program` per call keeps every solve on its
    own `Model` (the PySCIPOpt reuse trap the sibling suites document).
    """
    view = _primary_view(scenario)
    program = compile_policy_program(scenario, view)
    return solve_policy_program(program, **kwargs)


def _sealed_oracle_witness(*, enumerated: int, feasible: int, objective_codes: tuple[str, ...]) -> ExhaustiveOracleWitnessFacts:
    return ExhaustiveOracleWitnessFacts(enumerated_candidates=enumerated, feasible_candidates=feasible, objective_codes=objective_codes, seal=_SEAL)


# --------------------------------------------------------------------------
# Constants + deliberately-absent phase-2 symbols
# --------------------------------------------------------------------------


def test_not_proven_reason_is_the_single_phase_one_wire_code() -> None:
    assert NOT_PROVEN_REASON == "allocation.exact_proof_not_established"
    assert UnprovenConclusion().reason_code == NOT_PROVEN_REASON


def test_phase_two_symbols_are_deliberately_absent() -> None:
    """`gap_bounded` needs a sound dual bound this build cannot derive, and
    `score_lattice_closure` is out of scope until solver/oracle are
    cross-validated on a wider corpus. Both must be *absent*, not stubbed —
    an absent symbol cannot be emitted by accident.
    """
    assert not hasattr(proof, "gap_bounded")
    assert not hasattr(proof, "score_lattice_closure")
    assert "gap_bounded" not in proof.__all__
    assert "score_lattice_closure" not in proof.__all__


# --------------------------------------------------------------------------
# 1. Unrepresentability (headline)
# --------------------------------------------------------------------------


def test_perfect_floating_solve_still_proves_nothing() -> None:
    """The core rule: a *perfect* floating solve proves nothing.

    `_two_asset_pac_scenario` solves fully — every stage finishes `optimal`
    (so the incumbent is extracted and every stage is on its own optimum). Yet
    `conclude_without_proof` on that flawless run is still `not_proven`,
    because no field of a floating run may influence a proof.

    "Every stage finished optimal" is asserted structurally
    (`status == "finished"`, `scip_status == "optimal"`); the zero gap is a
    SCIP float and is deliberately *not* compared exactly.
    """
    result = _real_solver_result(_two_asset_pac_scenario())

    assert result.outcome == "incumbent"
    assert result.candidate is not None
    assert result.finished_stage_count == len(result.stages)
    assert all(stage.status == "finished" for stage in result.stages)
    assert all(stage.scip_status == "optimal" for stage in result.stages)

    conclusion = conclude_without_proof(result)
    assert isinstance(conclusion, UnprovenConclusion)
    assert conclusion.kind == "not_proven"
    assert conclusion.reason_code == NOT_PROVEN_REASON


def test_conclude_without_proof_is_unproven_for_every_solver_outcome() -> None:
    """No solver result — of *any* outcome — may conclude a proof.

    Three genuinely different `SolverRunResult`s are produced from the real
    pipeline: a fully-successful `incumbent`, a `reported_infeasible` (SCIP's
    floating infeasibility vocabulary), and a `no_incumbent` (limits exhausted
    before any solution). All three collapse to the identical
    `UnprovenConclusion`.
    """
    incumbent = _real_solver_result(_two_asset_pac_scenario())
    reported_infeasible = _real_solver_result(_pac_scenario(required=R(50), route_cap=R(10)))
    no_incumbent = _real_solver_result(_two_asset_pac_scenario(), time_budget_seconds=0.0)

    # Confirm the three fixtures really did drive the solver into three
    # distinct states, so the shared verdict below is not an accident.
    assert incumbent.outcome == "incumbent"
    assert reported_infeasible.outcome == "reported_infeasible"
    assert no_incumbent.outcome == "no_incumbent"

    for result in (incumbent, reported_infeasible, no_incumbent):
        conclusion = conclude_without_proof(result)
        assert isinstance(conclusion, UnprovenConclusion)
        assert conclusion.kind == "not_proven"
        assert conclusion.reason_code == NOT_PROVEN_REASON


def test_unproven_conclusion_has_no_field_that_can_hold_a_proof() -> None:
    """`UnprovenConclusion` is structurally incapable of expressing a proof:
    its only fields are `reason_code` and `kind`, and none of the
    proof-bearing fields the proven conclusions carry exist here.
    """
    field_names = set(UnprovenConclusion.__dataclass_fields__)
    assert field_names == {"reason_code", "kind"}
    assert not field_names & {"witness", "proof_source", "tie_break_closed", "enumerated_candidates", "feasible_candidates", "issue_codes"}

    conclusion = UnprovenConclusion()
    assert conclusion.kind == "not_proven"


def test_unproven_conclusion_is_frozen() -> None:
    """Frozen: it cannot be mutated into holding a proof kind after the fact."""
    conclusion = UnprovenConclusion()
    with pytest.raises(dataclasses.FrozenInstanceError):
        conclusion.kind = "optimal_proven"


def test_no_public_callable_maps_solver_result_to_a_proven_type() -> None:
    """Introspect (never eyeball): any public callable that *consumes* a
    `SolverRunResult` must return exactly `UnprovenConclusion` — never a
    proven type, never a union that admits one. The unsafe transition is
    absent, so there is nothing to call.
    """
    proven_type_names = {"OptimalProvenConclusion", "InfeasibilityProvenConclusion", "ProvenConclusion"}
    checked_a_solver_consumer = False

    for name, obj in inspect.getmembers(proof, inspect.isfunction):
        if obj.__module__ != proof.__name__ or name.startswith("_"):
            continue
        annotations = inspect.get_annotations(obj)  # PEP 563: raw strings, not evaluated
        parameter_annotations = [str(value) for key, value in annotations.items() if key != "return"]
        if not any("SolverRunResult" in annotation for annotation in parameter_annotations):
            continue
        checked_a_solver_consumer = True
        return_annotation = str(annotations.get("return", ""))
        assert return_annotation == "UnprovenConclusion", f"{name} consumes a SolverRunResult but returns {return_annotation!r}"
        assert not any(proven in return_annotation for proven in proven_type_names)

    assert checked_a_solver_consumer, "expected at least one public callable to consume a SolverRunResult"


# --------------------------------------------------------------------------
# 2. Every raise path, checked for its exact exception type
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build_forged_witness",
    [
        # Missing seal (default None) — both witness types.
        pytest.param(lambda: ExhaustiveOracleWitnessFacts(enumerated_candidates=1, feasible_candidates=0, objective_codes=()), id="oracle_witness_missing_seal"),
        pytest.param(lambda: DeterministicConflictWitnessFacts(issue_codes=("ORDER_REQUIRED_MIN",), summary_code="ORDER_REQUIRED_MIN"), id="conflict_witness_missing_seal"),
        # A wrong seal object is no better than none — both witness types.
        pytest.param(lambda: ExhaustiveOracleWitnessFacts(enumerated_candidates=1, feasible_candidates=0, objective_codes=(), seal=object()), id="oracle_witness_wrong_seal"),
        pytest.param(lambda: DeterministicConflictWitnessFacts(issue_codes=("ORDER_REQUIRED_MIN",), summary_code="ORDER_REQUIRED_MIN", seal=object()), id="conflict_witness_wrong_seal"),
        # Oracle witness numeric invariants (real seal, so the seal check passes first).
        pytest.param(lambda: ExhaustiveOracleWitnessFacts(enumerated_candidates=0, feasible_candidates=0, objective_codes=(), seal=_SEAL), id="oracle_witness_enumerated_below_one"),
        pytest.param(lambda: ExhaustiveOracleWitnessFacts(enumerated_candidates=2, feasible_candidates=3, objective_codes=(), seal=_SEAL), id="oracle_witness_feasible_exceeds_enumerated"),
        pytest.param(lambda: ExhaustiveOracleWitnessFacts(enumerated_candidates=2, feasible_candidates=1, objective_codes=("fixed_l2", "fixed_l2"), seal=_SEAL), id="oracle_witness_duplicate_objective_codes"),
        # Conflict witness structural invariants (real seal).
        pytest.param(lambda: DeterministicConflictWitnessFacts(issue_codes=(), summary_code="ORDER_REQUIRED_MIN", seal=_SEAL), id="conflict_witness_empty_issue_codes"),
        pytest.param(lambda: DeterministicConflictWitnessFacts(issue_codes=("A", "A"), summary_code="A", seal=_SEAL), id="conflict_witness_duplicate_issue_codes"),
        pytest.param(lambda: DeterministicConflictWitnessFacts(issue_codes=("A", "B"), summary_code="C", seal=_SEAL), id="conflict_witness_summary_not_in_issue_codes"),
    ],
)
def test_forging_a_witness_raises_proof_forgery_error(build_forged_witness: Callable[[], object]) -> None:
    """Exact type matters: each guard must raise `ProofForgeryError`, not some
    incidental `AttributeError`/`ValueError` that would defeat a caller's
    handling while looking deliberate.
    """
    with pytest.raises(ProofForgeryError):
        build_forged_witness()


def test_optimal_conclusion_requires_a_feasible_candidate() -> None:
    """A valid oracle witness with zero feasible candidates cannot back an
    `optimal_proven` conclusion.
    """
    witness = _sealed_oracle_witness(enumerated=3, feasible=0, objective_codes=("fixed_l2",))
    with pytest.raises(ProofForgeryError):
        OptimalProvenConclusion(witness=witness)


def test_optimal_conclusion_requires_at_least_one_objective() -> None:
    """An optimality proof must cover at least one objective stage."""
    witness = _sealed_oracle_witness(enumerated=3, feasible=2, objective_codes=())
    with pytest.raises(ProofForgeryError):
        OptimalProvenConclusion(witness=witness)


def test_oracle_infeasibility_cannot_carry_a_feasible_candidate() -> None:
    """An oracle-backed infeasibility proof is a claim of *zero* feasible
    candidates; a witness that counts some is self-contradictory.
    """
    witness = _sealed_oracle_witness(enumerated=3, feasible=2, objective_codes=("fixed_l2",))
    with pytest.raises(ProofForgeryError):
        InfeasibilityProvenConclusion(witness=witness)


def test_conclude_infeasible_from_conflicts_rejects_bad_explicit_summary_code() -> None:
    """An explicit `summary_code` that is not among the evaluation's own
    conflict codes is a forgery, not a relabelling.
    """
    scenario = _pac_scenario(required=R(50), route_cap=R(10))
    view = _primary_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, {}, candidate_id="all-zero"))
    assert evaluation.conflict_codes  # precondition: there really are conflicts to summarise

    with pytest.raises(ProofForgeryError):
        conclude_infeasible_from_conflicts(evaluation, summary_code="NOT_A_REAL_CONFLICT_CODE")


def test_self_contradictory_oracle_result_is_forgery() -> None:
    """An `OracleResult` that reports no feasible candidates yet still returns
    a `best_candidate` is internally impossible; `conclude_with_oracle` refuses
    it rather than fabricating an infeasibility proof around a live candidate.
    """
    scenario = _two_asset_pac_scenario()
    oracle = run_exhaustive_oracle(scenario, _primary_view(scenario))
    assert oracle.best_candidate is not None  # a genuinely feasible oracle result ...
    contradictory = dataclasses.replace(oracle, feasible_candidates=0)  # ... now made to lie about it

    with pytest.raises(ProofForgeryError):
        conclude_with_oracle(contradictory, published=None)


# --------------------------------------------------------------------------
# 3. Happy paths against REAL evidence
# --------------------------------------------------------------------------


def test_oracle_with_its_own_best_candidate_proves_optimal() -> None:
    """The one legal promotion to `optimal_proven`: an exhaustive oracle plus
    the very candidate it proved best. The witness mirrors the oracle's *live*
    counts and objective codes — read off the result, never hardcoded.
    """
    scenario = _two_asset_pac_scenario()
    view = _primary_view(scenario)
    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.best_candidate is not None
    assert oracle.feasible_candidates > 0

    conclusion = conclude_with_oracle(oracle, published=oracle.best_candidate)

    assert isinstance(conclusion, OptimalProvenConclusion)
    assert conclusion.kind == "optimal_proven"
    assert conclusion.proof_source == "exhaustive_oracle"
    assert conclusion.tie_break_closed is True
    # Witness mirrors the oracle's actual facts (no global count literal).
    assert conclusion.witness.enumerated_candidates == oracle.enumerated_candidates
    assert conclusion.witness.feasible_candidates == oracle.feasible_candidates
    assert conclusion.witness.objective_codes == oracle.objective_codes


def test_oracle_with_agreeing_solver_incumbent_proves_optimal() -> None:
    """When the floating solver's incumbent happens to equal the oracle's
    proven optimum, publishing it promotes to `optimal_proven` — but the proof
    still flows through the *oracle*, not through the solver evidence. The
    solver only supplies a candidate to be checked against the oracle's truth.
    """
    scenario = _two_asset_pac_scenario()
    view = _primary_view(scenario)
    program = compile_policy_program(scenario, view)
    solver_result = solve_policy_program(program)
    assert solver_result.outcome == "incumbent"
    assert solver_result.candidate is not None

    oracle = run_exhaustive_oracle(scenario, view)
    conclusion = conclude_with_oracle(oracle, published=solver_result.candidate)

    assert isinstance(conclusion, OptimalProvenConclusion)
    assert conclusion.proof_source == "exhaustive_oracle"


def test_oracle_with_no_feasible_candidate_proves_infeasibility() -> None:
    """A genuine unconditional-floor infeasibility (`ORDER_REQUIRED_MIN` above
    the route's reachable cap) makes the exhaustive oracle reject every
    candidate. That promotes to `infeasibility_proven` via `exhaustive_oracle`,
    with a witness carrying zero feasible candidates.
    """
    scenario = _pac_scenario(required=R(50), route_cap=R(10))
    view = _primary_view(scenario)
    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.feasible_candidates == 0
    assert oracle.best_candidate is None

    conclusion = conclude_with_oracle(oracle, published=None)

    assert isinstance(conclusion, InfeasibilityProvenConclusion)
    assert conclusion.kind == "infeasibility_proven"
    assert conclusion.proof_source == "exhaustive_oracle"
    assert conclusion.witness.feasible_candidates == 0
    assert conclusion.witness.enumerated_candidates == oracle.enumerated_candidates


def test_deterministic_conflict_proves_infeasibility() -> None:
    """The exact evaluator's own named contract conflicts prove infeasibility
    with no search at all. An all-zero candidate on the infeasible scenario
    fails specifically on `ORDER_REQUIRED_MIN`, and that becomes an
    `infeasibility_proven` via `deterministic_conflict`.
    """
    scenario = _pac_scenario(required=R(50), route_cap=R(10))
    view = _primary_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, {}, candidate_id="all-zero"))
    assert evaluation.feasible is False
    assert "ORDER_REQUIRED_MIN" in evaluation.conflict_codes

    conclusion = conclude_infeasible_from_conflicts(evaluation)

    assert isinstance(conclusion, InfeasibilityProvenConclusion)
    assert conclusion.kind == "infeasibility_proven"
    assert conclusion.proof_source == "deterministic_conflict"
    assert conclusion.witness.summary_code in conclusion.witness.issue_codes
    assert conclusion.witness.summary_code == "ORDER_REQUIRED_MIN"


def test_feasible_evaluation_yields_no_fabricated_proof() -> None:
    """`conclude_infeasible_from_conflicts` never invents a conflict: a
    feasible evaluation (no conflict codes) downgrades to `not_proven` rather
    than fabricating an infeasibility proof.
    """
    scenario = _two_asset_pac_scenario()
    view = _primary_view(scenario)
    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.best_evaluation is not None
    feasible_evaluation: ExactEvaluation = oracle.best_evaluation
    assert feasible_evaluation.feasible is True
    assert feasible_evaluation.conflict_codes == ()

    conclusion = conclude_infeasible_from_conflicts(feasible_evaluation)

    assert isinstance(conclusion, UnprovenConclusion)
    assert conclusion.kind == "not_proven"


# --------------------------------------------------------------------------
# 4. The oracle proves its OWN optimum only
# --------------------------------------------------------------------------


def test_oracle_optimum_does_not_transfer_to_a_perturbed_published_candidate() -> None:
    """The oracle proves a statement about *its own* optimum. Publish a
    candidate that differs from it — here the best candidate with one
    decision's quanta perturbed — and the proof is downgraded, never
    transferred. Downgrading is sound; transferring would not be.
    """
    scenario = _two_asset_pac_scenario()
    view = _primary_view(scenario)
    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.best_candidate is not None

    original = oracle.best_candidate.decisions[0]
    bumped = dataclasses.replace(original, quanta=original.quanta + 1)
    perturbed = dataclasses.replace(oracle.best_candidate, decisions=(bumped, *oracle.best_candidate.decisions[1:]))

    conclusion = conclude_with_oracle(oracle, published=perturbed)
    assert isinstance(conclusion, UnprovenConclusion)
    assert conclusion.kind == "not_proven"


def test_oracle_optimum_does_not_transfer_when_nothing_is_published() -> None:
    """With a feasible optimum but nothing published, the oracle has proved an
    optimum about no published candidate — so `not_proven`, not `optimal`.
    """
    scenario = _two_asset_pac_scenario()
    oracle = run_exhaustive_oracle(scenario, _primary_view(scenario))
    assert oracle.feasible_candidates > 0

    conclusion = conclude_with_oracle(oracle, published=None)
    assert isinstance(conclusion, UnprovenConclusion)
    assert conclusion.kind == "not_proven"


# --------------------------------------------------------------------------
# 5. describe_conclusion — right keys per kind, and no seal leak
# --------------------------------------------------------------------------


def test_describe_unproven_conclusion_reports_kind_and_reason() -> None:
    described = describe_conclusion(UnprovenConclusion())
    assert dict(described) == {"kind": "not_proven", "reason_code": NOT_PROVEN_REASON}


def test_describe_optimal_proven_conclusion_reports_counts_without_leaking_the_seal() -> None:
    scenario = _two_asset_pac_scenario()
    view = _primary_view(scenario)
    oracle = run_exhaustive_oracle(scenario, view)
    conclusion = conclude_with_oracle(oracle, published=oracle.best_candidate)

    described = describe_conclusion(conclusion)
    assert set(described) == {"kind", "proof_source", "enumerated_candidates", "feasible_candidates"}
    assert described["kind"] == "optimal_proven"
    assert described["proof_source"] == "exhaustive_oracle"
    assert described["enumerated_candidates"] == oracle.enumerated_candidates
    assert described["feasible_candidates"] == oracle.feasible_candidates
    assert "seal" not in described
    assert _SEAL not in described.values()


def test_describe_oracle_infeasibility_reports_exhaustive_oracle_source() -> None:
    scenario = _pac_scenario(required=R(50), route_cap=R(10))
    view = _primary_view(scenario)
    oracle = run_exhaustive_oracle(scenario, view)
    conclusion = conclude_with_oracle(oracle, published=None)

    described = describe_conclusion(conclusion)
    assert set(described) == {"kind", "proof_source", "enumerated_candidates", "feasible_candidates"}
    assert described["kind"] == "infeasibility_proven"
    assert described["proof_source"] == "exhaustive_oracle"
    assert described["feasible_candidates"] == 0
    assert _SEAL not in described.values()


def test_describe_deterministic_conflict_reports_issue_codes_without_leaking_the_seal() -> None:
    scenario = _pac_scenario(required=R(50), route_cap=R(10))
    view = _primary_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, {}, candidate_id="all-zero"))
    conclusion = conclude_infeasible_from_conflicts(evaluation)

    described = describe_conclusion(conclusion)
    assert set(described) == {"kind", "proof_source", "issue_codes"}
    assert described["kind"] == "infeasibility_proven"
    assert described["proof_source"] == "deterministic_conflict"
    assert described["issue_codes"] == ["ORDER_REQUIRED_MIN"]
    assert "seal" not in described
    assert _SEAL not in described.values()
