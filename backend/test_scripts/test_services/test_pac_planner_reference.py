"""Project 67, lot A1: the PAC's reference values, and the rules that hold later plans to them.

A2 rewrites the FX decisions under the released PAC Tool. This file freezes what the planner publishes today, so that the
block can prove the PAC does not get worse. Two kinds of test, both pure (no server, no database):

* the rules R1-R7 of ``_pac_reference_values.reference_violations`` on made-up records: equal, better and worse vectors, an extra
  conversion, a new pair, a merge difference inside and outside its bound, a difference in a case with no merge;
* the file ``fixtures/pac_allocator/pac_reference_values.json`` (written once by ``diagnostics/pac_reference_recorder.py``, from the
  commit it names): its header, its cases, what it must not hold, and every case replanned through the real planner and held to
  it. The accepted-differences file starts empty: a difference A2-A4 causes is written there and approved by the coordinator, never
  by a rewrite of the reference.

N1 is the one case that records a fact about today's engine: two buys on one pair give two FX decisions. A2 rewrites that test.
"""

from __future__ import annotations

import copy
import json
import re
from fractions import Fraction

import pytest

from backend.test_scripts.test_services import _pac_reference_values as ref
from backend.test_scripts.test_services import _pac_synthetic_requests as synthetic
from backend.test_scripts.test_utils import print_section, print_success

PAIR = "broker-one|EUR|USD"


def _record(**overrides) -> dict:
    """A made-up recorded plan: one conversion EUR to USD, one order, two cells, no merge (one action per pair)."""
    record = {
        "uses_required_minimum": False,
        "state": "ready_incumbent",
        "proof_kind": "optimal_proven",
        "stop_reason": "completed",
        "valuation_rates": {"EUR": "1", "USD": "100/108"},
        "minor_units": {"EUR": "1/100", "USD": "1/100"},
        "references": {"fixed_reference": "100", "selected_funding": "100", "reachable_funding": "100", "trapped_funding": "0"},
        "asset_target_values": {"asset-1": "100"},
        "objective_vector": ["1000", "20", "5", "3", "1"],
        "conversions": {PAIR: {"debit": "93.1", "credit": "100", "spread_loss": "0.931"}},
        "fx_actions_per_pair": {PAIR: 1},
        "orders": {"route-1": {"asset_id": "asset-1", "broker_id": "broker-one", "quantity": "2", "cash_debit": "100", "fee": "0"}},
        "fundings": {"funding-1": "93.1"},
        "cells": {
            "broker-one|EUR": {"final_spendable": "0", "fx_debit": "93.1", "fx_credit": "0"},
            "broker-one|USD": {"final_spendable": "0", "fx_debit": "0", "fx_credit": "100"},
        },
        "rounding_top_ups": 0,
        "accounting": {"final_invested": "92", "shortfall": "8", "free_cash": "0", "economic_losses": "0.931", "rounding_delta": "0"},
        "costs": dict.fromkeys(ref.COST_FIELDS, "0"),
    }
    return {**copy.deepcopy(record), **overrides}


def _merged(**overrides) -> dict:
    """The same plan as one that A1 published with two FX actions on the one pair: R5 may apply."""
    return _record(fx_actions_per_pair={PAIR: 2}, **overrides)


def _with(record: dict, path: tuple[str, ...], value) -> dict:
    result = copy.deepcopy(record)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return result


def _entry(quantity: str, before: str, after: str) -> dict:
    return {"case": "made-up", "quantity": quantity, "before": before, "after": after, "unit": "-", "reason": "test", "approved_by": "test"}


# ---------------------------------------------------------------------------
# The rules, on made-up records
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "accepted", "rule"),
    [
        pytest.param(_record(), [], None, id="equal"),
        pytest.param(_with(_record(), ("objective_vector",), ["1000", "20", "5", "3", "2"]), [], "R3", id="worse-last-stage"),
        pytest.param(_with(_record(), ("objective_vector",), ["1001", "0", "0", "0", "0"]), [], "R3", id="worse-first-stage-beats-better-later-ones"),
        pytest.param(_with(_record(), ("objective_vector",), ["1000", "19", "9", "9", "9"]), [], "R7", id="better-alone-does-not-pass"),
        pytest.param(
            _with(_record(), ("objective_vector",), ["1000", "19", "9", "9", "9"]),
            [_entry("objective_vector", json.dumps(["1000", "20", "5", "3", "1"]), json.dumps(["1000", "19", "9", "9", "9"]))],
            None,
            id="better-and-accepted",
        ),
        pytest.param(_record(state="ready_no_incumbent"), [], "R1", id="state-changed"),
        pytest.param(_record(proof_kind="not_proven"), [], "R1", id="proof-lost"),
        pytest.param(_record(stop_reason="time_limit"), [], "R1", id="stop-reason-changed"),
        pytest.param(_with(_record(), ("references", "reachable_funding"), "101"), [], "R2", id="reference-moved"),
        pytest.param(_with(_record(), ("asset_target_values", "asset-1"), "99"), [], "R2", id="target-value-moved"),
        pytest.param(_with(_record(), ("conversions", "broker-one|USD|EUR"), {"debit": "1", "credit": "1", "spread_loss": "0"}), [], "R4", id="one-conversion-more-and-a-new-pair"),
    ],
)
def test_reference_rule_accepts_equal_and_better_and_refuses_worse(current, accepted, rule):
    print_section("Reference rules R1-R4, R7")
    problems = ref.reference_violations(_record(), current, accepted)
    if rule is None:
        assert problems == []
    else:
        assert any(problem.startswith(rule) for problem in problems), problems
    print_success(f"{rule or 'no violation'}")


