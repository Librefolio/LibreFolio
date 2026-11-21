"""The reserve a Rebalancer posting keeps back for its rounding (row 6 of lot CR, project 67; specification §16.6).

In the Rebalancer's model money is continuous: a buy's cost, its fee and a conversion's credit enter their cash cells as
exact amounts, with no rounding variable. The exact replay still rounds every posting once, against the plan (a debit up, a
credit down, ``ledger._PLAN_ROUNDING``). So that the rounding never leaves a cell short, each posting that happens keeps
back the worst case of its rounding: one minor unit of its currency, a debit taken out one unit higher, a credit coming in
one unit lower. Whatever the true rounding does not use stays in the cell.

A posting whose every possible amount is a whole number of minor units never rounds, and keeps nothing back: a buy by
amount in steps of one euro, a fixed fee of five euros. Its amounts are integer combinations of a few generators (a route's
step, a fee's parts, a conversion's rate times the source's minor unit); it rounds when one of them is not a multiple of the
minor unit. Without this, a plan that spends a cell to its last cent, as the hand-computed cases do (T4: 195 € of B and a
5 € fee out of 200 €), would look a cent or two short to the model.

The model (``constraints.cells``) and the replay's value «as the solver sees it» (``evaluation.solver_view``) read this one
table, keyed by the replay's posting ids, so they agree on every plan. The reserve is not a coefficient of ours (P5): it is
the currency's minor unit.

``RESERVE_ENABLED`` is the switch the developer has not decided yet (the coordinator recommends it on). Off, the model
spends cash to its last fraction of a cent and the replay may leave a cell a few cents short, which the plan then
publishes as a rounding top-up.
"""

from __future__ import annotations

from backend.app.services.pac_allocator.evaluation.reachability import fx_decision_specs
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, fx_rate, order_prices, valuation_rate_of
from backend.app.services.pac_allocator.models import ExactPlannerScenario
from backend.app.services.pac_allocator.numeric import ExactRatio, calculate_planning_fx_rate

RESERVE_ENABLED: bool = True

RESERVED_FAMILIES: frozenset[str] = frozenset({"buy_debit", "buy_fee", "fx_credit"})

_EXACT_ZERO = ExactRatio(0)


def _rounds(generators: tuple[ExactRatio, ...], quantum: ExactRatio) -> bool:
    """Whether an integer combination of ``generators`` can miss a multiple of ``quantum``: one of them is not a multiple."""
    for item in generators:
        ratio = item / quantum
        if ratio.denominator != 1:
            return True
    return False


def posting_reserves(scenario: ExactPlannerScenario) -> dict[str, ExactRatio]:
    """The reserve of every rounded posting a Rebalancer scenario can make, by the replay's posting id (``buy-debit:<route>``,
    ``buy-fee:<route>``, ``fx-credit:<key>``): one minor unit where the posting can round, zero where it cannot or when the
    reserve is off. Empty for the PAC, which keeps its rounded postings in the model."""
    if scenario.product != "rebalancer":
        return {}
    index = build_scenario_index(scenario)
    reserves: dict[str, ExactRatio] = {}

    def keep(posting_id: str, generators: tuple[ExactRatio, ...], quantum: ExactRatio) -> None:
        reserves[posting_id] = quantum if RESERVE_ENABLED and _rounds(generators, quantum) else _EXACT_ZERO

    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        capability = index.capabilities[(route.broker_id, route.capability_id)]
        fee = index.fees[(route.broker_id, route.fee_schedule_id)]
        quantum = index.currency_quantum[index.assets[route.asset_id].quote.price.currency]
        step = capability.order_step if capability.kind == "monetary_amount" else capability.order_step * order_prices(index, route).execution_native
        keep(f"buy-debit:{route.route_id}", (step,), quantum)
        fee_parts = (fee.fixed_fee.amount, fee.minimum_fee.amount, fee.proportional_rate * step, *((fee.maximum_fee.amount,) if fee.maximum_fee is not None else ()))
        keep(f"buy-fee:{route.route_id}", fee_parts, quantum)
    for spec in fx_decision_specs(scenario, index, None):
        rate = calculate_planning_fx_rate(
            approved_rate=fx_rate(index.fx_rate_by_pair, spec.source_currency, spec.destination_currency),
            spread=scenario.fx_spread_rate,
            source_valuation_rate=valuation_rate_of(index, spec.source_currency),
            destination_valuation_rate=valuation_rate_of(index, spec.destination_currency),
        )
        keep(f"fx-credit:{spec.key}", (index.currency_quantum[spec.source_currency] * rate,), index.currency_quantum[spec.destination_currency])
    return reserves
