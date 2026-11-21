"""Funding constraints: the pool a funding source draws from and the activation link of a funding route."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts, as_float
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id
from backend.app.services.pac_allocator.models import ExactOrderRoute, ExactPlannerScenario

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model


def add_funding_pool_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """``FUNDING_WITHIN_SELECTED``: one Broker/currency cash pool can fund
    several routes at once (e.g. split across two destination Brokers); the
    *sum* of what those routes transfer must not exceed what was selected.
    """
    by_source: dict[tuple[str, str], list[ExactOrderRoute]] = defaultdict(list)
    for route in scenario.funding_routes:
        by_source[(route.source_kind, route.source_id)].append(route)
    for (source_kind, source_id), routes in by_source.items():
        selected = _source_selected_amount(scenario, source_kind, source_id)
        transferred = [facts.currency_quantum[route.currency] * variables.quanta[exact_decision_id("funding_transfer", route.route_id)] for route in routes]
        if transferred:
            model.addCons(sum(transferred) <= selected, name=f"funding_within_selected:{source_kind}:{source_id}")


def _source_selected_amount(scenario: ExactPlannerScenario, source_kind: str, source_id: str) -> float:
    if source_kind == "existing_cash":
        for cash in scenario.existing_cash:
            if cash.cash_id == source_id:
                return as_float(cash.selected.amount)
    elif source_kind == "contribution":
        for contribution in scenario.contributions:
            if contribution.contribution_id == source_id:
                return as_float(contribution.amount.amount)
    raise KeyError(f"unknown funding source {source_kind}:{source_id}")


def _source_cash_cell(scenario: ExactPlannerScenario, source_kind: str, source_id: str) -> tuple[str, str] | None:
    """Return the (broker_id, currency) ledger cell a funding source draws
    down, or ``None`` for a contribution (fresh money, no broker ledger).
    """
    if source_kind != "existing_cash":
        return None
    for cash in scenario.existing_cash:
        if cash.cash_id == source_id:
            return (cash.broker_id, cash.selected.currency)
    raise KeyError(f"unknown existing_cash source {source_id}")


def add_funding_activation_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """Link ``funding_active`` to its transfer decision the same way, purely
    for ``objectives.route_priority`` — funding routes carry no fee/floor.
    """
    for route in scenario.funding_routes:
        decision = variables.quanta[exact_decision_id("funding_transfer", route.route_id)]
        active = variables.funding_active[route.route_id]
        quantum = facts.currency_quantum[route.currency]
        transfer_upper = quantum * decision.getUbOriginal()
        model.addCons(quantum * decision <= transfer_upper * active, name=f"funding_active_upper:{route.route_id}")
