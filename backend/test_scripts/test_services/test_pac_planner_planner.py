"""Orchestration tests for ``plan_pac_allocation`` (PAC planner v2).

This suite is the durable form of the Stage-5b smoke harness, driven from the
*same real wire fixture* (``_pac_request`` → ``pac_plan_request.min.v2.json``)
and validated through ``PAC_PLAN_INPUT_ADAPTER`` before it ever reaches the
service. Variants are built with ``copy.deepcopy`` plus targeted edits, never
hand-rolled.

``planner.py`` is one service function with a single non-negotiable spine:

    normalize → build_exact_policy_view → compile → SCIP
              → evaluate_exact_candidate replay (**always**) → proof → report

SCIP is the only production search engine, and since D-X1 its own status is
the proof: ``proof.conclude_with_solver`` is the only reader of it. The replay
is unconditional: SCIP is never trusted to report its own result. A candidate
the replay rejects is not a warning on a published plan — it yields
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
* **An optimum is SCIP's own status.** Every stage finished ``optimal`` on the
  plan the replay accepted ⇒ ``optimal_proven`` from ``solver_status``, whose
  witness names the published objective stages in order. The evidence is always
  ``reported_floating``: SCIP runs on every ready result.
* **``ready_infeasible`` is SCIP's verdict on the first, still-global stage**:
  ``infeasibility_proven`` from ``solver_status``, one stage of evidence with no
  primal, dual or gap, and ``stop_reason="completed"`` — the search ended on a
  verdict, not on a limit.
* **A limit is never a proof**: a budget that stops SCIP before a stage closes
  is ``ready_no_incumbent`` / ``not_proven`` with a limit stop, and its
  unfinished stages report nothing they did not observe.
* **The exhaustive oracle is a test instrument**: production cannot import it
  and its old module path no longer resolves (test_exhaustive_oracle_is_test_only);
  a domain far too large to enumerate is planned without enumerating it
  (test_x1_*).
* **``plan_rebalancing`` is deliberately absent**, and ``plan_pac_allocation`` is
  deliberately *not* re-exported from the package ``__init__`` so P1 consumers
  do not drag SCIP in at import — pinned by a subprocess (item 9).

These are pure in-process tests (``isolation="pure"``) except the one deliberate
subprocess in ``test_scip_import_isolation_in_subprocess``: no server, no
database, no clock, no sleeps, no network. Exact domain values compare with
``==``; SCIP floats are never compared exactly. Candidate/stage counts are read
off the live result objects, never hardcoded.

A FIXED REGRESSION this suite guards: a schema-valid, provably infeasible
request (require ≥1 whole unit against €5) used to make ``plan_pac_allocation``
*raise* instead of returning a result, violating its own "never raises on a
planning outcome" contract. It now returns ``ready_infeasible``, proven by
SCIP's own status (test_forced_infeasible_*).
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import math
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
)
from backend.app.services.pac_allocator import planner
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view
from backend.app.services.pac_allocator.normalize import normalize_pac_plan
from backend.app.services.pac_allocator.planner import plan_pac_allocation
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
    error). No oracle runs in production: SCIP closes the first, still-global
    stage ``infeasible``, and that status is the proof.
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


_ASSET_ONE_ID = "asset-one"
_ASSET_ONE_ROUTE_ID = "route-asset-one-broker-one-buy"
_ASSET_TWO_ID = "asset-two"
_ASSET_TWO_ROUTE_ID = "route-asset-two-broker-one-buy"


def _two_etf_contribution_payload() -> dict:
    """Pure PAC, the X1 shape: no existing cash, one €100 contribution, two ETFs.

    The fixture's Asset repriced to €40 plus a copy at €60 on the same Broker,
    target 0.5/0.5, one BUY route each, and one funding route able to move the
    whole contribution to the Broker. The exact optimum is one whole unit of
    each: €40 + €60 spend the contribution exactly, and every other whole-unit
    mix lands further from the €50/€50 target.
    """
    payload = _pac_request()
    asset_one = next(row for row in payload["assets"] if row["asset_id"] == _ASSET_ONE_ID)
    asset_one["quote"]["amount"] = "40.00"
    asset_two = copy.deepcopy(asset_one)
    asset_two["asset_id"] = _ASSET_TWO_ID
    asset_two["identity"] = {"kind": "manual_asset", "name": "Synthetic Asset Two", "ticker": "SYN2", "asset_class": "etf"}
    asset_two["quote"]["amount"] = "60.00"
    payload["assets"].append(asset_two)

    route_one = next(row for row in payload["order_routes"] if row["route_id"] == _ASSET_ONE_ROUTE_ID)
    route_two = copy.deepcopy(route_one)
    route_two["route_id"] = _ASSET_TWO_ROUTE_ID
    route_two["asset_id"] = _ASSET_TWO_ID
    payload["order_routes"].append(route_two)

    payload["target_weights"] = [{"asset_id": _ASSET_ONE_ID, "weight": "0.5"}, {"asset_id": _ASSET_TWO_ID, "weight": "0.5"}]
    payload["existing_cash"] = []
    payload["contributions"] = [{"contribution_id": "contribution-one", "label": "Monthly", "amount": {"amount": "100.00", "currency": "EUR"}, "provenance_id": "prov-manual"}]
    payload["funding_routes"] = [
        {
            "funding_route_id": "funding-contribution-one-broker-one",
            "source": {"kind": "contribution", "contribution_id": "contribution-one"},
            "broker_id": "broker-one",
            "currency": "EUR",
            "priority": 1,
            "transfer_cap": {"amount": "100.00", "currency": "EUR"},
            "provenance_id": "prov-manual",
        }
    ]
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
    # SCIP closed every stage optimal on the plan the replay accepted: its own
    # status is the proof (D-X1), so doing nothing is proven, not presumed.
    assert noop_result.proof.proof_source == "solver_status"

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

    SCIP itself finished: every stage closed, so the stop is ``completed``, not a
    limit. ``ready_no_incumbent`` with ``completed`` is exactly the state the UI's
    "replay rejected" notice keys on — the one no-plan outcome no budget explains.
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

    assert result.stop_reason == "completed"
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(result, mode="json", by_alias=True)
    stages = wire["solver_evidence"]["stages"]
    assert stages, "the replay-rejected result must still report the stages SCIP ran"
    assert {stage["status"] for stage in stages} == {"finished"}, stages
    _revalidate(result)


# --------------------------------------------------------------------------
# Item 6 — a limit is never a proof: a budget that stops SCIP before any stage
# closes is an honest ready_no_incumbent / not_proven with a limit stop.
# --------------------------------------------------------------------------
def test_exhausted_solver_budget_degrades_to_honest_not_proven():
    """A search stopped by its budget publishes nothing and proves nothing.

    With no time at all SCIP closes no stage, so there is no candidate to
    replay and no status to conclude from: ``ready_no_incumbent`` with
    ``not_proven``, and a ``time_limit`` stop because the search ended on a
    limit, not on a verdict. The evidence still reports the stages — as
    ``unfinished``, with no primal, dual or gap, because SCIP observed none: an
    unfinished stage never carries a fabricated observation.
    """
    result = plan_pac_allocation(_validated(_incumbent_payload()), solver_time_budget_seconds=0.0)

    assert isinstance(result, PacPlannerReadyNoIncumbentResult)
    assert (result.result_state, result.outcome) == ("ready_no_incumbent", "no_incumbent")
    assert (result.proof.kind, result.proof.reason_code) == ("not_proven", "allocation.exact_proof_not_established")
    assert result.stop_reason == "time_limit"
    assert not hasattr(result, "primary_solution")

    evidence = result.solver_evidence
    assert isinstance(evidence, ReportedFloatingSolverEvidence)
    unfinished = [stage for stage in evidence.stages if stage.status == "unfinished"]
    assert unfinished, evidence.stages
    for stage in unfinished:
        assert (stage.primal, stage.dual, stage.absolute_gap, stage.relative_gap) == (None, None, None, None), stage
    _revalidate(result)


# --------------------------------------------------------------------------
# Item 7 — ready_infeasible is SCIP's verdict on the first, still-global stage:
# infeasibility_proven from solver_status, and a completed stop.
# --------------------------------------------------------------------------
def _forced_min_scenario_view():
    request = _validated(_forced_min_payload())
    outcome = normalize_pac_plan(request)
    assert outcome.ready, "forced-min request must normalize; infeasibility is a search result"
    scenario = outcome.normalized
    return scenario, build_exact_policy_view(scenario, purpose="primary")


def test_ready_infeasible_result_type_pins_completed_and_infeasibility_proof():
    """The wire contract itself forbids any other shape for ``ready_infeasible``.

    Its stop is ``completed`` — an infeasible verdict ends the search, it is not
    a limit — its proof is an ``InfeasibilityProvenProof``, and that proof has a
    single source: SCIP's own status.
    """
    fields = PacPlannerReadyInfeasibleResult.model_fields
    assert get_args(fields["stop_reason"].annotation) == ("completed",)
    assert fields["proof"].annotation is InfeasibilityProvenProof
    proof_source = InfeasibilityProvenProof.model_fields["proof_source"].annotation
    assert set(get_args(proof_source)) == {"solver_status"}


def test_forced_infeasible_returns_ready_infeasible_not_raise():
    """A provably-infeasible plan RETURNS ``ready_infeasible``, proven by SCIP's own status.

    The input — ``required_minimum`` of one whole unit, €5 of cash against a
    €10 unit price — cannot be satisfied at all, so SCIP reports the first,
    still-global stage ``infeasible``. Under D-X1 that status *is* the proof:
    ``infeasibility_proven`` from ``solver_status``, whose witness names exactly
    that first objective, and ``stop_reason="completed"`` because the search
    ended on a verdict, not on a limit. The evidence reports what the solver
    actually did — one stage, ``infeasible``, global, with no primal, no dual
    and no gap, because an infeasible solve has none — and nothing about the
    later stages, which never had a face to run on.

    Regression origin, kept as this test's intent: this ordinary infeasible
    input once made ``plan_pac_allocation`` *raise* a ``ValidationError``
    (``completed`` against unfinished stage evidence) instead of returning a
    result, breaking its own "never raises on a planning outcome" contract. It
    must come back as a result, and that result must survive the wire union.
    """
    _scenario, view = _forced_min_scenario_view()
    first_objective_code = next(ref.code for ref in view.objectives if ref.ordinal == 1)

    result = plan_pac_allocation(_validated(_forced_min_payload()))
    assert isinstance(result, PacPlannerReadyInfeasibleResult)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(result, mode="json", by_alias=True)

    assert (wire["result_state"], wire["outcome"], wire["stop_reason"]) == ("ready_infeasible", "infeasible_proven", "completed")
    assert wire["proof"] == {
        "kind": "infeasibility_proven",
        "proof_source": "solver_status",
        "witness": {"kind": "solver_status", "objective_codes": [first_objective_code]},
    }

    evidence = wire["solver_evidence"]
    assert evidence["kind"] == "reported_floating"
    # Exactly the stage that ran: no "not_reached" rows appended after it.
    assert len(evidence["stages"]) == 1, evidence["stages"]
    (stage,) = evidence["stages"]
    assert (stage["objective_code"], stage["ordinal"], stage["scope"], stage["status"]) == (first_objective_code, 1, "global", "infeasible")
    assert (stage["primal"], stage["dual"], stage["absolute_gap"], stage["relative_gap"]) == (None, None, None, None)
    _revalidate(result)  # the real gate: revalidate through the wire union


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

    SCIP runs on every ready result, so the evidence is always
    ``ReportedFloatingSolverEvidence`` with ≥1 stage (min_length=1) and no
    ``tie:*`` leakage — the wire ObjectiveCode enum cannot express those stages.
    """
    evidence = ready_result.solver_evidence
    assert isinstance(evidence, ReportedFloatingSolverEvidence)
    assert len(evidence.stages) >= 1
    assert all(not stage.objective_code.startswith("tie") for stage in evidence.stages)
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
# Item 11 — the solver evidence and the stop/evidence invariant. SCIP is the
# only route, so every ready result carries reported_floating evidence, and a
# completed stop means no stage was left unfinished.
# --------------------------------------------------------------------------
def test_solver_route_carries_reported_floating_evidence(ready_result):
    """Every ready result reports the SCIP stages it ran, and proves only by them.

    ``completed`` ⇔ no stage unfinished is the biconditional
    ``_validate_stop_evidence`` enforces; asserted here as a property of the
    live results, so a routing regression fails at the planner rather than deep
    in the wire validator. Both fixtures are small and SCIP closes every stage
    optimal on them: every stage is ``finished``, and the proof is
    ``optimal_proven`` from ``solver_status``, whose witness names the published
    objective stages in order — the same codes, in the same order, as the
    evidence.
    """
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(ready_result, mode="json", by_alias=True)
    evidence = wire["solver_evidence"]
    assert evidence["kind"] == "reported_floating"
    stages = evidence["stages"]
    assert len(stages) >= 1
    unfinished = any(stage["status"] == "unfinished" for stage in stages)
    assert (wire["stop_reason"] == "completed") == (not unfinished)

    assert {stage["status"] for stage in stages} == {"finished"}, stages
    published_codes = [stage["objective_code"] for stage in wire["primary_solution"]["objectives"]["stages"]]
    assert [stage["objective_code"] for stage in sorted(stages, key=lambda stage: stage["ordinal"])] == published_codes
    assert wire["proof"] == {
        "kind": "optimal_proven",
        "proof_source": "solver_status",
        "witness": {"kind": "solver_status", "objective_codes": published_codes},
        "tie_break_closed": True,
    }
    _revalidate(ready_result)


