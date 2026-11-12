"""Order constraints: the unconditional required minimum of a buy route and the zero-or-at-least activation floor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts, _minimum_value, as_float
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id
from backend.app.services.pac_allocator.models import ExactPlannerScenario

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model


def add_order_required_minimum_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """``ORDER_REQUIRED_MIN``: unconditional per-route floor (not "if
    active" — evaluator.py forces this to zero for SELL in ``primary``
    purpose, so only BUY routes can carry a real nonzero value here).
    """
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        required_minimum = _minimum_value(route, "required_minimum")
        if required_minimum == 0.0:
            continue
        capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
        order_step = as_float(capability.order_step)
        decision = variables.quanta[exact_decision_id("buy_quantum", route.route_id)]
        model.addCons(order_step * decision >= required_minimum, name=f"order_required_min:{route.route_id}")


def add_order_activation_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """``ORDER_MIN_IF_ACTIVE``: a BUY route's measure is either exactly zero
    or at least ``max(order_step, minimum_if_active)`` — a disjunction, so it
    needs the ``buy_active`` binary (also reused by the fee epigraph and by
    ``route_priority``/``active_order_rows`` in ``objectives.py``).

    Every finite bound used below (``measure_upper``) comes straight from
    the route's own ``upper_quanta`` (read back off the SCIP variable via
    ``getUbOriginal()``, the exact value ``compiler.py`` set at creation) —
    never an arbitrary constant. ``active_floor`` is always strictly
    positive since ``order_step`` itself must be positive (enforced by
    ``ExactOrderCapability.__post_init__``), so the floor row always applies.
    """
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
        order_step = as_float(capability.order_step)
        decision = variables.quanta[exact_decision_id("buy_quantum", route.route_id)]
        active = variables.buy_active[route.route_id]
        measure_upper = order_step * decision.getUbOriginal()
        model.addCons(order_step * decision <= measure_upper * active, name=f"order_active_upper:{route.route_id}")
        active_floor = max(order_step, _minimum_value(route, "minimum_if_active"))
        model.addCons(order_step * decision >= active_floor * active, name=f"order_active_floor:{route.route_id}")
