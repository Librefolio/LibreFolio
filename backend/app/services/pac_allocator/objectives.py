"""Objective-stage builders for the PAC/Rebalancer SCIP compiler (Step 3).

The Rebalancer (B2 of project 67) has its own cascade, built from the same probe: one score ``J`` (SCIP minimizes
``λ·D + F·C``, the stage's ``scale`` is ``F``) or the «Target first» chain ``D`` then ``C``, then ``operation_count``,
``route_priority`` and the canonical vector as tie-breaks (``_rebalancer_cascade``). What follows describes the PAC's.

Scope: PAC ``proportional`` policy, ``primary`` purpose only — the same
scope as the ``constraints`` package (see that module's docstring and Step3
§16.6/§16.9). Builds the exact cascade ``evaluation/facts.py``'s ``objective_value_map``
uses for this purpose, confirmed from ``evaluation/references.py``'s ``build_objective_refs``/
``_objective_codes``:

    fixed_l2 -> shortfall -> route_priority -> explicit_cost -> active_order_rows

followed by the canonical tie-break vector (``view.tie_breaks[0].decision_ids``,
read directly off the view rather than re-derived, per the same
public-contract-only discipline as the exhaustive oracle of the test tree).

Each builder returns an ``ObjectiveStage`` (a name plus the linear/quadratic
SCIP expression to *minimize* for that stage). The actual lexicographic
re-optimization loop (solve stage N, pin its optimum, move to stage N+1) is
``solver.py``'s job (Step3 Stage 3) — this module only produces the ordered
list of stage expressions, mirroring ``objective_value_map``'s formulas one
for one so that a stage's SCIP-reported value and the Decimal-exact replay
value agree up to the float/exact projection error.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints import (
    CompiledVariables,
    ScenarioFacts,
    order_notional,
    order_prices,
    planning_fx_rate,
    valuation_rate,
)
from backend.app.services.pac_allocator.constraints.facts import as_float, asset_final_value_exprs, buy_measure_expr, buy_mid_value_expr
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id
from backend.app.services.pac_allocator.models import ExactPlannerScenario, ExactPolicyView, ExactTargetFidelity

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


# SCIP checks a nonlinear row ``residual_sq >= residual**2`` with an ABSOLUTE tolerance (numerics/feastol, 1e-6): each row
# can sit that much below the truth. A stage declares its band from its own rows (D3 of the step-2 plan of project 67).
_QUADRATIC_ROW_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class ObjectiveStage:
    """One cascade stage: minimize ``expression`` before moving to the next.

    ``scale``: SCIP minimizes ``scale ×`` the exact value of the view's objective (D2 of the step-2 plan of project 67): the
    Rebalancer's ``plan_score`` is ``J`` in euros at scale 1 (``λ·D/F + C``), and «Target first»'s ``target_distance`` is
    ``D`` at scale ``1/F`` (lot S1: the residuals are written over ``√F``). ``band``: how far below the truth the stage's
    value may sit because of its quadratic rows, in SCIP's units (D3). ``integral``: the expression takes only whole values,
    so it is pinned exactly. ``tie_break``: a plan found at this stage replaces the best one only if the objectives before
    it are no worse in exact arithmetic (D4).
    """

    code: str
    expression: LinearTerm
    scale: Fraction = Fraction(1)
    band: float = 0.0
    integral: bool = False
    tie_break: bool = False


@dataclass(frozen=True, slots=True)
class ObjectiveInputs:
    """Decision-independent constants the cascade needs, both read off a
    single all-zero-candidate probe evaluation (``compiler.py``'s job to
    obtain, via the public ``evaluate_exact_candidate`` — never re-derived,
    since ``fixed_reference``/``target_value`` depend on ``_can_reach_buy``/
    ``source_reachability`` (``evaluation/reachability.py``), reachability algorithms
    internal to the evaluator that this module must not duplicate).
    """

    target_value_by_asset: dict[str, float]
    fixed_reference: float
    # The Rebalancer (B2 of project 67), from the same probe: F exactly, the target of every cash cell that has one, and the
    # fidelity. The PAC leaves them empty.
    initial_wealth: Fraction = Fraction(0)
    # ``R`` (lot SLIP, ``evaluation.limits.plan_reference``): the targets' base, the uninvested ``N`` and the distance's scale.
    # ``F`` in the Rebalancer; ``initial_wealth`` keeps ``F`` for the money lost ``C = F − W``.
    reference: Fraction = Fraction(0)
    cash_target_by_cell: dict[tuple[str, str], float] = field(default_factory=dict)
    fidelity: ExactTargetFidelity | None = None


def compute_objective_inputs(target_value_by_asset: dict[str, float], fixed_reference: float, **rebalancer) -> ObjectiveInputs:
    return ObjectiveInputs(target_value_by_asset=dict(target_value_by_asset), fixed_reference=fixed_reference, **rebalancer)


def build_fixed_l2_stage(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs) -> ObjectiveStage:
    """``fixed_l2 = sum((final_value_a - target_value_a)^2)`` (PAC has no
    holdings, so ``final_value_a`` reduces to the sum of this Asset's own BUY
    ``mid_value`` contributions). One continuous epigraph variable per Asset:
    the square of a real number is always convex, so — unlike the fee cap in
    ``constraints`` — a plain ``>=`` epigraph row is exact here, not an
    approximation: minimizing pushes ``residual_sq_a`` down to precisely
    ``residual_a**2`` at optimality.
    """
    buy_value_by_asset: dict[str, LinearTerm] = defaultdict(float)
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        measure = buy_measure_expr(facts, variables, route)
        buy_value_by_asset[route.asset_id] = buy_value_by_asset[route.asset_id] + buy_mid_value_expr(facts, route, measure)

    total: LinearTerm = 0.0
    for asset_id, target_value in inputs.target_value_by_asset.items():
        residual_expr = buy_value_by_asset[asset_id] - target_value
        residual_sq = model.addVar(vtype="C", lb=0.0, name=f"residual_sq:{asset_id}")
        model.addCons(residual_sq >= residual_expr**2, name=f"fixed_l2_epigraph:{asset_id}")
        total = total + residual_sq
    return ObjectiveStage(code="fixed_l2", expression=total, band=len(scenario.target_weights) * _QUADRATIC_ROW_TOLERANCE)


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
        measure = buy_measure_expr(facts, variables, route)
        final_invested = final_invested + buy_mid_value_expr(facts, route, measure)
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
    return ObjectiveStage(code="route_priority", expression=total, integral=True)


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
        measure = buy_measure_expr(facts, variables, route)
        notional_expr = order_notional(facts, route, capability, measure)

        total = total + variables.buy_fee[route.route_id] * quote_valuation_rate

        mid_native, execution_native = order_prices(facts, route)
        if capability.kind == "whole_quantity":
            native_mid_value = measure * mid_native
        else:
            native_mid_value = measure * (mid_native / execution_native)
        execution_margin_loss = (notional_expr - native_mid_value) * quote_valuation_rate
        total = total + execution_margin_loss
    for spec in facts.fx_decisions:
        debit_expr = facts.currency_quantum[spec.source_currency] * variables.quanta[spec.decision_id]
        credit_expr = debit_expr * planning_fx_rate(facts, spec.source_currency, spec.destination_currency)
        spread_loss = debit_expr * valuation_rate(facts, spec.source_currency) - credit_expr * valuation_rate(facts, spec.destination_currency)
        total = total + spread_loss
    return ObjectiveStage(code="explicit_cost", expression=total)


def build_active_order_rows_stage(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs) -> ObjectiveStage:
    """``active_order_rows = len(state.orders)`` = count of BUY routes with a
    nonzero decision, i.e. the sum of every ``buy_active`` binary.
    """
    total: LinearTerm = 0.0
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        total = total + variables.buy_active[route.route_id]
    return ObjectiveStage(code="active_order_rows", expression=total, integral=True)


def build_canonical_tie_stages(variables: CompiledVariables, view: ExactPolicyView) -> list[ObjectiveStage]:
    """One trivial ``minimize quanta[decision_id]`` stage per entry of
    ``view.tie_breaks[0].decision_ids``, in that exact order — the single
    canonical tie-break vector confirmed to be the view's only
    ``TieBreakRef`` (ordinal 1). Read directly from the view rather than
    re-derived, for maximum robustness/consistency with evaluator.py.

    A Rebalancer lane is held at zero in SCIP (lot CR of project 67): its stage minimizes what the lane's source cell sends,
    which is the lane's amount when two Brokers share the currency, and otherwise never less than it.
    """
    sent_by_lane = variables.pool.sent_by_lane if variables.pool is not None else {}
    return [ObjectiveStage(code=f"tie:{decision_id}", expression=sent_by_lane.get(decision_id, variables.quanta[decision_id]), integral=True) for decision_id in view.tie_breaks[0].decision_ids]


@dataclass(frozen=True, slots=True)
class _RebalancerParts:
    """The Rebalancer's terms in SCIP (specifica §5-§6), each the float mirror of ``evaluation/facts._rebalancer_score``."""

    distance: LinearTerm  # D/F: sum of the epigraph variables of every residual over √F (lot S1)
    distance_rows: int
    wealth_loss: LinearTerm  # C = F - W


