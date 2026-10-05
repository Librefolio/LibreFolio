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
is unconditional and its verdict is authoritative: SCIP is never trusted to
report its own result. A plan whose only violation is a rounding deficit
within N minor units per cash pool (N = the pool's postings that carry a
quantum) is published with its top-ups — one per negative pool, "this
broker/currency needs D more" (test_rounding_tie_*). Any other rejection
raises ``ExactReplayRejectedError``, which the Tool reports as
``execution_failed``; it is never ``ready_no_incumbent``
(test_replay_rejection_*). The locked properties, each mapped to a test:

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
* **A Broker's conversion mode changes no figure** (R4.9): the same FX plan,
  planned with manual and with automatic conversions, publishes the same
  orders, ledger, costs and objectives; only the conversion's mode and step
  number differ, and an automatic conversion takes no step, so the orders
  follow the funding directly (test_conversion_mode_*).
* **How a request is written changes no figure** (contract compaction, plan
  §1/§3): omitting every default publishes the identical result, fingerprint
  included (test_omitting_the_defaults_*); the compact twin with no fee schedule
  buys what ``min`` buys (test_compact_twin_*); a rate-only schedule charges
  like its explicit EUR twin (test_rate_only_*). The last two may differ only in
  ``request_fingerprint``, by design.

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
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
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
from backend.app.services.pac_allocator import evaluator as EV
from backend.app.services.pac_allocator import planner
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate, exact_decision_id
from backend.app.services.pac_allocator.normalize import normalize_pac_plan
from backend.app.services.pac_allocator.planner import plan_pac_allocation
from backend.test_scripts.test_schemas.test_pac_planner_schemas import _compact_pac_request, _fixture, _pac_request

# The repository root: parents = [test_services, test_scripts, backend, <root>].
REPO_ROOT = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------
# Request builders — a fresh dict every call (``_pac_request`` re-reads JSON),
# deepcopy + targeted edits, validated through the real input adapter.
# --------------------------------------------------------------------------
def _validated(payload: dict):
    return PAC_PLAN_INPUT_ADAPTER.validate_python(payload)


def _revalidate(result):
    """The real gate: dump to python and re-validate against the wire union."""
    return PAC_PLAN_OUTPUT_ADAPTER.validate_python(result.model_dump(mode="python"))


def _incumbent_payload(payload: dict | None = None) -> dict:
    """The no-op fixture (or ``payload``), but with enough cash (€50) to buy whole units.

    €50 against a €10 whole-unit price buys 5 units, so the proven optimum stops
    being "do nothing" and becomes a single BUY.
    """
    payload = _pac_request() if payload is None else payload
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
    assert solution.conversions == []
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
# Item 5 — the replay's verdict is authoritative (commit 5, QX1-b): a plan whose
# only violation is a rounding deficit within N minor units per cash pool is
# published with its top-ups; any other rejection raises
# ExactReplayRejectedError, never ready_no_incumbent. Asserted on the published
# wire result, never on the planner's internal path.
# --------------------------------------------------------------------------
_BROKER_ONE_ID = "broker-one"

# The conflict codes a pure rounding deficit leaves behind; any other is a rejection.
_TOP_UP_TOLERATED_CODES = frozenset({"FX_SOURCE_CASH", "NO_SHORT_OR_LEVERAGE", "ROUNDING_BOUND", "SPENDABLE_CASH_NONNEGATIVE"})

# currency -> (tie price, cash, cash plus one minor unit). Three whole units at
# the tie price cost exactly half a minor unit more than the cash, which the
# HALF_UP replay posts as one whole minor unit more.
_ROUNDING_TIES = {
    "BHD": ("33.3335", "100.000", "100.001"),
    "EUR": ("33.335", "100.00", "100.01"),
    "JPY": ("333.5", "1000", "1001"),
}