# --------------------------------------------------------------------------
# C0b.1 — currency quanta come from babel, never from the request; C0b.3 — an
# exposure total above one is an invalid *result*. Both end to end through the
# service (the normalizer-level cases live in test_pac_planner_normalize.py).
# --------------------------------------------------------------------------
def _exposure_total_above_one_payload() -> dict:
    """The fixture Asset with its sector exposure split 0.7 + 0.5 = 1.2."""
    payload = _pac_request()
    asset = next(row for row in payload["assets"] if row["asset_id"] == "asset-one")
    sector = next(row for row in asset["exposures"] if row["dimension"] == "sector")
    sector["weight"] = "0.7"
    asset["exposures"].append({**copy.deepcopy(sector), "category_id": "tech", "label": "Tech", "weight": "0.5"})
    return payload


def test_exposure_total_above_one_is_an_invalid_result_not_a_failure():
    result = plan_pac_allocation(_validated(_exposure_total_above_one_payload()))

    assert isinstance(result, PacPlannerInvalidResult)
    assert (result.result_state, result.availability) == ("invalid", "invalid")
    assert [issue.model_dump(mode="json") for issue in result.issues] == [
        {
            "code": "allocation.exposure_total_exceeds_one",
            "severity": "error",
            "kind": "invalid",
            "path": {"kind": "field", "section": "assets", "entity_kind": "asset", "entity_id": "asset-one", "field": "exposures.weight"},
            "message_key": "allocation.exposure_total_exceeds_one",
            "params": [{"kind": "text", "name": "dimension", "value": "sector"}],
        }
    ]
    _revalidate(result)


