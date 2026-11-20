"""The plan's step counter is an executable order (contract §6.3 of project 67, specification §15 n. 7).

Followed by its numbers, a plan must be doable: every step finds, in the cash it spends, what the steps before it left
there. Found in F4a: on the G5 browser scenario the engine numbered a transfer of dollars out of a Broker that had none
until the exchange numbered after it (deposits, transfers, conversions, orders, in that fixed order).

Two layers:
- ``plan_sequence`` on hand-made flows: the G5 shape (EUR transfer Broker 1 → 2, the exchange on Broker 2, USD transfer
  Broker 2 → 1, then the purchases), the PAC's deposit before the exchange it pays, a conversion the Broker makes by itself
  applied where its order needs it, and a cycle no order can pay, which is refused;
- the engine's own plans: the G5 request (``rebalancer_plan_request.g5-browser.2-0-0.json``, the planner's real request on
  the test server's mock data) through ``plan_rebalancing``, and a PAC plan with a deposit and an exchange through
  ``plan_pac_allocation``. Each published plan is replayed in its numbers (``assert_executable``) from the ledger's initial
  balances, and must end at the ledger's final ones.

Amounts are the posted ones the ledger reconciles (each currency's minor unit), so the balances are compared exactly.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER
from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER
from backend.app.services.pac_allocator import plan_sequence
from backend.app.services.pac_allocator.plan_sequence import PlanNotExecutableError, PlanStepFlow, assert_executable, executable_order, step_flows
from backend.app.services.pac_allocator.planner import plan_pac_allocation, plan_rebalancing
from backend.test_scripts.test_services._pac_synthetic_requests import fx_conversion_request

G5_REQUEST = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator" / "rebalancer_plan_request.g5-browser.2-0-0.json"
B1, B2 = "broker:1", "broker:2"


def _f(text: str) -> Fraction:
    return Fraction(text)


def _flow(key: str, kind: str, debits=(), credits=(), *, numbered: bool = True) -> PlanStepFlow:
    return PlanStepFlow(key, kind, tuple((cell, _f(amount)) for cell, amount in debits), tuple((cell, _f(amount)) for cell, amount in credits), numbered=numbered)


# -- the counter on hand-made flows ---------------------------------------------------------------------------------


def _g5_flows() -> list[PlanStepFlow]:
    """The G5 plan's flows, in the lists' own order (as the report used to number them)."""
    return [
        _flow("transfer-eur", "transfer", [((B1, "EUR"), "6889.09")], [((B2, "EUR"), "6889.09")]),
        _flow("transfer-usd", "transfer", [((B2, "USD"), "818.65")], [((B1, "USD"), "818.65")]),
        _flow("exchange", "conversion", [((B2, "EUR"), "15089.09")], [((B2, "USD"), "16901.65")]),
        _flow("buy-usd", "order", [((B2, "USD"), "15975.75")]),
        _flow("buy-eur", "order", [((B1, "EUR"), "5078.56")]),
    ]


_G5_INITIAL = {(B1, "EUR"): _f("17350"), (B1, "USD"): _f("5344.53"), (B2, "EUR"): _f("8200"), (B2, "USD"): _f("0")}


def test_the_g5_shape_is_numbered_in_an_order_the_balances_can_follow() -> None:
    """The EUR transfer first (the exchange needs it), then the exchange (the USD transfer spends its dollars), then the USD
    transfer, then the purchases."""
    ordered = executable_order(_G5_INITIAL, _g5_flows())
    assert [flow.key for flow in ordered] == ["transfer-eur", "exchange", "transfer-usd", "buy-usd", "buy-eur"]


def test_the_old_fixed_order_of_kinds_is_not_executable_on_the_g5_shape() -> None:
    """The order the report used before (transfers, then conversions, then orders): the USD transfer spends dollars Broker 2
    does not hold yet. The invariant refuses it."""
    flows = [PlanStepFlow(flow.key, flow.kind, flow.debits, flow.credits, sequence=number) for number, flow in enumerate(_g5_flows(), start=1)]
    with pytest.raises(PlanNotExecutableError, match="step 2"):
        assert_executable(_G5_INITIAL, flows)


def test_a_purchase_comes_after_the_transfer_that_brings_its_cash() -> None:
    flows = [
        _flow("buy-b1-usd", "order", [((B1, "USD"), "100")]),
        _flow("transfer-usd", "transfer", [((B2, "USD"), "100")], [((B1, "USD"), "100")]),
    ]
    ordered = executable_order({(B1, "USD"): _f("0"), (B2, "USD"): _f("100")}, flows)
    assert [flow.key for flow in ordered] == ["transfer-usd", "buy-b1-usd"]


def test_a_deposit_comes_before_the_exchange_it_pays_for() -> None:
    """The PAC's shape: a contribution reaches the Broker, then the exchange spends it."""
    flows = [
        _flow("exchange", "conversion", [((B1, "EUR"), "100")], [((B1, "USD"), "110")]),
        _flow("deposit", "funding", [], [((B1, "EUR"), "100")]),
        _flow("buy", "order", [((B1, "USD"), "110")]),
    ]
    ordered = executable_order({}, flows)
    assert [flow.key for flow in ordered] == ["deposit", "exchange", "buy"]