def _tie_payload(currency: str, price: str, cash: str) -> dict:
    """The min fixture moved to ``currency``: a zero-fee whole-unit Asset at ``price``, ``cash`` on broker-one."""
    payload = _pac_request()
    payload["valuation_currency"] = currency
    asset = next(row for row in payload["assets"] if row["asset_id"] == _ASSET_ONE_ID)
    asset["quote"]["amount"] = price
    asset["quote"]["currency"] = currency
    broker = next(row for row in payload["brokers"] if row["broker_id"] == _BROKER_ONE_ID)
    for fee in broker["fee_schedules"]:
        fee["fixed_fee"]["currency"] = currency
        fee["variable_floor"]["currency"] = currency
        fee["variable_cap"]["amount"]["currency"] = currency
        fee["rate"] = "0"
    for row in payload["existing_cash"]:
        row["available"] = {"amount": cash, "currency": currency}
        row["selected"] = {"amount": cash, "currency": currency}
    return payload


def _plan_wire(payload: dict) -> dict:
    """Plan ``payload`` in the Tool's engine window, revalidate it, return the dumped wire result."""
    result = plan_pac_allocation(_validated(payload), solver_time_budget_seconds=_TOOL_ENGINE_WINDOW_SECONDS)
    _revalidate(result)
    return PAC_PLAN_OUTPUT_ADAPTER.dump_python(result, mode="json", by_alias=True)


def _published_minor_unit(wire: dict, currency: str) -> Decimal:
    (row,) = [row for row in wire["catalogs"]["currencies"] if row["currency"] == currency]
    return Decimal(row["minor_unit"])


def _assert_three_units_bought(wire: dict) -> None:
    order_rows = wire["primary_solution"]["order_rows"]
    bought = {(row["asset_id"], row["route_id"]): _order_summary(row) for row in order_rows}
    assert len(bought) == len(order_rows), f"more than one order row on one route: {order_rows}"
    assert bought == {(_ASSET_ONE_ID, _ASSET_ONE_ROUTE_ID): ("buy", "whole_quantity", Fraction(3), "asset_unit")}


def _broker_one_final_cash(wire: dict, currency: str) -> tuple[Decimal, Decimal]:
    (row,) = [row for row in wire["primary_solution"]["ledger_rows"] if (row["broker_id"], row["currency"]) == (_BROKER_ONE_ID, currency)]
    return Decimal(row["final_spendable"]), Decimal(row["final_physical"])


@pytest.mark.parametrize("currency", sorted(_ROUNDING_TIES))
def test_rounding_tie_is_published_with_its_top_up(currency):
    """A HALF_UP tie is a published, proven plan with one top-up of one minor unit.

    SCIP closes every stage with 3 units; the Decimal replay posts their cost one
    minor unit above the cash, so broker-one ends one minor unit short. The
    pool's only quantum-carrying posting is the buy debit (the initial cash has
    none, a zero fee is not posted): N = 1 and D = one minor unit, within the
    rule. The result is ``ready_incumbent`` / ``optimal_proven``; its one top-up
    names the pool, the missing minor unit (read from the published currency
    catalogue, never hard-coded), its one rounded posting and its valuation in
    the valuation currency; the ledger shows the pool at minus one minor unit.
    Before commit 5 the same plan was suppressed as ``ready_no_incumbent``.
    """
    price, cash, _ = _ROUNDING_TIES[currency]
    wire = _plan_wire(_tie_payload(currency, price, cash))
    minor = _published_minor_unit(wire, currency)
    assert 3 * Decimal(price) - Decimal(cash) == minor / 2, "the scenario must be a tie: exactly half a minor unit over the cash"

    assert (wire["result_state"], wire["outcome"], wire["stop_reason"]) == ("ready_incumbent", "incumbent_found", "completed")
    assert wire["proof"]["kind"] == "optimal_proven"
    _assert_three_units_bought(wire)
    assert _broker_one_final_cash(wire, currency) == (-minor, -minor)

    top_ups = wire["primary_solution"]["rounding_top_ups"]
    assert [(row["broker_id"], row["currency"]) for row in top_ups] == [(_BROKER_ONE_ID, currency)]
    (top_up,) = top_ups
    assert Decimal(top_up["amount"]) == minor
    assert top_up["rounded_postings"] == 1
    valuation = top_up["valuation_amount"]
    assert (valuation["currency"], valuation["value"]["kind"]) == (currency, "finite_decimal")
    assert Decimal(valuation["value"]["value"]) == minor


