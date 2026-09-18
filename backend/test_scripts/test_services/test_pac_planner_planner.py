"""Orchestration tests for ``plan_pac_allocation`` (PAC planner v2, Step 3, Stage 5b).

This suite is the durable form of the Stage-5b smoke harness: every property that
throwaway script checked is preserved here, driven from the *same real wire
fixture* (``_pac_request`` → ``pac_plan_request.min.v2.json``) and validated
through ``PAC_PLAN_INPUT_ADAPTER`` before it ever reaches the service. Variants
are built with ``copy.deepcopy`` plus targeted edits, never hand-rolled.

``planner.py`` is one service function with a single non-negotiable spine:

    normalize → build_exact_policy_view → oracle-or-solver
              → evaluate_exact_candidate replay (**always**) → proof → report

The replay is unconditional: neither search is trusted to report its own result.
A candidate that fails replay is not a warning on a published plan — it yields
``ready_no_incumbent`` and nothing is published (test_replay_failure_*). The
locked properties, each mapped to a test:

* **No-op is a first-class optimum, not "no exception".** The unmodified fixture
  has €5 against a €10 whole-unit price, so doing nothing *is* the proven
  optimum. Asserting ``ready_no_op`` **and** ``optimal_proven`` is what caught a
  real defect once (building a ``PacIncumbentSolution``, which needs ≥1 order
  row, before testing for no-op) — the single most common real-world PAC case
  early in the month.
* **The wire-union revalidation is the real gate**: ``model_dump`` →
  ``PAC_PLAN_OUTPUT_ADAPTER.validate_python`` runs every schema validator.
* **``ready_infeasible`` is unreachable from SCIP.** It needs an
  ``InfeasibilityProvenProof``; the wire ``proof_source`` literal admits both
  ``exhaustive_oracle`` and ``deterministic_conflict``, but the planner emits
  **only** the oracle source (see FIX B below) — a floating
  ``reported_infeasible`` maps to ``not_proven``. Its ``stop_reason`` is pinned
  to ``"completed"``.
* **The oracle is routing, never a wire contract**: a domain above the cap falls
  back to the solver and an honest ``not_proven``, never ``optimal_proven``.
* **``plan_rebalancing`` is deliberately absent**, and ``plan_pac_allocation`` is
  deliberately *not* re-exported from the package ``__init__`` so P1 consumers
  do not drag SCIP in at import — pinned by a subprocess (item 9).

These are pure in-process tests (``isolation="pure"``) except the one deliberate
subprocess in ``test_scip_import_isolation_in_subprocess``: no server, no
database, no clock, no sleeps, no network. Exact domain values compare with
``==``; SCIP floats are never compared exactly. Candidate/stage counts are read
off the live result objects, never hardcoded.

TWO FIXED REGRESSIONS this suite now guards. Both were live frozen-code defects
in an earlier dispatch; the production fixes have since landed, so these tests
are their regression guards, not descriptions of outstanding bugs. A
schema-valid, provably-infeasible request (require ≥1 whole unit against €5)
used to make ``plan_pac_allocation`` *raise* instead of returning a result,
violating its own "never raises on a planning outcome" contract, and it did so
on *both* routes to ``ready_infeasible``.

FIX A — the solver is no longer run once the oracle settles the outcome. On the
oracle route the oracle proves infeasibility (``feasible_candidates == 0``)
while a redundant SCIP solve reported the same program ``reported_infeasible``
with **unfinished** stages, and ``PacPlannerReadyInfeasibleResult`` pins
``stop_reason="completed"`` against that unfinished ``solver_evidence``, which
``_validate_stop_evidence`` rejects — a finished stage must carry a finite
primal, which an infeasible solve has none of. ``planner._search`` now tries the
oracle FIRST and, when it settles the outcome, does not run the solver at all:
``_Search.solver is None``, the result carries
``SolverNotRunEvidence(reason="allocation.solver_not_required")`` — which has
**no ``.stages``** — and ``stop_reason == "completed"``, the one combination
``_validate_stop_evidence`` allows for ``not_run`` evidence. When the oracle
does not run (domain above the cap) the solver runs as before and evidence is
``ReportedFloatingSolverEvidence`` with ``.stages``. (test_forced_infeasible_*,
test_oracle_settled_*, test_solver_route_*.)

FIX B — ``deterministic_conflict`` is no longer emitted. When the oracle was
bypassed (domain over the cap) and the do-nothing candidate carried a conflict,
the planner used to call ``conclude_infeasible_from_conflicts`` and
``_wire_infeasibility`` built a ``DeterministicConflictWitness`` from the
evaluator's *internal* conflict codes (e.g. ``ORDER_REQUIRED_MIN``), which are
not members of the wire ``PlannerIssueCode`` enum — so it raised too. The
planner no longer calls that path: ``DeterministicConflictWitness.issue_codes``
is ``list[PlannerIssueCode]`` (the frozen 80-value ``allocation.*`` universe)
while ``ExactEvaluation.conflict_codes`` carries exact-domain codes such as
``ORDER_REQUIRED_MIN``. Two different vocabularies, and no bridge should be
invented: a normalization-time statement about *declared inputs* and an
evaluation-time statement about a *candidate* are not the same claim, so a
mapping table would manufacture an equivalence and publish it as a **witness** —
exactly what ``proof.py`` exists to make unrepresentable. Proven infeasibility
now comes from the oracle alone; everything else is honestly ``not_proven``, and
``_wire_infeasibility`` accepts only the ``exhaustive_oracle`` source and raises
if handed anything else. The schema literal still admits both values (that is the
wire shape, not ours to change), and ``proof.py`` still recognises the
``deterministic_conflict`` *source* at the conclusion layer — the planner simply
never projects it. Item 7 is still tested structurally through the real proof
layer. (test_deterministic_conflict_*, test_forced_min_over_cap_*.)
"""

