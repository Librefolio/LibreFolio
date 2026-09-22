"""Objective-stage builders for the PAC/Rebalancer SCIP compiler (Step 3).

Scope: PAC ``proportional`` policy, ``primary`` purpose only — the same
scope as ``constraints.py`` (see that module's docstring and Step3
§16.6/§16.9). Builds the exact cascade evaluator.py's ``_objective_value_map``
uses for this purpose, confirmed from ``_build_objective_refs``/
``_objective_codes``:

    fixed_l2 -> shortfall -> route_priority -> explicit_cost -> active_order_rows

followed by the canonical tie-break vector (``view.tie_breaks[0].decision_ids``,
read directly off the view rather than re-derived, per the same
public-contract-only discipline as ``oracle.py``).

Each builder returns an ``ObjectiveStage`` (a name plus the linear/quadratic
SCIP expression to *minimize* for that stage). The actual lexicographic
re-optimization loop (solve stage N, pin its optimum, move to stage N+1) is
``solver.py``'s job (Step3 Stage 3) — this module only produces the ordered
list of stage expressions, mirroring ``_objective_value_map``'s formulas one
for one so that a stage's SCIP-reported value and the Decimal-exact replay
value agree up to the float/exact projection error.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints import (
    CompiledVariables,
    ScenarioFacts,
    as_float,
    buy_pool_currencies,
    fx_rate,
    order_notional,
    order_prices,
    valuation_rate,
)
from backend.app.services.pac_allocator.evaluator import exact_decision_id
from backend.app.services.pac_allocator.models import ExactOrderRoute, ExactPlannerScenario, ExactPolicyView

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Expr, Model

    LinearTerm = float | Expr

__all__ = [
    "ObjectiveInputs",
    "ObjectiveStage",
    "build_active_order_rows_stage",
    "build_canonical_tie_stages",
    "build_explicit_cost_stage",
    "build_fixed_l2_stage",
    "build_objective_cascade",
    "build_route_priority_stage",
    "build_shortfall_stage",
    "compute_objective_inputs",
]


@dataclass(frozen=True, slots=True)
class ObjectiveStage:
    """One cascade stage: minimize ``expression`` before moving to the next."""

    code: str
    expression: LinearTerm


@dataclass(frozen=True, slots=True)
class ObjectiveInputs:
    """Decision-independent constants the cascade needs, both read off a
    single all-zero-candidate probe evaluation (``compiler.py``'s job to
    obtain, via the public ``evaluate_exact_candidate`` — never re-derived,
    since ``fixed_reference``/``target_value`` depend on ``_can_reach_buy``/
    ``_source_reachability``, private reachability algorithms this module
    must not duplicate).
    """

    target_value_by_asset: dict[str, float]
    fixed_reference: float


def _buy_measure_expr(facts: ScenarioFacts, variables: CompiledVariables, route: ExactOrderRoute) -> LinearTerm:
    capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
    order_step = as_float(capability.order_step)
    decision = variables.quanta[exact_decision_id("buy_quantum", route.route_id)]
    return order_step * decision


def _buy_mid_value_expr(facts: ScenarioFacts, route: ExactOrderRoute, measure: LinearTerm) -> LinearTerm:
    """Mirrors evaluator.py's ``native_mid_value`` -> ``mid_value`` (valuation
    currency) chain for one BUY route, as a function of its own ``measure``.
    """
    capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
    mid_native, execution_native = order_prices(facts, route)
    if capability.kind == "whole_quantity":
        native_mid_value = measure * mid_native
    else:
        native_mid_value = measure * (mid_native / execution_native)
    quote_currency = facts.assets_by_id[route.asset_id]
    return native_mid_value * valuation_rate(facts, quote_currency)


def compute_objective_inputs(target_value_by_asset: dict[str, float], fixed_reference: float) -> ObjectiveInputs:
    return ObjectiveInputs(target_value_by_asset=dict(target_value_by_asset), fixed_reference=fixed_reference)


def build_fixed_l2_stage(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs) -> ObjectiveStage:
    """``fixed_l2 = sum((final_value_a - target_value_a)^2)`` (PAC has no
    holdings, so ``final_value_a`` reduces to the sum of this Asset's own BUY
    ``mid_value`` contributions). One continuous epigraph variable per Asset:
    the square of a real number is always convex, so — unlike the fee cap in
    ``constraints.py`` — a plain ``>=`` epigraph row is exact here, not an
    approximation: minimizing pushes ``residual_sq_a`` down to precisely
    ``residual_a**2`` at optimality.
    """
    buy_value_by_asset: dict[str, LinearTerm] = defaultdict(float)
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        measure = _buy_measure_expr(facts, variables, route)
        buy_value_by_asset[route.asset_id] = buy_value_by_asset[route.asset_id] + _buy_mid_value_expr(facts, route, measure)

    total: LinearTerm = 0.0
    for asset_id, target_value in inputs.target_value_by_asset.items():
        residual_expr = buy_value_by_asset[asset_id] - target_value
        residual_sq = model.addVar(vtype="C", lb=0.0, name=f"residual_sq:{asset_id}")
        model.addCons(residual_sq >= residual_expr**2, name=f"fixed_l2_epigraph:{asset_id}")
        total = total + residual_sq
    return ObjectiveStage(code="fixed_l2", expression=total)


def build_shortfall_stage(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs) -> ObjectiveStage:
    """``shortfall = fixed_reference - final_invested``; ``fixed_reference``
    is the decision-independent probe constant, ``final_invested`` is the
    sum of every Asset's ``final_value`` (same BUY ``mid_value`` sum as
    ``fixed_l2`` — recomputed here rather than threaded through, since each
    stage builder must stay independently readable and cheap to re-derive).
    """
    final_invested: LinearTerm = 0.0
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        measure = _buy_measure_expr(facts, variables, route)
        final_invested = final_invested + _buy_mid_value_expr(facts, route, measure)
    return ObjectiveStage(code="shortfall", expression=inputs.fixed_reference - final_invested)


def build_route_priority_stage(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs) -> ObjectiveStage:
    """``route_priority = sum(funding priority * active) + sum(order priority
    * active)`` — evaluator.py only sums priority for routes whose transfer/
    order actually posted a nonzero amount (``_evaluate_funding``/
    ``_evaluate_orders`` both skip zero-amount rows), which is exactly what
    ``funding_active``/``buy_active`` represent.
    """
    total: LinearTerm = 0.0
    for route in scenario.funding_routes:
        total = total + route.priority * variables.funding_active[route.route_id]
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        total = total + route.priority * variables.buy_active[route.route_id]
    return ObjectiveStage(code="route_priority", expression=total)


def build_explicit_cost_stage(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs) -> ObjectiveStage:
    """``explicit_cost = buy_fees + fx_spread_loss + execution_margin_loss``
    (SELL-only terms are always zero for PAC ``proportional``), all three
    valued in the scenario's valuation currency, mirroring
    ``_evaluate_costs`` exactly.
    """
    total: LinearTerm = 0.0
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        quote_currency = facts.assets_by_id[route.asset_id]
        quote_valuation_rate = valuation_rate(facts, quote_currency)
        capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
        measure = _buy_measure_expr(facts, variables, route)
        notional_expr = order_notional(facts, route, capability, measure)

        total = total + variables.buy_fee[route.route_id] * quote_valuation_rate

        mid_native, execution_native = order_prices(facts, route)
        if capability.kind == "whole_quantity":
            native_mid_value = measure * mid_native
        else:
            native_mid_value = measure * (mid_native / execution_native)
        execution_margin_loss = (notional_expr - native_mid_value) * quote_valuation_rate
        total = total + execution_margin_loss

        for pool_currency in _buy_pool_currencies_for_route(scenario, facts, route, quote_currency):
            # f"{route_id}:{currency}" mirrors evaluator._fx_debit_key exactly (private helper, re-derived not imported).
            fx_decision = variables.quanta[exact_decision_id("fx_debit", f"{route.route_id}:{pool_currency}")]
            debit_expr = facts.currency_quantum[pool_currency] * fx_decision
            effective_rate = _fx_effective_rate(facts, pool_currency, quote_currency)
            credit_expr = debit_expr * effective_rate
            spread_loss = debit_expr * valuation_rate(facts, pool_currency) - credit_expr * quote_valuation_rate
            total = total + spread_loss
    return ObjectiveStage(code="explicit_cost", expression=total)


def _fx_effective_rate(facts: ScenarioFacts, source_currency: str, destination_currency: str) -> float:
    return fx_rate(facts, source_currency, destination_currency) * (1.0 - facts.fx_spread_rate)


def _buy_pool_currencies_for_route(scenario: ExactPlannerScenario, facts: ScenarioFacts, route: ExactOrderRoute, quote_currency: str) -> tuple[str, ...]:
    return buy_pool_currencies(scenario, facts, broker_id=route.broker_id, quote_currency=quote_currency)


def build_active_order_rows_stage(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs) -> ObjectiveStage:
    """``active_order_rows = len(state.orders)`` = count of BUY routes with a
    nonzero decision, i.e. the sum of every ``buy_active`` binary.
    """
    total: LinearTerm = 0.0
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        total = total + variables.buy_active[route.route_id]
    return ObjectiveStage(code="active_order_rows", expression=total)


def build_canonical_tie_stages(variables: CompiledVariables, view: ExactPolicyView) -> list[ObjectiveStage]:
    """One trivial ``minimize quanta[decision_id]`` stage per entry of
    ``view.tie_breaks[0].decision_ids``, in that exact order — the single
    canonical tie-break vector confirmed to be the view's only
    ``TieBreakRef`` (ordinal 1). Read directly from the view rather than
    re-derived, for maximum robustness/consistency with evaluator.py.
    """
    return [ObjectiveStage(code=f"tie:{decision_id}", expression=variables.quanta[decision_id]) for decision_id in view.tie_breaks[0].decision_ids]


def build_objective_cascade(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs, view: ExactPolicyView) -> list[ObjectiveStage]:
    """Return the complete ordered cascade for PAC ``proportional``
    ``primary``: the 5 named stages, then the canonical tie-break vector.
    """
    stages = [
        build_fixed_l2_stage(model, scenario, facts, variables, inputs),
        build_shortfall_stage(model, scenario, facts, variables, inputs),
        build_route_priority_stage(model, scenario, facts, variables, inputs),
        build_explicit_cost_stage(model, scenario, facts, variables, inputs),
        build_active_order_rows_stage(model, scenario, facts, variables, inputs),
    ]
    stages.extend(build_canonical_tie_stages(variables, view))
    return stages