@pytest.mark.parametrize("currency", sorted(_ROUNDING_TIES))
def test_rounding_tie_with_one_more_minor_unit_needs_no_top_up(currency):
    """The counterfactual: one more minor unit of cash buys the same plan, with no top-up.

    Proves the announced top-up is exactly enough: the same 3 units, the pool
    back at zero, and ``rounding_top_ups`` published and empty.
    """
    price, cash, one_more = _ROUNDING_TIES[currency]
    wire = _plan_wire(_tie_payload(currency, price, one_more))

    assert (wire["result_state"], wire["outcome"], wire["stop_reason"]) == ("ready_incumbent", "incumbent_found", "completed")
    assert wire["proof"]["kind"] == "optimal_proven"
    _assert_three_units_bought(wire)
    assert Decimal(one_more) - Decimal(cash) == _published_minor_unit(wire, currency)
    assert _broker_one_final_cash(wire, currency) == (0, 0)

    assert "rounding_top_ups" in wire["primary_solution"], sorted(wire["primary_solution"])
    assert wire["primary_solution"]["rounding_top_ups"] == []


def _threshold_breach_payload() -> dict:
    """The EUR tie with a EUR 1 fixed fee: SCIP buys 2 units; a third leaves the pool EUR 1.01 short."""
    price, cash, _ = _ROUNDING_TIES["EUR"]
    payload = _tie_payload("EUR", price, cash)
    broker = next(row for row in payload["brokers"] if row["broker_id"] == _BROKER_ONE_ID)
    for fee in broker["fee_schedules"]:
        fee["fixed_fee"]["amount"] = "1"
    return payload


def test_replay_rejection_beyond_the_rounding_threshold_raises(monkeypatch):
    """A candidate short by more than N minor units raises; it never becomes ``ready_no_incumbent``.

    Replaces ``test_replay_failure_suppresses_the_plan``, obsolete by design: it
    pinned the behaviour the developer reversed on 25/09 (a replay rejection
    answered ``ready_no_incumbent`` + ``completed``). Not a flake, not a defect.

    Seam: ``planner.solve_policy_program`` runs the real SCIP and hands the
    replay the same candidate (same view and candidate ids) with one more buy
    quantum; the replay and the classifier stay real. The zero-fee tie cannot
    host it: its view bounds the route at 3 units, so a 4th would be out of
    bounds (a contract failure, not a threshold breach). With a EUR 1 fixed fee
    SCIP buys 2 units, and the tampered 3rd ends broker-one EUR 1.01 short over
    two rounded postings (buy debit and fee). The candidate is also replayed
    directly, to prove that the cash rules are the only ones it breaks and that
    D > N x minor unit: the raise is attributable to the threshold alone.
    """
    real_solve = planner.solve_policy_program
    buy_id = exact_decision_id("buy_quantum", _ASSET_ONE_ROUTE_ID)
    tampered = []

    def solve_one_quantum_too_many(*args, **kwargs):
        run = real_solve(*args, **kwargs)
        assert run.candidate is not None, "SCIP must hold a candidate for the seam to tamper with"
        candidate = replace(run.candidate, decisions=tuple(replace(item, quanta=item.quanta + 1) if item.decision_id == buy_id else item for item in run.candidate.decisions))
        tampered.append(candidate)
        return replace(run, candidate=candidate)

    monkeypatch.setattr(planner, "solve_policy_program", solve_one_quantum_too_many)
    request = _validated(_threshold_breach_payload())
    try:
        outcome = plan_pac_allocation(request, solver_time_budget_seconds=_TOOL_ENGINE_WINDOW_SECONDS)
    except ValueError as error:  # ExactReplayRejectedError is an ExactEvaluatorError, a ValueError
        outcome = error

    assert len(tampered) == 1, "the planner must run SCIP exactly once and replay its candidate"
    (candidate,) = tampered
    assert {item.decision_id: item.quanta for item in candidate.decisions}[buy_id] == 3, "SCIP's own plan is 2 units"

    scenario = normalize_pac_plan(request).normalized
    evaluation = evaluate_exact_candidate(scenario, build_exact_policy_view(scenario, purpose="primary"), candidate)
    assert evaluation.candidate_valid is True
    assert "SPENDABLE_CASH_NONNEGATIVE" in evaluation.conflict_codes
    assert set(evaluation.conflict_codes) <= _TOP_UP_TOLERATED_CODES, evaluation.conflict_codes
    (ledger,) = [row for row in evaluation.ledgers if (row.broker_id, row.currency) == (_BROKER_ONE_ID, "EUR")]
    rounded_postings = sum(1 for posting in evaluation.postings if (posting.broker_id, posting.currency) == (_BROKER_ONE_ID, "EUR") and posting.quantum is not None)
    (spec,) = [row for row in scenario.currency_specs if row.currency == "EUR"]
    assert (rounded_postings, -ledger.final_spendable) == (2, spec.minor_unit * 101)
    assert -ledger.final_spendable > rounded_postings * spec.minor_unit

    assert not isinstance(outcome, PacPlannerReadyNoIncumbentResult), f"a replay rejection must raise ExactReplayRejectedError, not answer {outcome.result_state} / {outcome.stop_reason}"
    assert isinstance(outcome, EV.ExactReplayRejectedError), repr(outcome)


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
def _numbered_sections(solution) -> tuple[list, list, list]:
    """The action sections a user executes in order: funding, manual conversions, orders.

    An FX action is the engine's per-route decision, not a step; an automatic
    conversion happens inside the orders, so it carries no sequence either.
    """
    return list(solution.funding_actions), [row for row in solution.conversions if row.sequence is not None], list(solution.order_rows)