from __future__ import annotations

import copy
import os
import subprocess
import sys
import textwrap
from fractions import Fraction
from pathlib import Path
from typing import get_args

import pytest

from backend.app.schemas.pac_allocator import (
    PAC_PLAN_INPUT_ADAPTER,
    PAC_PLAN_OUTPUT_ADAPTER,
    InfeasibilityProvenProof,
    PacPlannerInvalidResult,
    PacPlannerNeedsInputResult,
    PacPlannerReadyIncumbentResult,
    PacPlannerReadyInfeasibleResult,
    PacPlannerReadyNoIncumbentResult,
    PacPlannerReadyNoOpResult,
    PacPlannerUnsupportedResult,
    PlannerResultSnapshot,
    ReportedFloatingSolverEvidence,
    SolverNotRunEvidence,
)
from backend.app.services.pac_allocator import planner
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view
from backend.app.services.pac_allocator.normalize import normalize_pac_plan
from backend.app.services.pac_allocator.oracle import (
    MAX_EXHAUSTIVE_ORACLE_CANDIDATES,
    OracleDomainTooLargeError,
    run_exhaustive_oracle,
)
from backend.app.services.pac_allocator.planner import plan_pac_allocation
from backend.app.services.pac_allocator.proof import (
    InfeasibilityProvenConclusion,
    UnprovenConclusion,
    conclude_infeasible_from_conflicts,
    conclude_with_oracle,
    conclude_without_proof,
)
from backend.app.services.pac_allocator.solver import solve_policy_program
from backend.test_scripts.test_schemas.test_pac_planner_schemas import _pac_request

# The repository root: parents = [test_services, test_scripts, backend, <root>].
REPO_ROOT = Path(__file__).resolve().parents[3]

_ZERO_CANDIDATE_ID = "plan:zero"  # id the planner gives the do-nothing re-evaluation


# --------------------------------------------------------------------------
# Request builders — a fresh dict every call (``_pac_request`` re-reads JSON),
# deepcopy + targeted edits, validated through the real input adapter.
# --------------------------------------------------------------------------
def _validated(payload: dict):
    return PAC_PLAN_INPUT_ADAPTER.validate_python(payload)


def _revalidate(result):
    """The real gate: dump to python and re-validate against the wire union."""
    return PAC_PLAN_OUTPUT_ADAPTER.validate_python(result.model_dump(mode="python"))


def _incumbent_payload() -> dict:
    """The no-op fixture, but with enough cash (€50) to buy whole units.

    €50 against a €10 whole-unit price buys 5 units, so the proven optimum stops
    being "do nothing" and becomes a single BUY.
    """
    payload = _pac_request()
    for cash in payload["existing_cash"]:
        cash["available"]["amount"] = "50.00"
        cash["selected"]["amount"] = "50.00"
    # The min fixture ships no funding_routes; still raise any transfer_cap a
    # future variant might carry so raised cash can actually reach the broker.
    for route in payload.get("funding_routes", []):
        cap = route.get("transfer_cap")
        if isinstance(cap, dict) and cap.get("kind") == "amount":
            cap["amount"]["amount"] = "1000000.00"
    return payload


