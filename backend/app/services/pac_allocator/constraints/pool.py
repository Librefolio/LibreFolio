"""The Rebalancer's cash rule in the SCIP model (lot CR of project 67; journal ``67_rebalancer/notes/regola-cassa-eseguibilita.md``).

A model that checks only the final balances lets cash go round between Brokers at no cost (free transfers, no spread): two
opposite exchanges and two transfers that no order of the steps can pay. The rule, agreed with the developer on 16/11:
- R1: a cell (Broker × currency) that receives a conversion sends nothing to another Broker;
- R2: money travels only in the currency it already has: a cell sends at most its original money, its cash and its deposits.

Instead of one decision per transfer lane, each cell has ONE signed integer, ``pool_net`` (minor units, positive = receives,
negative = sends); per currency the balances add up to zero. A number is never both positive and negative, so «back and
forth» is impossible. The lanes' decisions stay in the view (the replay, the report and the step counter read transfers) but
SCIP holds them at zero: ``derive_transfer_quanta`` sets them from the balances when the candidate is read
(``solver._extract_candidate``), by a fixed rule.

The exact replay checks the same rule as ``TRANSFER_NO_RELAY`` (``reachability.TransferRelayGroup``). The PAC has no cash
rule: it keeps one decision per lane, even on a lane a test sets by hand (D4 a), and its model does not move.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import as_float
from backend.app.services.pac_allocator.evaluation.bounds import transfer_decision_id
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id, floor_units
from backend.app.services.pac_allocator.models import ExactPlannerScenario, ExactPolicyView, ExactTransferLane

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model, Variable

    from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, LinearTerm, ScenarioFacts

type Cell = tuple[str, str]  # (Broker, currency)


class CashPoolContractError(ValueError):
    """The balances of a candidate cannot be carried by the scenario's lanes: a defect of the model, never a plan."""


@dataclass(frozen=True, slots=True)
class PoolVariables:
    """The cash rule's variables: per cell its balance, what it sends, whether it moves; per currency whether any cell moves."""

    net: dict[Cell, Variable]
    sent: dict[Cell, Variable]
    active: dict[Cell, Variable]
    moving: dict[str, Variable]
    sent_by_lane: dict[str, Variable]  # lane decision_id -> ``sent`` of its source cell, for the lane's tie-break stage


def pool_cells(scenario: ExactPlannerScenario) -> dict[str, tuple[str, ...]]:
    """The Brokers of every currency the lanes carry, sorted: the cells that get a balance. Empty for the PAC."""
    if scenario.product != "rebalancer":
        return {}
    brokers: dict[str, set[str]] = defaultdict(set)
    for lane in scenario.transfer_lanes:
        brokers[lane.currency].update((lane.source_broker_id, lane.destination_broker_id))
    return {currency: tuple(sorted(items)) for currency, items in sorted(brokers.items())}


def _own_quanta(scenario: ExactPlannerScenario, view: ExactPolicyView) -> dict[Cell, int]:
    """Each cell's original money in minor units, at most: its selected cash and every deposit its funding routes can bring
    (the routes' own upper bounds). R2's bound, and the tightest lower bound of the cell's balance."""
    quantum = {item.currency: item.minor_unit for item in scenario.currency_specs}
    upper = {access.decision_id: access.upper_quanta for access in view.decisions}
    own: dict[Cell, int] = defaultdict(int)
    for cash in scenario.existing_cash:
        own[(cash.broker_id, cash.selected.currency)] += floor_units(cash.selected.amount, quantum[cash.selected.currency])
    for route in scenario.funding_routes:
        if route.source_kind == "contribution":
            own[(route.broker_id, route.currency)] += upper[exact_decision_id("funding_transfer", route.route_id)]
    return own


def create_pool_variables(model: Model, scenario: ExactPlannerScenario, view: ExactPolicyView) -> PoolVariables | None:
    """The cash rule's variables, or ``None`` for a scenario without one (the PAC). A cell sends at most its own money (the
    lower bound of ``net``) and receives at most what the other cells of its currency own (the upper bound)."""
    cells = pool_cells(scenario)
    if not cells:
        return None
    own = _own_quanta(scenario, view)
    net: dict[Cell, Variable] = {}
    sent: dict[Cell, Variable] = {}
    active: dict[Cell, Variable] = {}
    moving: dict[str, Variable] = {}
    for currency, brokers in cells.items():
        total = sum(own.get((broker, currency), 0) for broker in brokers)
        for broker in brokers:
            mine = own.get((broker, currency), 0)
            name = f"{broker}:{currency}"
            net[(broker, currency)] = model.addVar(vtype="I", lb=-mine, ub=total - mine, name=f"pool_net:{name}")
            sent[(broker, currency)] = model.addVar(vtype="I", lb=0, ub=mine, name=f"pool_sent:{name}")
            active[(broker, currency)] = model.addVar(vtype="B", name=f"pool_active:{name}")
        moving[currency] = model.addVar(vtype="B", name=f"pool_moving:{currency}")
    sent_by_lane = {transfer_decision_id(lane): sent[(lane.source_broker_id, lane.currency)] for lane in scenario.transfer_lanes}
    return PoolVariables(net=net, sent=sent, active=active, moving=moving, sent_by_lane=sent_by_lane)