def _action_sequences(solution) -> list[int]:
    return [row.sequence for section in _numbered_sections(solution) for row in section]


def _referenced_provenance(solution) -> set[str]:
    rows = (*solution.funding_actions, *solution.fx_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows)
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
    assert len(sequences) == len(set(sequences))  # globally unique across funding/manual conversions/orders
    for section in _numbered_sections(solution):
        section_sequences = [row.sequence for row in section]
        assert section_sequences == sorted(section_sequences)  # each section internally ascending

    published = {provenance.provenance_id for provenance in ready_result.provenance}
    assert _referenced_provenance(solution) <= published


# --------------------------------------------------------------------------
# R4.9 — a Broker's conversion mode is presentation only. The same FX plan,
# planned once with manual and once with automatic conversions, differs only in
# the mode and step number of its conversion — and, since an automatic
# conversion is not a step the user performs, in where the order numbering
# starts.
# --------------------------------------------------------------------------
_FX_CONTRIBUTION_ID = "contribution-one"
_FX_FUNDING_ROUTE_ID = "funding-contribution-one-broker-one"
_CONVERSION_MODES = ("manual", "automatic")


def _fx_contribution_payload(conversion_mode: str) -> dict:
    """A EUR contribution buying a USD-quoted Asset at broker-one: the plan must convert.

    The min fixture's Asset is quoted in USD (its zero fee schedule moves with
    it), the Broker holds no cash, and one €50 contribution can reach it in EUR
    only. A 1.25 EUR/USD rate with a 4% spread makes the conversion cost
    something, so equal figures across modes are not trivially equal zeros.
    The spread is chosen, not incidental: the effective rate 1.25 × 0.96 = 6/5
    has an odd denominator, so no EUR→USD credit lands on a HALF_UP tie of the
    USD cent. Ties are no longer refused (option A removed the compiler's
    credit-tie guard) and
    ``test_manual_conversion_reaching_an_exact_credit_tie_still_plans`` plans
    one, but this fixture keeps the conversion-mode tests free of them.
    """
    payload = _pac_request()
    asset = next(row for row in payload["assets"] if row["asset_id"] == _ASSET_ONE_ID)
    asset["quote"]["currency"] = "USD"
    broker = next(row for row in payload["brokers"] if row["broker_id"] == _BROKER_ONE_ID)
    broker["conversion_mode"] = conversion_mode
    for fee in broker["fee_schedules"]:
        fee["fixed_fee"]["currency"] = "USD"
        fee["variable_floor"]["currency"] = "USD"
        fee["variable_cap"]["amount"]["currency"] = "USD"
    payload["fx_rates"] = {"EUR/USD": "1.25"}
    payload["fx_spread_rate"] = "0.04"
    payload["existing_cash"] = []
    payload["contributions"] = [{"contribution_id": _FX_CONTRIBUTION_ID, "label": "Monthly", "amount": {"amount": "50.00", "currency": "EUR"}, "provenance_id": "prov-manual"}]
    payload["funding_routes"] = [
        {
            "funding_route_id": _FX_FUNDING_ROUTE_ID,
            "source": {"kind": "contribution", "contribution_id": _FX_CONTRIBUTION_ID},
            "broker_id": _BROKER_ONE_ID,
            "currency": "EUR",
            "priority": 1,
            "transfer_cap": {"amount": "50.00", "currency": "EUR"},
            "provenance_id": "prov-manual",
        }
    ]
    return payload