def _rebalancer_parts(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs, cells: dict) -> _RebalancerParts:
    """``D``, and ``C = F − W``, as SCIP expressions over the decisions.

    Every Asset is worth ``V⁰`` plus its buys (``asset_final_value_exprs``). A cash cell is worth the sum of its POSTED terms
    (``add_ledger_balance_constraints``): the same amounts the replay's ledger posts, rounded against the plan. ``W`` is the
    Assets, every cell, and the contributions no route deposited; ``N`` is ``F`` less the Assets and the cells with a
    target. ``D`` squares each residual through one epigraph variable: the square is convex, so minimizing pushes each
    variable down to the square itself.

    Lot S1 of project 67 (the consultant's diagnosis of G5): each residual first goes into a variable of its own,
    ``r = residual / √F``, and the epigraph squares ``r``. Squared as a long sum, SCIP expanded the row into pairwise
    products of integer variables, and its cuts on them deduced a false bound at node 1. Over ``√F`` the squares are
    already euros of ``J``: the returned ``distance`` is ``D/F``, and the score is ``λ·D/F + C`` at scale 1.

    Lot SLIP: ``N`` and the scale read ``R`` (``inputs.reference``), which is ``F`` in the Rebalancer; ``C`` keeps ``F``.
    """
    initial_wealth = float(inputs.initial_wealth)
    reference = float(inputs.reference)
    asset_values = asset_final_value_exprs(scenario, facts, variables)
    cell_values = {key: sum(terms) * valuation_rate(facts, key[1]) for key, terms in cells.items()}
    targeted = {key: cell_values.get(key, 0.0) for key in inputs.cash_target_by_cell}
    residuals: list[tuple[str, LinearTerm]] = [(f"asset:{asset_id}", asset_values[asset_id] - inputs.target_value_by_asset[asset_id]) for asset_id in sorted(asset_values)]
    residuals += [(f"cash:{broker_id}:{currency}", targeted[(broker_id, currency)] - target) for (broker_id, currency), target in sorted(inputs.cash_target_by_cell.items())]
    residuals.append(("uninvested", reference - sum(asset_values.values()) - sum(targeted.values())))
    over_root = 1.0 / math.sqrt(reference) if reference > 0 else 1.0
    distance: LinearTerm = 0.0
    for name, residual in residuals:
        scaled = model.addVar(vtype="C", lb=None, ub=None, name=f"distance_res:{name}")
        model.addCons(scaled == residual * over_root, name=f"distance_residual:{name}")
        squared = model.addVar(vtype="C", lb=0.0, name=f"distance_sq:{name}")
        model.addCons(squared >= scaled**2, name=f"distance_epigraph:{name}")
        distance = distance + squared
    undeposited: LinearTerm = sum(as_float(item.amount.amount) * valuation_rate(facts, item.amount.currency) for item in scenario.contributions)
    for route in scenario.funding_routes:
        if route.source_kind == "contribution":
            moved = facts.currency_quantum[route.currency] * variables.quanta[exact_decision_id("funding_transfer", route.route_id)]
            undeposited = undeposited - moved * valuation_rate(facts, route.currency)
    final_wealth = sum(asset_values.values()) + sum(cell_values.values()) + undeposited
    return _RebalancerParts(distance=distance, distance_rows=len(residuals), wealth_loss=initial_wealth - final_wealth)