def add_cash_pool_terms(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, cells: dict[Cell, list[LinearTerm]]) -> None:
    """Post each cell's balance into its ledger, in place of the lanes' transfers, with the rule's rows:

    - ``pool_native`` (R2): what a cell sends is covered by its cash and the deposits it receives;
    - ``pool_balance``: per currency, the balances add up to zero (a transfer moves money, it does not make any);
    - ``own_first`` (R1): a conversion into a cell switches its balance to «receives or nothing», through the conversion's
      activity binary; the coefficient is the balance's own lower bound, the cell's original money, read off the variable;
    - ``pool_sent``: what the cell sends, at least minus its balance (read only by the lanes' tie-breaks);
    - ``pool_active``/``pool_moving``: a moving cell switches its binary on, and a currency moves if any of its cells does,
      for the operation count (``objectives.build_operation_count_stage``).
    """
    pool = variables.pool
    if pool is None:
        return
    native: dict[Cell, float] = defaultdict(float)
    for cash in scenario.existing_cash:
        native[(cash.broker_id, cash.selected.currency)] += as_float(cash.selected.amount)
    deposits: dict[Cell, list[LinearTerm]] = defaultdict(list)
    for route in scenario.funding_routes:
        if route.source_kind == "contribution":
            deposits[(route.broker_id, route.currency)].append(facts.currency_quantum[route.currency] * variables.quanta[exact_decision_id("funding_transfer", route.route_id)])
    by_currency: dict[str, list[Variable]] = defaultdict(list)
    moving_by_currency: dict[str, list[Variable]] = defaultdict(list)
    for (broker, currency), balance in pool.net.items():
        quantum = facts.currency_quantum[currency]
        name = f"{broker}:{currency}"
        moved = quantum * balance
        cells[(broker, currency)].append(moved)
        model.addCons(moved + native[(broker, currency)] + sum(deposits[(broker, currency)], 0.0) >= 0, name=f"pool_native:{name}")
        model.addCons(pool.sent[(broker, currency)] >= -balance, name=f"pool_sent:{name}")
        active = pool.active[(broker, currency)]
        model.addCons(balance <= balance.getUbOriginal() * active, name=f"pool_active_in:{name}")
        model.addCons(balance >= balance.getLbOriginal() * active, name=f"pool_active_out:{name}")
        by_currency[currency].append(balance)
        moving_by_currency[currency].append(active)
    for currency, balances in by_currency.items():
        model.addCons(sum(balances, 0.0) == 0, name=f"pool_balance:{currency}")
        model.addCons(pool.moving[currency] <= sum(moving_by_currency[currency], 0.0), name=f"pool_moving:{currency}")
    for spec in facts.fx_decisions:
        balance = pool.net.get((spec.broker_id, spec.destination_currency))
        if balance is None:
            continue
        model.addCons(balance >= balance.getLbOriginal() * (1 - variables.fx_active[spec.decision_id]), name=f"own_first:{spec.decision_id}")


def derive_transfer_quanta(lanes: tuple[ExactTransferLane, ...], nets: Mapping[Cell, int]) -> dict[str, int]:
    """The transfers of a plan from its cell balances, by a fixed rule: per currency, the senders and the receivers in Broker
    order, the first sender serving the first receiver until one of them is done. Every lane gets a value, zero if unused.

    Each balance must add up to zero per currency and every sender-receiver pair needs its lane (the Rebalancer's lanes join
    every pair of its Brokers): otherwise ``CashPoolContractError``.
    """
    by_pair = {(lane.source_broker_id, lane.destination_broker_id, lane.currency): transfer_decision_id(lane) for lane in lanes}
    quanta = dict.fromkeys(by_pair.values(), 0)
    by_currency: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (broker, currency), value in sorted(nets.items()):
        by_currency[currency].append((broker, value))
    for currency, items in by_currency.items():
        if sum(value for _, value in items) != 0:
            raise CashPoolContractError(f"the balances of {currency} do not add up to zero: {items}")
        senders = [[broker, -value] for broker, value in items if value < 0]
        receivers = [[broker, value] for broker, value in items if value > 0]
        i = j = 0
        while i < len(senders) and j < len(receivers):
            moved = min(senders[i][1], receivers[j][1])
            key = (senders[i][0], receivers[j][0], currency)
            if key not in by_pair:
                raise CashPoolContractError(f"no lane from {key[0]} to {key[1]} in {currency}")
            quanta[by_pair[key]] += moved
            senders[i][1] -= moved
            receivers[j][1] -= moved
            i += senders[i][1] == 0
            j += receivers[j][1] == 0
    return quanta