@pytest.fixture(scope="module")
def fx_plan_by_mode() -> dict[str, dict]:
    """The FX scenario planned once per conversion mode, as dumped wire results."""
    return {mode: _plan_wire(_fx_contribution_payload(mode)) for mode in _CONVERSION_MODES}


def _without_numbering(solution: dict) -> dict:
    """The solution's figures: every step number and every conversion mode removed."""
    figures = copy.deepcopy(solution)
    for section in ("funding_actions", "conversions", "order_rows"):
        for row in figures[section]:
            row.pop("sequence")
    for row in figures["conversions"]:
        row.pop("mode")
    return figures


def _wire_exact(number: dict) -> Fraction:
    """An ``ExactNumber`` read off the wire, exactly: either branch of the union."""
    if number["kind"] == "finite_decimal":
        return Fraction(Decimal(number["value"]))
    return Fraction(int(number["numerator"]), int(number["denominator"]))


def test_conversion_mode_changes_no_figure_of_the_plan(fx_plan_by_mode):
    """Manual and automatic conversions publish the same plan, figure for figure.

    Both runs are proven optima on the same compiled model — the engine never
    reads the mode — so orders, FX actions, ledger, costs, accounting and
    objectives must agree exactly. The conversion row agrees too, once its mode
    and step number are set aside; nothing else may differ.
    """
    for mode, wire in fx_plan_by_mode.items():
        assert (wire["result_state"], wire["proof"]["kind"]) == ("ready_incumbent", "optimal_proven"), mode
        solution = wire["primary_solution"]
        assert solution["funding_actions"] and solution["fx_actions"] and solution["order_rows"], f"{mode}: the scenario must fund, convert and buy"
        assert [row["mode"] for row in solution["conversions"]] == [mode], solution["conversions"]

    manual, automatic = fx_plan_by_mode["manual"], fx_plan_by_mode["automatic"]
    assert manual["primary_solution"]["fx_actions"] == automatic["primary_solution"]["fx_actions"]
    assert _without_numbering(manual["primary_solution"]) == _without_numbering(automatic["primary_solution"])
    assert manual["scenario_basis"] == automatic["scenario_basis"]


def test_conversion_mode_conversion_aggregates_the_fx_actions(fx_plan_by_mode):
    """The published conversion is the EUR→USD one at broker-one, built from every FX action.

    Its debit and spread are the exact sums of the actions', its credit the sum
    of their posted credits, and each action names it — read off the live
    result, in either mode.
    """
    for mode, wire in fx_plan_by_mode.items():
        solution = wire["primary_solution"]
        (conversion,) = solution["conversions"]
        assert conversion["conversion_id"] == f"conversion:{_BROKER_ONE_ID}:EUR:USD", mode
        assert (conversion["broker_id"], conversion["source_debit"]["currency"], conversion["destination_credit"]["currency"]) == (_BROKER_ONE_ID, "EUR", "USD")
        actions = solution["fx_actions"]
        assert conversion["fx_action_ids"] == [action["action_id"] for action in actions]
        assert {action["conversion_id"] for action in actions} == {conversion["conversion_id"]}
        assert all("sequence" not in action for action in actions), actions
        assert Fraction(Decimal(conversion["source_debit"]["amount"])) == sum(Fraction(Decimal(action["source_debit"]["amount"])) for action in actions)
        assert Fraction(Decimal(conversion["destination_credit"]["amount"])) == sum(Fraction(Decimal(action["destination_credit"]["amount"])) for action in actions)
        assert _wire_exact(conversion["spread_loss"]["value"]) == sum(_wire_exact(action["spread_loss"]["value"]) for action in actions)
        assert _wire_exact(conversion["spread_loss"]["value"]) > 0, "a 4% spread must cost something"