def build_operation_count_stage(scenario: ExactPlannerScenario, variables: CompiledVariables) -> ObjectiveStage:
    """``operation_count`` (specifica §6.4): orders, deposits, conversions and transfers, each through its activity binary.

    The transfers come from the cash rule's balances (lot CR of project 67): per currency, the cells that move less one, the
    number of transfers ``pool.derive_transfer_quanta`` makes from them (one when two Brokers share the currency).
    """
    binaries = (*variables.buy_active.values(), *variables.funding_active.values(), *variables.fx_active.values())
    expression = sum(binaries, 0.0)
    if variables.pool is not None:
        expression = expression + sum(variables.pool.active.values(), 0.0) - sum(variables.pool.moving.values(), 0.0)
    return ObjectiveStage(code="operation_count", expression=expression, integral=True, tie_break=True)


def _over(wealth: Fraction) -> Fraction:
    """``1/F``, the scale of a stage SCIP sees over ``F``; 1 for an empty portfolio, where nothing is scaled."""
    return 1 / wealth if wealth > 0 else Fraction(1)


def _rebalancer_cascade(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, inputs: ObjectiveInputs, view: ExactPolicyView, cells: dict) -> list[ObjectiveStage]:
    """The Rebalancer's cascade (B2 of project 67), in the order of the view: one score, or the «Target first» chain, then
    the tie-breaks, which choose only among plans no worse on what precedes them (D4)."""
    parts = _rebalancer_parts(model, scenario, facts, variables, inputs, cells)
    fidelity = inputs.fidelity
    if fidelity is not None and fidelity.kind == "target_first":
        stages = [
            # SCIP minimizes D/F (lot S1); the exact value of the stage is D.
            ObjectiveStage(code="target_distance", expression=parts.distance, scale=_over(inputs.reference), band=parts.distance_rows * _QUADRATIC_ROW_TOLERANCE),
            ObjectiveStage(code="wealth_loss", expression=parts.wealth_loss),
        ]
    else:
        weight = as_float(fidelity.distance_weight) if fidelity is not None else 1.0
        stages = [
            ObjectiveStage(
                code="plan_score",
                # J in euros, as the replay counts it (lot S1): λ·D/F + C, at scale 1.
                expression=weight * parts.distance + parts.wealth_loss,
                band=weight * parts.distance_rows * _QUADRATIC_ROW_TOLERANCE,
            )
        ]
    priority = build_route_priority_stage(model, scenario, facts, variables, inputs)
    stages += [build_operation_count_stage(scenario, variables), ObjectiveStage(code=priority.code, expression=priority.expression, integral=True, tie_break=True)]
    stages += [ObjectiveStage(code=stage.code, expression=stage.expression, integral=True, tie_break=True) for stage in build_canonical_tie_stages(variables, view)]
    return stages


def build_objective_cascade(
    model: Model,
    scenario: ExactPlannerScenario,
    facts: ScenarioFacts,
    variables: CompiledVariables,
    inputs: ObjectiveInputs,
    view: ExactPolicyView,
    cells: dict | None = None,
) -> list[ObjectiveStage]:
    """Return the complete ordered cascade of the ``primary`` view: the PAC's five named stages, or the Rebalancer's, then
    the canonical tie-break vector.
    """
    if scenario.product == "rebalancer":
        return _rebalancer_cascade(model, scenario, facts, variables, inputs, view, cells or {})
    stages = [
        build_fixed_l2_stage(model, scenario, facts, variables, inputs),
        build_shortfall_stage(model, scenario, facts, variables, inputs),
        build_route_priority_stage(model, scenario, facts, variables, inputs),
        build_explicit_cost_stage(model, scenario, facts, variables, inputs),
        build_active_order_rows_stage(model, scenario, facts, variables, inputs),
    ]
    stages.extend(build_canonical_tie_stages(variables, view))
    return stages
