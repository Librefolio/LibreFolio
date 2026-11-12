"""Fee constraints: the bounds of the fee variable and the epigraph that linearizes the exact fee formula
(``financial_math.fees.calculate_fee``) for every buy route.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts, as_float, order_notional
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id
from backend.app.services.pac_allocator.models import ExactFeeSchedule, ExactOrderCapability, ExactOrderRoute, ExactPlannerScenario

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model

    from backend.app.services.pac_allocator.constraints.facts import LinearTerm


def _fee_cap_excess(fee_schedule: ExactFeeSchedule, notional_upper: float) -> float | None:
    """``rate * notional_upper - cap`` where the fee cap can bind within the
    route's notional range, else ``None`` (no cap, or a linear fee that
    never exceeds it). This one predicate decides both halves of the exact
    cap (QX1-a, module docstring): whether ``add_fee_epigraph_constraints``
    gives the route a ``fee_capped`` binary, with this excess as the Big-M
    that switches the linear row off on the cap branch, and whether
    ``_fee_clamp_upper`` lowers the fee bound to the cap.
    """
    if fee_schedule.maximum_fee is None:
        return None
    linear_upper = as_float(fee_schedule.proportional_rate) * notional_upper
    cap = as_float(fee_schedule.maximum_fee.amount)
    return linear_upper - cap if linear_upper > cap else None


def _fee_clamp_upper(fee_schedule: ExactFeeSchedule, notional_upper: float) -> float:
    """Upper bound of ``clamp(rate * notional, floor, cap)`` over the route's
    notional range: ``max(floor, min(rate * notional_upper, cap))``. The
    floor must be in it (X2); the cap only where ``_fee_cap_excess`` gives
    the route its binary (QX1-a), both in the module docstring.
    """
    linear_upper = as_float(fee_schedule.proportional_rate) * notional_upper
    if fee_schedule.maximum_fee is not None and _fee_cap_excess(fee_schedule, notional_upper) is not None:
        linear_upper = as_float(fee_schedule.maximum_fee.amount)
    return max(as_float(fee_schedule.minimum_fee.amount), linear_upper)


def _fee_variable_upper(facts: ScenarioFacts, route: ExactOrderRoute, capability: ExactOrderCapability, notional_upper: float) -> float:
    """The same upper bound ``add_fee_epigraph_constraints`` gives the fee
    variable, reused so the posted-units variable is bounded by the very
    envelope the fee itself lives in.
    """
    fee_schedule = facts.fee_by_key[(route.broker_id, route.fee_schedule_id)]
    return as_float(fee_schedule.fixed_fee.amount) + _fee_clamp_upper(fee_schedule, notional_upper)


def add_fee_epigraph_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """Linearize ``financial_math.fees.calculate_fee``'s ``0 if notional==0 else fixed +
    clamp(rate*notional, floor, cap)`` for every BUY route, gated by the same
    ``buy_active`` binary as ``add_order_activation_constraints``.

    Rows, with ``fee_upper`` from ``_fee_clamp_upper`` and ``big_m = fixed +
    fee_upper``:

    - ``fee_active_upper``: ``fee <= big_m * active``;
    - ``fee_floor``: ``fee >= fixed + floor - big_m * (1 - active)``;
    - ``fee_linear``: ``fee >= fixed + rate * notional - big_m * (1 -
      active) - cap_excess * capped``;
    - only where the cap can bind (``_fee_cap_excess``), a ``fee_capped``
      binary with ``fee_capped_active``: ``capped <= active``, and
      ``fee_cap``: ``fee >= (fixed + cap) * capped``.

    Order off: ``order_active_upper`` forces the notional to zero, ``capped``
    follows ``active`` to zero, and every lower row is at most zero, since
    ``fee_upper >= floor``. Order on, ``capped = 0``: the fee lies in
    ``[fixed + max(floor, rate * notional), fixed + fee_upper]``, which is
    non-empty exactly when ``rate * notional <= cap`` on a capped route.
    Order on, ``capped = 1``: the linear row asks at most ``fixed + cap``,
    because ``cap_excess = rate * notional_upper - cap``, so the fee is
    exactly ``fixed + cap``. The floor row holds on both branches, because
    ``ExactFeeSchedule`` validates ``floor <= cap``. The minimum over the
    branches is ``financial_math.fees.calculate_fee`` at every notional: ``explicit_cost``
    minimizes it, and the earlier stages (``fixed_l2``, ``shortfall``,
    ``route_priority``) feel the fee only through the ledger, where a higher
    fee never helps them.
    """
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
        fee_schedule = facts.fee_by_key[(route.broker_id, route.fee_schedule_id)]
        order_step = as_float(capability.order_step)
        decision = variables.quanta[exact_decision_id("buy_quantum", route.route_id)]
        active = variables.buy_active[route.route_id]
        fee = variables.buy_fee[route.route_id]

        measure = order_step * decision
        notional_expr = order_notional(facts, route, capability, measure)
        measure_upper = order_step * decision.getUbOriginal()
        notional_upper = order_notional(facts, route, capability, measure_upper)

        fixed = as_float(fee_schedule.fixed_fee.amount)
        rate = as_float(fee_schedule.proportional_rate)
        floor = as_float(fee_schedule.minimum_fee.amount)
        fee_upper = _fee_clamp_upper(fee_schedule, notional_upper)
        big_m = fixed + fee_upper

        model.addCons(fee <= (fixed + fee_upper) * active, name=f"fee_active_upper:{route.route_id}")
        model.addCons(fee >= fixed + floor - big_m * (1 - active), name=f"fee_floor:{route.route_id}")

        cap_relief: LinearTerm = 0.0
        cap_excess = _fee_cap_excess(fee_schedule, notional_upper)
        if fee_schedule.maximum_fee is not None and cap_excess is not None:
            cap = as_float(fee_schedule.maximum_fee.amount)
            capped = model.addVar(vtype="B", name=f"fee_capped:{route.route_id}")
            model.addCons(capped <= active, name=f"fee_capped_active:{route.route_id}")
            model.addCons(fee >= (fixed + cap) * capped, name=f"fee_cap:{route.route_id}")
            cap_relief = cap_excess * capped
        model.addCons(fee >= fixed + rate * notional_expr - big_m * (1 - active) - cap_relief, name=f"fee_linear:{route.route_id}")