@pytest.mark.parametrize("mode", _CONVERSION_MODES)
def test_conversion_mode_decides_whether_the_conversion_is_a_step(fx_plan_by_mode, mode):
    """Manual: the conversion is the step between funding and orders. Automatic: it is none.

    The steps a user performs are numbered 1..n in execution order — funding,
    manual conversions, orders — with no gap: an automatic conversion consumes
    no number, so the first order directly follows the last funding action.
    """
    solution = fx_plan_by_mode[mode]["primary_solution"]
    funding = [row["sequence"] for row in solution["funding_actions"]]
    conversions = [row["sequence"] for row in solution["conversions"]]
    orders = [row["sequence"] for row in solution["order_rows"]]

    assert funding == list(range(1, len(funding) + 1))
    if mode == "manual":
        assert conversions == list(range(len(funding) + 1, len(funding) + len(conversions) + 1))
        first_order = len(funding) + len(conversions) + 1
    else:
        assert conversions == [None] * len(conversions)
        first_order = len(funding) + 1
    assert orders == list(range(first_order, first_order + len(orders)))


# --------------------------------------------------------------------------
# R13 — option A: a conversion whose range reaches an exact HALF_UP credit tie
# plans like any other. The compiler's credit-tie guard is gone; the developer's
# EUR→USD case, rebuilt synthetically on the R4.9 FX fixture, is the regression.
# --------------------------------------------------------------------------
def test_manual_conversion_reaching_an_exact_credit_tie_still_plans():
    """1.1298 EUR/USD, no spread, a €30 contribution: a proven optimum, not ``execution_failed``.

    €25.00 converts to exactly 28.245 USD, half a USD cent: an exact HALF_UP
    credit tie inside the conversion's range (the EUR quantum is one cent and
    the FX decision's box reaches 2500 of them). Before option A the
    compiler's credit-tie guard raised ``LedgerPostingScopeError`` as soon as
    such a tie was reachable, published as ``execution_failed``, while €20
    (below the first tie, at €25) already planned. A posted credit enters the
    ledger only with a ``+`` sign, so the model's latitude at a tie cannot
    change what is feasible: the request must plan to a proven optimum, and
    every published credit must be the HALF_UP posting of its exact conversion.
    """
    payload = _fx_contribution_payload("manual")
    payload["fx_rates"] = {"EUR/USD": "1.1298"}
    payload["fx_spread_rate"] = "0"
    payload["contributions"][0]["amount"]["amount"] = "30.00"
    payload["funding_routes"][0]["transfer_cap"]["amount"] = "30.00"
    request = _validated(payload)

    # The precondition, verified rather than assumed: €25.00 is a whole number
    # of EUR quanta, converts to exactly half a USD quantum, and lies inside the
    # FX decision's box -- the tie is reachable in the compiled scenario.
    assert Decimal("25.00") * Decimal("1.1298") == Decimal("28.245")
    outcome = normalize_pac_plan(request)
    assert outcome.ready, [issue.code for issue in outcome.issues]
    scenario = outcome.normalized
    minor_unit = {spec.currency: Fraction(*spec.minor_unit.as_integer_ratio()) for spec in scenario.currency_specs}
    (rate,) = [Fraction(*row.rate.as_integer_ratio()) for row in scenario.fx_rates if (row.pair_first, row.pair_second) == ("EUR", "USD")]
    assert (rate, scenario.fx_spread_rate) == (Fraction(Decimal("1.1298")), 0)
    tie_quanta = Fraction(Decimal("25.00")) / minor_unit["EUR"]
    assert tie_quanta.denominator == 1
    assert (tie_quanta * minor_unit["EUR"] * rate / minor_unit["USD"]) % 1 == Fraction(1, 2)
    fx_decision_id = exact_decision_id("fx_debit", f"{_ASSET_ONE_ROUTE_ID}:EUR")
    (fx_access,) = [access for access in build_exact_policy_view(scenario, purpose="primary").decisions if access.decision_id == fx_decision_id]
    assert fx_access.mode == "mutable"
    assert fx_access.lower_quanta <= tie_quanta <= fx_access.upper_quanta

    result = plan_pac_allocation(request, solver_time_budget_seconds=_TOOL_ENGINE_WINDOW_SECONDS)
    assert result.availability == "ready"
    assert isinstance(result, PacPlannerReadyIncumbentResult)
    assert (result.result_state, result.proof.kind, result.stop_reason) == ("ready_incumbent", "optimal_proven", "completed")
    _revalidate(result)

    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(result, mode="json", by_alias=True)
    solution = wire["primary_solution"]
    assert solution["funding_actions"] and solution["fx_actions"] and solution["order_rows"], "the plan must fund, convert and buy"
    usd_minor_unit = _published_minor_unit(wire, "USD")
    for action in solution["fx_actions"]:
        debit, credit = action["source_debit"], action["destination_credit"]
        assert (debit["currency"], credit["currency"]) == ("EUR", "USD"), action
        assert Decimal(credit["amount"]) == (Decimal(debit["amount"]) * Decimal("1.1298")).quantize(usd_minor_unit, rounding=ROUND_HALF_UP), action


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