def _forced_min_payload() -> dict:
    """A provably-infeasible request: require ≥1 whole unit against €5 / €10 unit.

    Normalizes cleanly (infeasibility is a *search* result, not a normalization
    error); the oracle then proves 0 feasible candidates and the do-nothing
    candidate carries an ``ORDER_REQUIRED_MIN`` conflict.
    """
    payload = _pac_request()
    payload["order_routes"][0]["required_minimum"] = {"kind": "whole_quantity", "quantity": "1", "unit": "asset_unit"}
    return payload


def _empty_assets_payload() -> dict:
    payload = _pac_request()
    payload["assets"] = []
    return payload


def _duplicate_provenance_payload() -> dict:
    payload = _pac_request()
    payload["provenance"].append(copy.deepcopy(payload["provenance"][0]))
    return payload


def _negative_cash_payload() -> dict:
    payload = _pac_request()
    for cash in payload["existing_cash"]:
        cash["available"]["amount"] = "-5.00"
        cash["selected"]["amount"] = "-5.00"
    return payload


# --------------------------------------------------------------------------
# Fixtures — the two canonical ready results, computed once per module (pure,
# immutable pydantic models, safe to share read-only).
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def noop_result():
    return plan_pac_allocation(_validated(_pac_request()))


@pytest.fixture(scope="module")
def incumbent_result():
    return plan_pac_allocation(_validated(_incumbent_payload()))


@pytest.fixture(params=["no_op", "incumbent"])
def ready_result(request, noop_result, incumbent_result):
    """Every ready result the fixture can produce end-to-end, one at a time."""
    return {"no_op": noop_result, "incumbent": incumbent_result}[request.param]


# --------------------------------------------------------------------------
# Item 1 — the no-op-optimal fixture (a REQUIREMENT: state AND proof, not "no
# exception").
# --------------------------------------------------------------------------
def test_unmodified_fixture_is_no_op_optimal(noop_result):
    """€5 vs a €10 whole-unit price ⇒ doing nothing is the proven optimum.

    This asserts the *shape*, not merely the absence of an exception: a
    ``PacIncumbentSolution`` needs ≥1 order row, so building one before testing
    for no-op is the exact defect this case exists to catch.
    """
    assert isinstance(noop_result, PacPlannerReadyNoOpResult)
    assert noop_result.result_state == "ready_no_op"
    assert noop_result.outcome == "no_op"
    assert noop_result.proof.kind == "optimal_proven"
    # The oracle is what makes ``optimal_proven`` reachable at all.
    assert noop_result.proof.proof_source == "exhaustive_oracle"

    solution = noop_result.primary_solution
    assert solution.validation == "decimal_verified"
    assert solution.order_rows == []
    assert solution.funding_actions == []
    assert solution.fx_actions == []
    _revalidate(noop_result)


# --------------------------------------------------------------------------
# Item 2 — incumbent path end-to-end.
# --------------------------------------------------------------------------
def test_incumbent_path_end_to_end(incumbent_result):
    """€50 buys 5 whole units ⇒ one BUY, €50 debited, decimal-verified."""
    assert isinstance(incumbent_result, PacPlannerReadyIncumbentResult)
    assert incumbent_result.result_state == "ready_incumbent"
    assert incumbent_result.outcome == "incumbent_found"

    solution = incumbent_result.primary_solution
    assert solution.validation == "decimal_verified"
    assert len(solution.order_rows) == 1

    order = solution.order_rows[0]
    assert order.cash_debit.currency == "EUR"
    assert Fraction(order.cash_debit.amount) == Fraction(50)
    _revalidate(incumbent_result)


# --------------------------------------------------------------------------
# Item 3 — wire-union revalidation for every ready result.
# --------------------------------------------------------------------------
def test_ready_output_revalidates_against_wire_union(ready_result):
    revalidated = _revalidate(ready_result)
    assert revalidated is not None
    assert revalidated.result_state == ready_result.result_state


# --------------------------------------------------------------------------
# Item 4 — the three failure availabilities, end-to-end and via the mapping.
# --------------------------------------------------------------------------
_FAILURES = [
    pytest.param(_empty_assets_payload, "needs_input", "missing", PacPlannerNeedsInputResult, id="needs_input"),
    pytest.param(_duplicate_provenance_payload, "invalid", "invalid", PacPlannerInvalidResult, id="invalid"),
    pytest.param(_negative_cash_payload, "unsupported", "unsupported", PacPlannerUnsupportedResult, id="unsupported"),
]