def test_reference_rule_lets_a_conversion_go_and_refuses_a_new_pair():
    """R4 holds in one direction only: fewer conversions are fine (the PAC may do without one), more or new ones never."""
    dropped = _with(_record(), ("conversions",), {})
    assert not [problem for problem in ref.reference_violations(_record(), dropped, []) if problem.startswith("R4")]
    renamed = _with(_record(), ("conversions",), {"broker-one|CHF|USD": {"debit": "1", "credit": "1", "spread_loss": "0"}})
    assert any(problem.startswith("R4 new conversion pairs") for problem in ref.reference_violations(_record(), renamed, []))


MOVED_CELL = ("cells", "broker-one|USD", "final_spendable")


def _cell_moved(by: str) -> dict:
    current = _merged()
    current["cells"]["broker-one|USD"]["final_spendable"] = by
    return current


@pytest.mark.parametrize(
    ("recorded", "current", "accepted", "expected_prefixes"),
    [
        # R6: no merge in the recorded case, so any difference is refused, with or without an entry.
        pytest.param(_record(), _with(_record(), ("orders", "route-1", "cash_debit"), "99.99"), [], ["R6"], id="R6-no-merge-order-differs"),
        pytest.param(_record(), _with(_record(), ("orders", "route-1", "cash_debit"), "99.99"), [_entry("orders.route-1.cash_debit", "100", "99.99")], ["R6"], id="R6-an-entry-does-not-excuse-a-case-without-a-merge"),
        # R5: a merge, an equal vector, a difference inside the bound and written down.
        pytest.param(_merged(), _cell_moved("0.01"), [_entry("cells.broker-one|USD.final_spendable", "0", "0.01")], [], id="R5-inside-the-bound-and-accepted"),
        pytest.param(_merged(), _cell_moved("0.01"), [], ["R5 cells.broker-one|USD.final_spendable"], id="R5-inside-the-bound-but-not-written-down"),
        pytest.param(_merged(), _cell_moved("0.05"), [_entry("cells.broker-one|USD.final_spendable", "0", "0.05")], ["R5 cells' final spendable moved"], id="R5-written-down-but-outside-the-bound"),
        pytest.param(_merged(), _with(_merged(), ("rounding_top_ups",), 1), [], ["R5 rounding top-ups"], id="R5-one-more-top-up"),
        pytest.param(_merged(), _merged(), [], [], id="R5-merge-with-no-difference"),
        # R7: a strictly better vector in a merge case passes on its entry alone: the effect has no ceiling.
        pytest.param(
            _merged(),
            _with(_with(_merged(), ("objective_vector",), ["1000", "10", "5", "3", "1"]), ("orders", "route-1", "cash_debit"), "150"),
            [_entry("objective_vector", json.dumps(["1000", "20", "5", "3", "1"]), json.dumps(["1000", "10", "5", "3", "1"]))],
            [],
            id="R7-better-vector-covers-its-effects",
        ),
    ],
)
def test_reference_rule_bounds_a_merge_difference_by_its_units(recorded, current, accepted, expected_prefixes):
    print_section("Reference rules R5-R7")
    problems = ref.reference_violations(recorded, current, accepted)
    if not expected_prefixes:
        assert problems == []
    else:
        for prefix in expected_prefixes:
            assert any(problem.startswith(prefix) for problem in problems), (prefix, problems)
    print_success(f"expected {expected_prefixes or 'nothing'}")


def test_the_merge_bound_is_one_minor_unit_of_each_currency_per_merged_action():
    """Two actions on EUR to USD: (2 - 1) x (0.01 USD at 100/108 EUR + 0.01 EUR) = 0.0192592... EUR, valued at the mid rate."""
    allowance = ref.merge_allowance(_merged())
    assert allowance == Fraction(1, 100) * Fraction(100, 108) + Fraction(1, 100)
    assert ref.merge_allowance(_record()) == 0  # one action per pair: no merge, no allowance
    assert ref.merge_allowance(_record(fx_actions_per_pair={PAIR: 3})) == 2 * allowance


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------