# --------------------------------------------------------------------------
# Contract compaction — how a request is written changes no figure of the plan.
# A field equal to its default may be omitted; a fee schedule without money
# takes the route's quote currency (F1-extended, plan §3).
# --------------------------------------------------------------------------
_CANDIDATE_MAX_FIXTURE = "pac_plan_request.candidate-max.v2.json"
_BROKER_ONE_CAPABILITY_ID = "cap-broker-one-eur-whole"
_RATE_SCHEDULE_ID = "fee-broker-one-rate-buy"
# SCIP's own floats: compared with a tolerance, never exactly.
_SCIP_FLOAT_FIELDS = ("primal", "dual", "absolute_gap", "relative_gap")


def _defaults_omitted(payload: dict) -> dict:
    """``payload`` as a compact client sends it: every field equal to its default dropped."""
    validated = _validated(payload)
    compact = validated.model_dump(mode="json", exclude_defaults=True)
    assert compact != validated.model_dump(mode="json"), "nothing to omit: the comparison would be vacuous"
    return compact


_EXPLICIT_REQUESTS = (
    pytest.param(_pac_request, id="min-no-op"),
    pytest.param(_incumbent_payload, id="min-incumbent"),
    pytest.param(lambda: _fixture(_CANDIDATE_MAX_FIXTURE), id="candidate-max"),
)


@pytest.mark.parametrize("build_payload", _EXPLICIT_REQUESTS)
def test_omitting_the_defaults_publishes_the_identical_result(build_payload):
    """The same validated request, written in full or without its defaults: one result, one fingerprint."""
    explicit = build_payload()

    explicit_wire = _plan_wire(explicit)
    compact_wire = _plan_wire(_defaults_omitted(explicit))

    assert compact_wire["snapshot"]["request_fingerprint"] == explicit_wire["snapshot"]["request_fingerprint"]
    assert compact_wire == explicit_wire


def _economic_projection(wire: dict) -> dict:
    """What the user acts on: each order (by route), its debit and fee, the costs, the objectives and the proof."""
    solution = wire["primary_solution"]
    orders = {row["route_id"]: (row["kind"], row["asset_id"], row["broker_id"], row["instruction"], row["cash_debit"], row["fee"]) for row in solution["order_rows"]}
    assert len(orders) == len(solution["order_rows"]), f"more than one order row on one route: {solution['order_rows']}"
    return {"orders": orders, "costs": solution["costs"], "objectives": solution["objectives"], "proof": wire["proof"]}