@pytest.mark.parametrize(("builder", "availability", "issue_kind", "result_type"), _FAILURES)
def test_failure_availabilities_end_to_end(builder, availability, issue_kind, result_type):
    """A failure is a *result*, never an exception, and always carries an issue."""
    result = plan_pac_allocation(_validated(builder()))
    assert isinstance(result, result_type)
    assert result.result_state == availability
    assert result.availability == availability
    assert len(result.issues) >= 1
    assert any(issue.kind == issue_kind and issue.severity == "error" for issue in result.issues)
    _revalidate(result)


@pytest.mark.parametrize(("builder", "availability", "issue_kind", "result_type"), _FAILURES)
def test_failure_result_mapping_is_direct(builder, availability, issue_kind, result_type):
    """``_failure_result`` maps each normalizer availability onto its wire type.

    Belt-and-suspenders for the end-to-end coverage above: it pins the mapping
    itself using the *real* issues the normalizer produced, so a future change
    to ``plan_pac_allocation``'s routing cannot silently mis-file a failure.
    """
    request = _validated(builder())
    outcome = normalize_pac_plan(request)
    assert outcome.availability == availability
    snapshot = PlannerResultSnapshot(snapshot_id=request.snapshot.snapshot_id, request_fingerprint=request.snapshot.snapshot_id)

    result = planner._failure_result(outcome.availability, snapshot, list(outcome.issues))
    assert isinstance(result, result_type)
    assert result.result_state == availability
    assert len(result.issues) >= 1
    assert any(issue.kind == issue_kind and issue.severity == "error" for issue in result.issues)


# --------------------------------------------------------------------------
# Item 5 — replay failure suppresses the plan (ready_no_incumbent, no solution).
# --------------------------------------------------------------------------
class _InfeasibleReplay:
    """A stand-in the planner only ever reads ``.feasible`` from.

    The replay result is discarded the moment ``.feasible`` is read (the planner
    re-derives everything else from the do-nothing candidate), so a lightweight
    object is enough — and honest about what the planner actually consumes.
    """

    feasible = False


def test_replay_failure_suppresses_the_plan(monkeypatch):
    """A candidate that fails exact replay yields no publishable plan.

    The forced infeasibility is applied only to the *published* candidate; the
    do-nothing re-evaluation inside ``_no_incumbent_result`` (id ``plan:zero``)
    stays real so the scenario basis and report can still be built. The would-be
    incumbent is therefore suppressed rather than degraded into a warning.
    """
    real_evaluate = planner.evaluate_exact_candidate

    def replay(scenario, view, candidate, *, checkpoint=None):
        if candidate.candidate_id == _ZERO_CANDIDATE_ID:
            return real_evaluate(scenario, view, candidate, checkpoint=checkpoint)
        return _InfeasibleReplay()

    monkeypatch.setattr(planner, "evaluate_exact_candidate", replay)
    result = plan_pac_allocation(_validated(_incumbent_payload()))

    assert isinstance(result, PacPlannerReadyNoIncumbentResult)
    assert result.result_state == "ready_no_incumbent"
    assert result.proof.kind == "not_proven"
    assert not hasattr(result, "primary_solution")
    _revalidate(result)


# --------------------------------------------------------------------------
# Item 6 — oracle-too-large falls back to the solver and an honest not_proven.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("payload_builder", [_pac_request, _incumbent_payload], ids=["no_op", "incumbent"])
@pytest.mark.parametrize("mechanism", ["domain_estimate", "oracle_raises"])
def test_oracle_too_large_falls_back_to_honest_not_proven(monkeypatch, payload_builder, mechanism):
    """A domain above the cap degrades honestly — a ready result, never a failure,
    whose proof is ``not_proven`` and *never* ``optimal_proven``.

    Both routing exits are exercised: the pre-check estimate exceeding the cap,
    and ``run_exhaustive_oracle`` raising ``OracleDomainTooLargeError``.
    """
    if mechanism == "domain_estimate":
        monkeypatch.setattr(planner, "estimate_oracle_domain_size", lambda view: MAX_EXHAUSTIVE_ORACLE_CANDIDATES + 1)
    else:

        def _too_large(scenario, view, *, checkpoint=None, **_):
            raise OracleDomainTooLargeError("forced oversize domain")

        monkeypatch.setattr(planner, "run_exhaustive_oracle", _too_large)

    result = plan_pac_allocation(_validated(payload_builder()))
    assert result.availability == "ready"
    assert result.proof.kind == "not_proven"
    _revalidate(result)