def test_reference_record_holds_no_decision_id_fingerprint_or_time():
    """Neither the file nor a freshly extracted record carries a decision id, a tie-break key, a fingerprint or a wall time."""
    print_section("Reference record: what it must not hold")
    text = ref.REFERENCE_FILE.read_text(encoding="utf-8")
    fresh = json.dumps(ref.plan_record(ref.CASES["fx-eur-funds-usd"](), budget_seconds=10), sort_keys=True)
    for label, source in (("the file", text), ("a fresh record", fresh)):
        for token in ref.FORBIDDEN_IN_RECORD:
            assert token not in source, f"{label} holds {token!r}"
    assert not re.search(r"\d{4}-\d{2}-\d{2}T", text), "a timestamp in the reference file"
    print_success("no fx:, tie_break, ordered_keys, fingerprint, wall, timestamp")


def test_reference_file_names_its_commit_and_budget_and_every_case():
    print_section("Reference record: header and cases")
    recorded = ref.load_reference()
    header = recorded["header"]
    assert re.fullmatch(r"[0-9a-f]{40}", header["recorded_at_commit"]), header
    assert header["solver_budget_seconds"] == ref.REFERENCE_BUDGET_SECONDS
    assert set(recorded["cases"]) == set(ref.CASES), "the file and the corpus name different cases: re-recording is a decision of the coordinator, not a fix"
    for name, case in recorded["cases"].items():
        assert isinstance(case["uses_required_minimum"], bool), name
    assert ref.load_accepted() == [] or all({"case", "quantity", "before", "after", "unit", "reason", "approved_by"} <= set(entry) for entry in ref.load_accepted())
    print_success(f"{len(recorded['cases'])} cases, recorded at {header['recorded_at_commit'][:9]}")


def test_no_reference_case_uses_a_required_minimum():
    """M19: A4 removes «Acquisto obbligatorio» from the PAC. A case that used it would change in A4, and the file is frozen."""
    assert not [name for name, build in ref.CASES.items() if ref.uses_required_minimum(build())]
    assert not [name for name, build in ref.GRID_VARIANTS.items() if ref.uses_required_minimum(build())]
    assert not [name for name, case in ref.load_reference()["cases"].items() if case["uses_required_minimum"]]


@pytest.mark.parametrize("name", sorted(ref.CASES))
def test_reference_case_matches_the_recorded_plan(name):
    """Every corpus case, planned in the Tool's engine window, holds the rules R1-R7 against what the file recorded."""
    print_section(f"Reference case {name}")
    recorded = ref.load_reference()["cases"][name]
    accepted = [entry for entry in ref.load_accepted() if entry["case"] == name]
    current = ref.plan_record(ref.CASES[name]())
    assert ref.reference_violations(recorded, current, accepted) == []
    print_success(f"{name}: {current['state']} {current['proof_kind']} {current['stop_reason']}")


def test_two_buys_on_one_pair_have_two_fx_decisions():
    """N1, today: two buy routes on the one EUR to USD pair of broker-one give two ``fx_debit`` decisions.

    The plan of today ties an FX decision to the route that spends it. A2 changes it to one decision per broker and pair, and rewrites
    this test to expect one: it is the signal that the exchange happened. This test does not say how many FX actions the plan publishes.
    """
    _, view = synthetic.scenario_of(synthetic.fx_two_assets_one_pair_request())
    refs_of = {decision.decision_id: {(item.kind, item.entity_id) for item in decision.entity_refs} for decision in view.decisions if decision.family == "fx_debit"}
    from_eur = [refs for refs in refs_of.values() if ("currency", "EUR") in refs]
    assert len(from_eur) == 2, refs_of
    assert {entity for refs in from_eur for kind, entity in refs if kind == "order_route"} == {"route-asset-1-buy", "route-asset-2-buy"}


@pytest.mark.parametrize(
    ("build", "expected_from_currencies_by_route"),
    [
        pytest.param(synthetic.fx_two_way_request, {"route-asset-1-buy": {"USD"}, "route-asset-2-buy": {"EUR"}}, id="N2-both-directions-of-one-pair"),
        pytest.param(synthetic.fx_two_brokers_request, {"route-asset-1-buy": {"EUR"}, "route-asset-1-broker-two-buy": {"EUR"}}, id="N3-one-conversion-per-broker"),
        pytest.param(synthetic.fx_two_sources_request, {"route-asset-1-buy": {"EUR", "CHF"}}, id="N4-two-pairs-toward-one-currency"),
    ],
)
def test_the_new_corpus_cases_open_the_conversions_they_are_built_for(build, expected_from_currencies_by_route):
    """N2-N4 are only worth recording if the view offers the conversions V7 and the broker split act on: read from the engine's own view."""
    _, view = synthetic.scenario_of(build())
    found: dict[str, set[str]] = {}
    for decision in view.decisions:
        if decision.family != "fx_debit":
            continue
        refs = {(item.kind, item.entity_id) for item in decision.entity_refs}
        (route,) = [entity for kind, entity in refs if kind == "order_route"]
        (currency,) = [entity for kind, entity in refs if kind == "currency"]
        found.setdefault(route, set()).add(currency)
    assert found == expected_from_currencies_by_route