def _without_request_fingerprint_and_scip_floats(wire: dict) -> dict:
    """Every published field but the two kinds that may legitimately differ.

    Measured on this scenario (S1): ``snapshot.request_fingerprint`` is the only
    field that depends on how the request was written — the implicit and the
    explicit zero schedule carry different IDs, so they hash differently (plan
    §3); ``solution_id`` is the constant ``solution:primary``. SCIP's floats are
    compared on their own, with a tolerance.
    """
    figures = copy.deepcopy(wire)
    figures["snapshot"].pop("request_fingerprint")
    for stage in figures["solver_evidence"]["stages"]:
        for field in _SCIP_FLOAT_FIELDS:
            stage.pop(field, None)
    return figures


def _scip_primals(wire: dict) -> list[tuple[str, float]]:
    return [(stage["objective_code"], float(stage["primal"])) for stage in wire["solver_evidence"]["stages"]]


def _assert_same_plan_figures(candidate: dict, reference: dict) -> None:
    assert _economic_projection(candidate) == _economic_projection(reference)
    assert _without_request_fingerprint_and_scip_floats(candidate) == _without_request_fingerprint_and_scip_floats(reference)
    candidate_primals, reference_primals = _scip_primals(candidate), _scip_primals(reference)
    assert [code for code, _ in candidate_primals] == [code for code, _ in reference_primals]
    for (code, candidate_primal), (_, reference_primal) in zip(candidate_primals, reference_primals, strict=True):
        assert math.isclose(candidate_primal, reference_primal, rel_tol=1e-9, abs_tol=1e-6), code


def test_compact_twin_plans_like_min_figure_for_figure():
    """The compact twin (no defaults, no fee schedule at all) buys exactly what ``min`` buys.

    ``min`` alone is a no-op (€5 against a €10 whole unit), which any two
    requests would agree on: both get the same €50 of cash first, and the
    reference must really trade. The fingerprints are not compared — the twin's
    implicit zero instance has its own ID (plan §3).
    """
    reference = _plan_wire(_incumbent_payload())
    twin = _plan_wire(_incumbent_payload(_compact_pac_request()))

    assert (reference["result_state"], reference["proof"]["kind"]) == ("ready_incumbent", "optimal_proven")
    assert reference["primary_solution"]["order_rows"], "positive control: the reference must buy something"
    _assert_same_plan_figures(twin, reference)


def _incumbent_with_buy_schedule(**schedule: object) -> dict:
    payload = _incumbent_payload()
    broker = next(row for row in payload["brokers"] if row["broker_id"] == _BROKER_ONE_ID)
    broker["fee_schedules"] = [{"fee_schedule_id": _RATE_SCHEDULE_ID, "capability_id": _BROKER_ONE_CAPABILITY_ID, "side": "buy", **schedule}]
    route = next(row for row in payload["order_routes"] if row["route_id"] == _ASSET_ONE_ROUTE_ID)
    route["fee_schedule_id"] = _RATE_SCHEDULE_ID
    return payload


def test_rate_only_schedule_charges_like_its_explicit_eur_twin():
    """A 1% schedule with no money field charges what the same schedule spelled out in EUR charges.

    The fee is real (> 0), so the agreement is not two zeroes agreeing.
    """
    zero_eur = {"amount": "0", "currency": "EUR"}
    reference = _plan_wire(_incumbent_with_buy_schedule(fixed_fee=zero_eur, rate="0.01", variable_floor=zero_eur, variable_cap={"kind": "none"}))
    rate_only = _plan_wire(_incumbent_with_buy_schedule(rate="0.01"))

    assert (reference["result_state"], reference["proof"]["kind"]) == ("ready_incumbent", "optimal_proven")
    order_rows = reference["primary_solution"]["order_rows"]
    assert order_rows, "positive control: the reference must buy something"
    assert all(Fraction(row["fee"]["amount"]) > 0 for row in order_rows), order_rows
    assert _wire_exact(reference["primary_solution"]["costs"]["buy_fees"]["value"]) > 0
    _assert_same_plan_figures(rate_only, reference)