def test_manual_only_scenario_plans_without_any_currency_input(noop_result, incumbent_result):
    """No copy and no currency table: the quantum is derived, so both ready paths run."""
    payload = _pac_request()
    assert "currency_specs" not in payload
    assert {record["kind"] for record in payload["provenance"]} == {"manual"}

    for result, state in ((noop_result, "ready_no_op"), (incumbent_result, "ready_incumbent")):
        assert result.result_state == state
        assert result.proof.kind == "optimal_proven"
        assert result.model_dump(mode="json")["catalogs"]["currencies"] == [{"currency": "EUR", "minor_unit": "0.01"}]


def test_currency_catalog_publishes_the_babel_quantum_of_every_referenced_currency():
    payload = _incumbent_payload()
    # Rates only reference JPY and KWD: enough to put them in the scenario.
    payload["fx_rates"] = {"EUR/JPY": "160", "EUR/KWD": "0.33"}

    result = plan_pac_allocation(_validated(payload))

    assert isinstance(result, PacPlannerReadyIncumbentResult)
    assert result.proof.kind == "optimal_proven"
    # Sorted by code; zero, two and three CLDR digits respectively.
    assert result.model_dump(mode="json")["catalogs"]["currencies"] == [
        {"currency": "EUR", "minor_unit": "0.01"},
        {"currency": "JPY", "minor_unit": "1"},
        {"currency": "KWD", "minor_unit": "0.001"},
    ]
    _revalidate(result)