def test_a_conversion_the_broker_makes_by_itself_has_no_number_and_pays_its_order() -> None:
    flows = [
        _flow("auto", "conversion", [((B1, "EUR"), "100")], [((B1, "USD"), "110")], numbered=False),
        _flow("buy", "order", [((B1, "USD"), "110")]),
    ]
    ordered = executable_order({(B1, "EUR"): _f("100")}, flows)
    assert [flow.key for flow in ordered] == ["buy"]


def test_a_transfer_of_an_automatic_conversion_s_proceeds_applies_the_conversion() -> None:
    """A Broker that converts by itself: its proceeds can leave by a transfer, with no order on that cell to trigger it."""
    flows = [
        _flow("auto", "conversion", [((B2, "EUR"), "100")], [((B2, "USD"), "110")], numbered=False),
        _flow("transfer-usd", "transfer", [((B2, "USD"), "110")], [((B1, "USD"), "110")]),
        _flow("buy-b1", "order", [((B1, "USD"), "110")]),
    ]
    initial = {(B2, "EUR"): _f("100")}
    ordered = executable_order(initial, flows)
    assert [flow.key for flow in ordered] == ["transfer-usd", "buy-b1"]
    numbered = [PlanStepFlow(flow.key, flow.kind, flow.debits, flow.credits, numbered=flow.numbered, sequence={"transfer-usd": 1, "buy-b1": 2}.get(flow.key)) for flow in flows]
    assert_executable(initial, numbered)


def test_final_balances_that_differ_from_the_ledger_are_refused() -> None:
    flows = [PlanStepFlow("buy", "order", (((B1, "EUR"), _f("10")),), (), sequence=1)]
    assert_executable({(B1, "EUR"): _f("10")}, flows, {(B1, "EUR"): _f("0")})
    with pytest.raises(PlanNotExecutableError, match="the ledger says"):
        assert_executable({(B1, "EUR"): _f("10")}, flows, {(B1, "EUR"): _f("1")})


def test_the_known_limit_cash_that_returns_to_its_cell() -> None:
    """The counter is greedy, not a search. Here an order exists (both transfers, then the exchange), but the counter
    takes the exchange first, as its kind comes before the transfers, and then no transfer can be paid: it refuses the
    plan. It needs cash that leaves a cell and comes back to it; no engine plan has shown it."""
    flows = [
        _flow("exchange", "conversion", [((B1, "EUR"), "10")], [((B1, "USD"), "11")]),
        _flow("out", "transfer", [((B1, "EUR"), "10")], [((B2, "EUR"), "10")]),
        _flow("back", "transfer", [((B2, "EUR"), "10")], [((B1, "EUR"), "10")]),
    ]
    initial = {(B1, "EUR"): _f("10")}
    with pytest.raises(PlanNotExecutableError):
        executable_order(initial, flows)
    by_hand = [PlanStepFlow(flow.key, flow.kind, flow.debits, flow.credits, sequence={"out": 1, "back": 2, "exchange": 3}[flow.key]) for flow in flows]
    assert_executable(initial, by_hand)