# --------------------------------------------------------------------------
# Item 7 — ready_infeasible and the two infeasibility sources.
#
# The natural end-to-end ``ready_infeasible`` now WORKS (FIX A): the oracle
# settles the outcome and the solver is not run, so ``not_run`` evidence coexists
# with the pinned ``stop_reason="completed"``. The ``deterministic_conflict``
# source is real at the ``proof.py`` conclusion layer but is deliberately NOT
# projected onto the wire (FIX B). See the module docstring.
# --------------------------------------------------------------------------
def _forced_min_scenario_view():
    request = _validated(_forced_min_payload())
    outcome = normalize_pac_plan(request)
    assert outcome.ready, "forced-min request must normalize; infeasibility is a search result"
    scenario = outcome.normalized
    return scenario, build_exact_policy_view(scenario, purpose="primary")


def test_infeasibility_conclusion_sources_and_scip_non_promotion():
    """The two legal infeasibility sources at the ``proof.py`` conclusion layer,
    and a floating SCIP ``reported_infeasible`` shown to be non-promotable.

    ``proof.py`` is frozen and still recognises BOTH sources at the conclusion
    layer; FIX B changed only whether the *planner* projects the conflict source
    onto the wire — it does not (see ``test_deterministic_conflict_is_not_emitted``).
    """
    scenario, view = _forced_min_scenario_view()

    # Source 1: the exhaustive oracle proves the whole discrete domain infeasible,
    # and this source wires cleanly onto the InfeasibilityProvenProof.
    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.feasible_candidates == 0  # read off the live result, not hardcoded
    oracle_proof = planner._wire_infeasibility(conclude_with_oracle(oracle, published=None))
    assert oracle_proof.kind == "infeasibility_proven"
    assert oracle_proof.proof_source == "exhaustive_oracle"

    # Source 2: the do-nothing candidate carries a deterministic contract conflict
    # (``ORDER_REQUIRED_MIN``) the proof layer reads directly, with no search.
    # Asserted at the conclusion level: the conflict source is real in the frozen
    # ``proof.py``, even though the planner never projects it onto the wire —
    # ``_wire_infeasibility`` rejects it (FIX B), which the vocabulary-mismatch
    # reasoning in ``test_deterministic_conflict_is_not_emitted`` explains.
    zero_eval = planner._zero_candidate_evaluation(scenario, view)
    assert zero_eval.conflict_codes  # the ORDER_REQUIRED_MIN conflict
    conflict_conclusion = conclude_infeasible_from_conflicts(zero_eval)
    assert isinstance(conflict_conclusion, InfeasibilityProvenConclusion)
    assert conflict_conclusion.proof_source == "deterministic_conflict"

    assert {oracle_proof.proof_source, conflict_conclusion.proof_source} == {"exhaustive_oracle", "deterministic_conflict"}

    # The point of the whole package, unchanged: a floating SCIP infeasible cannot
    # become a proof. It is reported_infeasible, and its conclusion is not_proven.
    solver = solve_policy_program(compile_policy_program(scenario, view))
    assert solver.outcome == "reported_infeasible"
    scip_conclusion = conclude_without_proof(solver)
    assert isinstance(scip_conclusion, UnprovenConclusion)
    assert planner._wire_proof(scip_conclusion).kind == "not_proven"


def test_ready_infeasible_result_type_pins_completed_and_infeasibility_proof():
    """The wire contract itself forbids any other shape for ``ready_infeasible``.

    The ``proof_source`` literal still admits BOTH ``exhaustive_oracle`` and
    ``deterministic_conflict`` — that is the schema's shape, unchanged by FIX B,
    which only stopped the *planner* from projecting the conflict source. This
    assertion stays exactly to pin that the schema shape is not ours to narrow.
    """
    fields = PacPlannerReadyInfeasibleResult.model_fields
    assert get_args(fields["stop_reason"].annotation) == ("completed",)
    assert fields["proof"].annotation is InfeasibilityProvenProof
    proof_source = InfeasibilityProvenProof.model_fields["proof_source"].annotation
    assert set(get_args(proof_source)) == {"exhaustive_oracle", "deterministic_conflict"}