# --------------------------------------------------------------------------
# D-X1 — SCIP is the only production search engine and its own status is the
# proof; the exhaustive oracle is a test instrument. Asserted on the dumped
# wire JSON, so the module imports whatever the schema's Python types say.
# --------------------------------------------------------------------------

# Far above a SCIP plan of the X1 scenario (~189 polls measured 2026-09-28),
# far below any enumeration of it (the oracle polls ~89-96 times per candidate).
_ENUMERATION_CHECKPOINT_BUDGET = 2_000

# The engine window the Tool claims for a plan (``engine_timeout_ms=30_000`` in
# ``tool_plugins/pac_allocator.py``), so the X1 scenario is planned exactly as
# production plans it. A budget handed to SCIP, never an assertion: the test
# itself neither reads nor asserts on the clock.
_TOOL_ENGINE_WINDOW_SECONDS = 30.0

# Decision modes whose value the view fixes: they span one point, not a range.
_SINGLE_POINT_DECISION_MODES = frozenset({"disabled", "frozen_exact"})


class _CheckpointBudgetExceeded(Exception):
    """Raised by ``_CountingCheckpoint`` when the planner polls past its budget."""


class _CountingCheckpoint:
    """A ``Checkpoint`` that counts its polls and trips once they pass a budget.

    Every production engine polls the cooperative checkpoint inside its loops —
    that is the cancellation contract — so the poll count measures how much
    search work a plan did without ever reading a clock.
    """

    def __init__(self, budget: int) -> None:
        self.budget = budget
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1
        if self.calls > self.budget:
            raise _CheckpointBudgetExceeded(f"checkpoint polled {self.calls} times, past the budget of {self.budget}: a SCIP plan of this scenario polls it a few hundred times at most, so the production planner is enumerating the candidate domain (defect X1)")