def test_a_cycle_no_order_can_pay_is_refused() -> None:
    """Each transfer needs what the other brings: no order is executable, and the counter says so instead of numbering one."""
    flows = [
        _flow("to-b2", "transfer", [((B1, "EUR"), "10")], [((B2, "EUR"), "10")]),
        _flow("to-b1", "transfer", [((B2, "USD"), "10")], [((B1, "USD"), "10")]),
        _flow("exchange-b1", "conversion", [((B1, "USD"), "10")], [((B1, "EUR"), "10")]),
        _flow("exchange-b2", "conversion", [((B2, "EUR"), "10")], [((B2, "USD"), "10")]),
    ]
    with pytest.raises(PlanNotExecutableError, match="no step can be paid"):
        executable_order({}, flows)


# -- the engine's own plans -------------------------------------------------------------------------------------------


def _published_flows(request: dict, solution) -> tuple[dict, dict, list[PlanStepFlow]]:
    cells = {cash["cash_id"]: (cash["broker_id"], cash["selected"]["currency"]) for cash in request.get("existing_cash", [])}
    initial = {(row.broker_id, row.currency): Fraction(row.initial_selected) for row in solution.ledger_rows}
    final = {(row.broker_id, row.currency): Fraction(row.final_physical) for row in solution.ledger_rows}
    flows = step_flows(solution.funding_actions, getattr(solution, "transfers", []), solution.conversions, solution.order_rows, cells)
    return initial, final, flows


def test_the_engine_numbers_the_g5_plan_in_an_executable_order() -> None:
    request = json.loads(G5_REQUEST.read_text())
    result = plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=3.5)
    assert result.result_state == "ready_incumbent"
    solution = result.primary_solution
    initial, final, flows = _published_flows(request, solution)
    assert_executable(initial, flows, final)
    # The cash rule (lot CR, specification §16.2): no transfer leaves a cell that a conversion or a transfer credits, so
    # converted money never travels. The plan itself depends on the solver's clock (not proven at 3.5 s): the rule does not.
    # Before the rule this plan was: EUR transfer, exchange, then the USD transfer it paid for.
    credited = {(row.destination_broker_id, row.amount.currency) for row in solution.transfers} | {(row.broker_id, row.destination_credit.currency) for row in solution.conversions}
    assert solution.transfers, "PREMISE: on G5 cash has to travel"
    assert all((row.source_broker_id, row.amount.currency) not in credited for row in solution.transfers)


def test_the_engine_numbers_the_g5_plan_executably_when_both_brokers_convert_by_themselves() -> None:
    request = json.loads(G5_REQUEST.read_text())
    for broker in request["brokers"]:
        broker["conversion_mode"] = "automatic"
    result = plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=3.5)
    assert result.result_state == "ready_incumbent"
    initial, final, flows = _published_flows(request, result.primary_solution)
    assert_executable(initial, flows, final)


def test_the_planner_checks_the_invariant_on_the_plan_it_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The check runs in production, not only here: with the counter replaced by the builders' own order (the old one),
    planning G5 raises instead of publishing a plan in an order its balances cannot follow."""
    monkeypatch.setattr(plan_sequence, "executable_order", lambda _initial, flows: [flow for flow in flows if flow.numbered])
    request = json.loads(G5_REQUEST.read_text())
    with pytest.raises(PlanNotExecutableError):
        plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=3.5)


def test_the_engine_numbers_a_pac_plan_with_a_deposit_and_an_exchange_in_an_executable_order() -> None:
    request = fx_conversion_request("plan-sequence-pac", funding_currency="EUR", assets=[("USD", "10")], fx_rates={"EUR/USD": "1.1"})
    result = plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=3.5)
    assert result.result_state == "ready_incumbent"
    solution = result.primary_solution
    assert solution.funding_actions and [row for row in solution.conversions if row.sequence is not None]
    initial, final, flows = _published_flows(request, solution)
    assert_executable(initial, flows, final)