def test_forced_infeasible_returns_ready_infeasible_not_raise():
    """FIX A, end-to-end: a provably-infeasible plan RETURNS ``ready_infeasible``.

    Regression origin — a real defect. This input (``required_minimum`` 1 whole
    unit, €5 cash against a €10 unit price) once made ``plan_pac_allocation``
    *raise* a ``ValidationError`` instead of returning a result, breaking its own
    "never raises on a planning outcome" contract on a perfectly ordinary
    infeasible input. The oracle proved infeasibility while a redundant SCIP
    solve reported the same program ``reported_infeasible`` with unfinished
    stages, and ``stop_reason="completed"`` against that unfinished evidence was
    rejected by ``_validate_stop_evidence``. The fix runs the oracle first and,
    once it settles the outcome, does not run the solver at all: ``not_run``
    evidence + ``stop_reason="completed"`` is exactly the pair the validator
    allows.
    """
    result = plan_pac_allocation(_validated(_forced_min_payload()))
    assert isinstance(result, PacPlannerReadyInfeasibleResult)
    assert result.result_state == "ready_infeasible"
    assert result.outcome == "infeasible_proven"
    assert result.proof.kind == "infeasibility_proven"
    assert result.proof.proof_source == "exhaustive_oracle"
    assert result.stop_reason == "completed"
    # No solver ran, so evidence is the not_run variant, not floating stages.
    assert isinstance(result.solver_evidence, SolverNotRunEvidence)
    assert result.solver_evidence.reason == "allocation.solver_not_required"
    _revalidate(result)  # the real gate: revalidate through the wire union


def test_deterministic_conflict_is_not_emitted(noop_result, incumbent_result):
    """FIX B: ``deterministic_conflict`` is never published in phase 1.

    ``DeterministicConflictWitness.issue_codes`` is ``list[PlannerIssueCode]``
    (the frozen 80-value ``allocation.*`` wire universe) while
    ``ExactEvaluation.conflict_codes`` carries exact-domain codes such as
    ``ORDER_REQUIRED_MIN``. Two different vocabularies, and no bridge should be
    invented: a normalization-time statement about *declared inputs* and an
    evaluation-time statement about a *candidate* are not the same claim, so a
    mapping table would manufacture an equivalence and publish it as a
    **witness** — exactly what ``proof.py`` exists to make unrepresentable. So
    ``_wire_infeasibility`` accepts only the oracle source and raises otherwise,
    and no end-to-end result carries the conflict source.
    """
    # (1) The wire projection rejects a conflict-sourced conclusion outright.
    scenario, view = _forced_min_scenario_view()
    zero_eval = planner._zero_candidate_evaluation(scenario, view)
    conflict_conclusion = conclude_infeasible_from_conflicts(zero_eval)
    assert conflict_conclusion.proof_source == "deterministic_conflict"
    with pytest.raises(ValueError):
        planner._wire_infeasibility(conflict_conclusion)

    # (2) No result the planner produces carries a deterministic_conflict proof.
    results = [
        noop_result,
        incumbent_result,
        plan_pac_allocation(_validated(_forced_min_payload())),
        plan_pac_allocation(_validated(_empty_assets_payload())),
        plan_pac_allocation(_validated(_duplicate_provenance_payload())),
        plan_pac_allocation(_validated(_negative_cash_payload())),
    ]
    for result in results:
        proof = getattr(result, "proof", None)
        assert getattr(proof, "proof_source", None) != "deterministic_conflict"


def test_forced_min_over_cap_degrades_to_not_proven(monkeypatch):
    """FIX B: with the oracle bypassed, an infeasible domain degrades honestly.

    Above the oracle cap the oracle does not run, so the do-nothing candidate's
    ``ORDER_REQUIRED_MIN`` conflict is the only signal. The planner used to feed
    that to ``conclude_infeasible_from_conflicts`` and raise while wiring a
    ``DeterministicConflictWitness`` from non-wire codes; it now never calls that
    path. Proven infeasibility comes from the oracle alone, so an over-cap
    infeasible domain becomes ``ready_no_incumbent`` / ``not_proven`` — a result,
    never a raise, never a ``deterministic_conflict``. The floating SCIP evidence
    is unfinished (an infeasible solve has no finite primal, so no stage can
    finish), which is exactly why a floating ``reported_infeasible`` can only be
    ``not_proven`` and never a proof.
    """
    monkeypatch.setattr(planner, "estimate_oracle_domain_size", lambda view: MAX_EXHAUSTIVE_ORACLE_CANDIDATES + 1)
    result = plan_pac_allocation(_validated(_forced_min_payload()))
    assert isinstance(result, PacPlannerReadyNoIncumbentResult)
    assert result.result_state == "ready_no_incumbent"
    assert result.proof.kind == "not_proven"
    assert not hasattr(result.proof, "proof_source")
    assert isinstance(result.solver_evidence, ReportedFloatingSolverEvidence)
    # An infeasible solve cannot finish a stage, so the stop is a limit, not
    # "completed" — the honest not_proven degradation, not a proof.
    assert any(stage.status == "unfinished" for stage in result.solver_evidence.stages)
    assert result.stop_reason != "completed"
    _revalidate(result)