def _candidate_domain_size(view) -> int:
    """How many candidates a brute-force search of ``view`` would have to visit.

    Read off the view's own decision boxes (a fixed decision spans one point),
    not off the oracle module this batch evicts from production.
    """
    return math.prod(1 if access.mode in _SINGLE_POINT_DECISION_MODES else access.upper_quanta - access.lower_quanta + 1 for access in view.decisions)


def _order_summary(row: dict) -> tuple:
    instruction = row["instruction"]
    quantity = instruction.get("quantity")
    return row["kind"], instruction["kind"], None if quantity is None else Fraction(quantity), instruction.get("unit")


def test_x1_planner_does_not_enumerate_a_large_domain():
    """X1, deterministically: the production planner never enumerates the domain.

    The X1 shape — pure PAC, a €100 contribution, two ETFs at €40/€60 — has a
    domain of 60 006 candidates (two BUY decisions plus a funding transfer
    counted in cents). Enumerating it is what blew the soft deadline (defect
    X1); D-X1 cures it by making SCIP the only production search engine.

    "Does not enumerate" is proven by counting ``Checkpoint`` polls, never by
    the clock. Measured 2026-09-28 on this scenario: SCIP polls once per
    cascade stage (8 here), the exact replay ~178 times, the whole SCIP path
    ~189; the exhaustive oracle ~89-96 times *per candidate*, ≈5.7 million
    here. The budget sits an order of magnitude above the first figure and
    three below the second — and since the domain alone exceeds it, even an
    enumerator polling once per candidate would trip it. That precondition is
    verified, not assumed: a smaller scenario would let this test pass on a
    planner that still enumerates.

    Then the published result, as D-X1 defines it: SCIP optimal on every stage
    ⇒ ``optimal_proven`` from ``solver_status``, whose witness names the
    published objective stages in order; ``completed``; ``reported_floating``
    evidence with every stage finished; and the exact optimum — one whole unit
    of each ETF, rows found by Asset and route, never by position.
    """
    request = _validated(_two_etf_contribution_payload())
    normalized = normalize_pac_plan(request)
    assert normalized.ready, [issue.code for issue in normalized.issues]
    domain_size = _candidate_domain_size(build_exact_policy_view(normalized.normalized, purpose="primary"))
    assert domain_size > _ENUMERATION_CHECKPOINT_BUDGET, f"the X1 scenario must be too large to enumerate within the budget: {domain_size} candidates vs {_ENUMERATION_CHECKPOINT_BUDGET} polls"

    checkpoint = _CountingCheckpoint(budget=_ENUMERATION_CHECKPOINT_BUDGET)
    result = plan_pac_allocation(request, checkpoint=checkpoint, solver_time_budget_seconds=_TOOL_ENGINE_WINDOW_SECONDS)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(result, mode="json", by_alias=True)

    assert (wire["result_state"], wire["outcome"], wire["stop_reason"]) == ("ready_incumbent", "incumbent_found", "completed")
    published_codes = [stage["objective_code"] for stage in wire["primary_solution"]["objectives"]["stages"]]
    assert wire["proof"] == {
        "kind": "optimal_proven",
        "proof_source": "solver_status",
        "witness": {"kind": "solver_status", "objective_codes": published_codes},
        "tie_break_closed": True,
    }

    evidence = wire["solver_evidence"]
    assert evidence["kind"] == "reported_floating"
    assert evidence["stages"], "reported_floating evidence must carry the stages SCIP ran"
    assert {stage["status"] for stage in evidence["stages"]} == {"finished"}, evidence["stages"]

    order_rows = wire["primary_solution"]["order_rows"]
    bought = {(row["asset_id"], row["route_id"]): _order_summary(row) for row in order_rows}
    assert len(bought) == len(order_rows), f"more than one order row on one route: {order_rows}"
    one_whole_unit = ("buy", "whole_quantity", Fraction(1), "asset_unit")
    assert bought == {(_ASSET_ONE_ID, _ASSET_ONE_ROUTE_ID): one_whole_unit, (_ASSET_TWO_ID, _ASSET_TWO_ROUTE_ID): one_whole_unit}

    assert checkpoint.calls <= _ENUMERATION_CHECKPOINT_BUDGET