# --------------------------------------------------------------------------
# Item 8 — plan_rebalancing is absent; __all__ is minimal.
# --------------------------------------------------------------------------
def test_plan_rebalancing_is_absent_and_all_is_minimal():
    """Absent beats always-failing.

    Every Rebalancer policy and the SELL verifier are deferred. A
    ``plan_rebalancing`` that existed but always failed would invite wiring; an
    absent one fails at import, in the exact place the missing work is obvious.
    So the export surface is a single function and nothing more.
    """
    assert not hasattr(planner, "plan_rebalancing")
    assert planner.__all__ == ["plan_pac_allocation"]


# --------------------------------------------------------------------------
# Item 9 — SCIP import isolation, verified in a SUBPROCESS.
# --------------------------------------------------------------------------
_IMPORT_ISOLATION_PROBE = textwrap.dedent("""
    import sys
    import backend.app.services.pac_allocator  # the lightweight P1 package
    assert "pyscipopt" not in sys.modules, "pyscipopt leaked from the package __init__"
    import backend.app.services.pac_allocator.planner  # planner -> compiler -> pyscipopt
    assert "pyscipopt" in sys.modules, "pyscipopt missing after importing planner"
    print("IMPORT-ISOLATION-OK")
    """)


def test_scip_import_isolation_in_subprocess():
    """``plan_pac_allocation`` is deliberately not re-exported from the package.

    The chain ``planner -> compiler -> pyscipopt`` (``compiler.py`` imports
    ``Model`` at module level because it instantiates one) means re-exporting it
    from ``__init__`` would drag SCIP into every consumer of the lightweight P1
    analyses and silently falsify the package's "No solver" promise. An absent
    export with no explanation is indistinguishable from an oversight — so this
    test *is* the explanation. It runs in a fresh interpreter because in-process
    the modules are already loaded by sibling tests and the assertion would be
    vacuous.
    """
    proc = subprocess.run(
        [sys.executable, "-c", _IMPORT_ISOLATION_PROBE],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr[-2000:]!r}"
    assert "IMPORT-ISOLATION-OK" in proc.stdout


# --------------------------------------------------------------------------
# Item 10 — sequence, containment and evidence properties on ready results.
# --------------------------------------------------------------------------
def _action_sequences(solution) -> list[int]:
    return [row.sequence for row in (*solution.funding_actions, *solution.fx_actions, *solution.order_rows)]


def _referenced_provenance(solution) -> set[str]:
    rows = (*solution.funding_actions, *solution.fx_actions, *solution.order_rows, *solution.exposure_rows)
    return {provenance_id for row in rows for provenance_id in row.provenance_ids}


def test_ready_result_sequence_and_containment_properties(ready_result):
    """Global sequence uniqueness, per-section ascent, provenance containment,
    honest deployment, and evidence that matches the search that ran — read off
    the live result.

    Solver evidence is a ``PlannerSolverEvidence`` union, so the check branches
    on the variant rather than assuming floating stages: an oracle-settled
    result carries ``SolverNotRunEvidence`` (no ``.stages``), while a solver-run
    result carries ``ReportedFloatingSolverEvidence`` with ≥1 stage (min_length=1)
    and no ``tie:*`` leakage — the wire ObjectiveCode enum cannot express those
    stages.
    """
    evidence = ready_result.solver_evidence
    if isinstance(evidence, ReportedFloatingSolverEvidence):
        assert len(evidence.stages) >= 1
        assert all(not stage.objective_code.startswith("tie") for stage in evidence.stages)
    else:
        assert isinstance(evidence, SolverNotRunEvidence)
        assert evidence.kind == "not_run"
        assert evidence.reason == "allocation.solver_not_required"
    assert ready_result.stop_reason in {"completed", "time_limit", "node_limit"}
    assert ready_result.proof.kind in {"optimal_proven", "not_proven", "infeasibility_proven"}
    assert ready_result.deployment.reason_code == "allocation.deployment_omitted"

    solution = ready_result.primary_solution
    sequences = _action_sequences(solution)
    assert len(sequences) == len(set(sequences))  # globally unique across funding/fx/order
    for section in (solution.funding_actions, solution.fx_actions, solution.order_rows):
        section_sequences = [row.sequence for row in section]
        assert section_sequences == sorted(section_sequences)  # each section internally ascending

    published = {provenance.provenance_id for provenance in ready_result.provenance}
    assert _referenced_provenance(solution) <= published


# --------------------------------------------------------------------------
# Item 11 — the PlannerSolverEvidence union and the stop/evidence invariant.
# FIX A: the oracle-settled route carries not_run evidence and a completed stop;
# the over-cap route carries reported_floating evidence. Both arms are observed.
# --------------------------------------------------------------------------
def test_oracle_settled_results_carry_not_run_evidence(ready_result):
    """FIX A: both small-domain fixtures go the oracle route, so the solver is
    never run — evidence is ``not_run`` and the stop is ``completed``.

    Before the fix the planner ran SCIP even when the oracle had already settled
    the outcome; that redundant solve is what made an ordinary infeasible
    scenario unemittable. Here the fixtures are feasible, but the routing is the
    same: an oracle that settles the outcome leaves ``_Search.solver is None``,
    so the wire evidence is ``SolverNotRunEvidence`` and nothing stopped early.
    """
    evidence = ready_result.solver_evidence
    assert isinstance(evidence, SolverNotRunEvidence)
    assert evidence.kind == "not_run"
    assert evidence.reason == "allocation.solver_not_required"
    assert ready_result.stop_reason == "completed"
    _revalidate(ready_result)


def test_not_run_evidence_implies_completed_stop(ready_result):
    """The union invariant, tied to ``_validate_stop_evidence``'s own rule.

    ``_validate_stop_evidence`` requires a limit stop (``time_limit`` /
    ``node_limit``) to carry ``reported_floating`` evidence, so ``not_run``
    evidence can *only* coexist with ``stop_reason == "completed"``. The
    ``completed`` ⇔ no-unfinished-stage biconditional the validator also enforces
    applies **inside** the floating branch only — there is no notion of an
    unfinished stage when the solver never ran. Asserted as a property of every
    ready result the fixture produces, so a routing regression that emitted a
    limit stop against ``not_run`` evidence would fail here rather than deep in
    the wire validator.
    """
    evidence = ready_result.solver_evidence
    if isinstance(evidence, SolverNotRunEvidence):
        assert ready_result.stop_reason == "completed"
    else:
        assert isinstance(evidence, ReportedFloatingSolverEvidence)
        unfinished = any(stage.status == "unfinished" for stage in evidence.stages)
        # Inside the floating branch: completed iff no stage is unfinished.
        assert (ready_result.stop_reason == "completed") == (not unfinished)


@pytest.mark.parametrize("payload_builder", [_pac_request, _incumbent_payload], ids=["no_op", "incumbent"])
def test_solver_route_carries_reported_floating_evidence(monkeypatch, payload_builder):
    """The other arm of the union: when the domain is above the oracle cap the
    solver runs, and its evidence is ``ReportedFloatingSolverEvidence`` with ≥1
    stage.

    This makes the union explicit — the same fixtures that carry ``not_run``
    evidence on the oracle route carry floating stages on the solver route — and
    exercises the floating half of the ``completed`` ⇔ no-unfinished-stage
    biconditional that ``not_run`` evidence can never reach.
    """
    monkeypatch.setattr(planner, "estimate_oracle_domain_size", lambda view: MAX_EXHAUSTIVE_ORACLE_CANDIDATES + 1)
    result = plan_pac_allocation(_validated(payload_builder()))
    assert result.availability == "ready"
    evidence = result.solver_evidence
    assert isinstance(evidence, ReportedFloatingSolverEvidence)
    assert len(evidence.stages) >= 1
    unfinished = any(stage.status == "unfinished" for stage in evidence.stages)
    assert (result.stop_reason == "completed") == (not unfinished)
    _revalidate(result)