_ORACLE_MODULE = "backend.app.services.pac_allocator.oracle"
_TEST_TREE_PACKAGE = "backend.test_scripts"
_PRODUCTION_ROOT = REPO_ROOT / "backend" / "app"

# Every import shape the scan must reject, with the module it resolves to from
# inside ``backend.app.services.pac_allocator``: the presence barrier for the
# absence the structural test asserts.
_TEST_ONLY_IMPORT_SHAPES = (
    ("import backend.test_scripts.test_utils", "backend.test_scripts.test_utils"),
    ("from backend.app.services.pac_allocator.oracle import OracleResult", _ORACLE_MODULE),
    ("from backend.app.services.pac_allocator import oracle", _ORACLE_MODULE),
    ("from .oracle import run_exhaustive_oracle", _ORACLE_MODULE),
    ("from . import oracle as exhaustive", _ORACLE_MODULE),
    ("from ....test_scripts import test_utils", _TEST_TREE_PACKAGE),
)


def _is_test_only(module: str) -> bool:
    return any(module == root or module.startswith(f"{root}.") for root in (_ORACLE_MODULE, _TEST_TREE_PACKAGE))


def _test_only_imports(source: str, package: str) -> list[tuple[int, str]]:
    """``(line, module)`` for every import in ``source`` that binds test-only code.

    ``import a.b`` binds ``a.b``; ``from a import b`` binds ``a`` and may bind the
    submodule ``a.b`` — ``from ...pac_allocator import oracle`` is exactly that
    shape. Relative forms resolve against ``package``, as the interpreter does.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names if _is_test_only(alias.name))
        elif isinstance(node, ast.ImportFrom):
            base = importlib.util.resolve_name("." * node.level + (node.module or ""), package)
            if _is_test_only(base):
                found.append((node.lineno, base))
            else:
                found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names if _is_test_only(f"{base}.{alias.name}"))
    return sorted(found)


def _scan_production_imports() -> tuple[list[str], list[str]]:
    """Scan every ``backend/app/**/*.py``; return (scanned files, offending imports)."""
    scanned: list[str] = []
    offenders: list[str] = []
    for path in sorted(_PRODUCTION_ROOT.rglob("*.py")):
        relative = path.relative_to(REPO_ROOT)
        # A module's package is its directory; so is an ``__init__``'s.
        package = ".".join(relative.with_suffix("").parts[:-1])
        scanned.append(relative.as_posix())
        offenders.extend(f"{relative.as_posix()}:{line} imports {module}" for line, module in _test_only_imports(path.read_text(encoding="utf-8"), package))
    return scanned, offenders


def test_exhaustive_oracle_is_test_only():
    """D-X1: the exhaustive oracle is a test instrument, never a production engine.

    It moves into the test tree, where it remains the independent cross-check
    of SCIP and the Decimal evaluator. Production must not be able to reach it,
    nor anything else under ``backend.test_scripts``: the old module path no
    longer resolves, and no module under ``backend/app`` imports either, by any
    absolute or relative form.

    Two presence barriers keep that absence honest: the detector must flag
    every import shape it exists to reject, and the scan must actually have
    walked ``planner.py`` — a scan that looked at nothing would find nothing too.
    """
    for statement, module in _TEST_ONLY_IMPORT_SHAPES:
        assert _test_only_imports(statement, "backend.app.services.pac_allocator") == [(1, module)], statement

    scanned, offenders = _scan_production_imports()
    assert "backend/app/services/pac_allocator/planner.py" in scanned, f"the scan did not reach the planner: {len(scanned)} files under {_PRODUCTION_ROOT}"

    violations = list(offenders)
    spec = importlib.util.find_spec(_ORACLE_MODULE)
    if spec is not None:
        # A leftover ``oracle/`` directory resolves as a namespace package, whose spec has no origin.
        where = os.path.relpath(spec.origin, REPO_ROOT) if spec.origin else f"a namespace package in {list(spec.submodule_search_locations or ())}"
        violations.insert(0, f"{_ORACLE_MODULE} still resolves, to {where}")
    assert not violations, "the exhaustive oracle must be test-only (D-X1), and backend/app must import neither it nor backend.test_scripts:\n" + "\n".join(violations)
