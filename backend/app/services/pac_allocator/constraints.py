"""Hard-constraint builders for the PAC/Rebalancer SCIP compiler (Step 3).

Scope for this build: PAC ``proportional`` policy, ``primary`` purpose only
(see ``plan-phase00Step3PacRebalancerSolverPolicies.prompt.md`` §16.6/§16.9).
SELL is always off for this policy, so every SELL-only ``ExactConstraintCode``
(``SELL_WITHIN_INVENTORY``, ``NO_ASSET_BUY_AND_SELL``, ``SELL_ELIGIBLE``, ...)
is out of scope by construction, not merely deferred.

Every ``ExactConstraintCode`` that ``evaluator.py`` enforces at replay time
falls into exactly one of three buckets here:

1. Already a ``DecisionAccess`` box bound (``lower_quanta``/``upper_quanta``)
   — ``compiler.py`` sets it directly on the SCIP variable; nothing to add
   here (``ORDER_CAP``, most of ``ORDER_QUANTIZED``'s effect, ``SELECTED_
   WITHIN_AVAILABLE``'s upstream precondition, disabled/frozen decisions).
2. A scenario-level precondition or accounting tautology, true by
   construction of the linear expressions this module and ``objectives.py``
   build — never a live SCIP row (``FUNDING_SOURCE_CONSERVATION``,
   ``NO_SELF_TRANSFER``, ``NO_DOUBLE_COUNT``, ``ORDER_QUANTIZED``,
   ``ORDER_SIDE_ALLOWED``, ``NO_IMPLICIT_ROUTE``, ``FX_RATE_ORDER_SAFE``,
   ``FX_NATIVE_QUANTUM``, ``ROUTE_DECLARED``,
   ``COST_NOT_INVESTMENT``, ``SELL_POSTED_ONCE``, ``ROUNDING_BOUND``,
   ``ACCOUNTING_IDENTITY``, ``REBALANCER_NONEMPTY`` — this last one is also
   simply inapplicable, ``scenario.product == "pac"`` here).
3. A genuine cross-decision or semi-continuous constraint a plain box bound
   cannot express — one ``model.addCons(...)`` call per instance:
   ``FUNDING_WITHIN_SELECTED`` (funding-source pooling),
   ``NO_SHORT_OR_LEVERAGE`` (Broker×currency ledger balance, folding in
   ``FX_SOURCE_CASH``'s spendable-cash floor), ``FX_CREDIT_POSITIVE`` (an
   active conversion posts a nonzero credit: the ``:active`` row of its
   posted credit, ``_posted_units_term``), ``ORDER_REQUIRED_MIN``
   (unconditional per-route floor), ``ORDER_MIN_IF_ACTIVE`` (semi-continuous:
   measure is either exactly zero or at least the active floor), and the
   fee epigraph (linearizes ``numeric.calculate_fee``'s ``fixed +
   clamp(rate * notional, floor, cap)`` for the ``explicit_cost`` objective).

The Decimal-exact replay via ``evaluate_exact_candidate`` is the only source
of truth for feasibility and for every reported number; this module's job is
only to keep the solver's search space close enough to the truth that a
floating incumbent survives replay. Every Big-M coefficient below is derived
from a route's own known finite bounds (``order_step * upper_quanta``) —
never an arbitrary constant, per Step3 §4's "Nessun Big-M arbitrario" rule.

Fee (``add_fee_epigraph_constraints``): for a nonzero order
``calculate_fee`` is ``fixed + clamp(rate * notional, floor, cap)``, three
pieces of the notional: flat at the floor, linear, flat at the cap. Under a
minimization, plain lower-bound rows represent the convex floor+linear part
exactly. The cap makes the function concave, so where it can bind within
the route's range (``_fee_cap_excess``: ``rate * notional_upper > cap``) a
``fee_capped`` binary picks the branch: the linear one, where the fee's
upper bound implies ``rate * notional <= cap``, or the flat one, where the
fee is exactly ``fixed + cap``. The minimal fee the model admits is then
``calculate_fee`` at every notional. The posted fee is debited in the cash
ledger, so this is also what lets the model reach the plans the exact
replay accepts.

Fee bound (``_fee_clamp_upper``): the fee variable of an active BUY route is
bounded by ``fixed + max(floor, min(rate * notional_upper, cap))``, in the
epigraph's Big-M and in the posted-fee units alike. Two defects found on
2026-09-24 shaped it:

- X2: the minimum belongs in the bound. With ``rate * notional_upper``
  alone, a minimum above it (a flat minimum on a zero rate, or a small
  route) left the floor row unsatisfiable, order on or off, and the whole
  model infeasible.
- QX1-a: the cap used to be ignored. The linear row priced a capped order
  at the uncapped fee and excluded plans the exact replay accepts (EUR50 050
  at EUR100 a unit, 0.19% capped at EUR18: the replay buys 500 units, the
  model stopped at 499). The cap enters the bound only together with its
  binary: with the linear row always on, a capped bound would make every
  order past the cap infeasible (at most 94 units in that example).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from backend.app.services.pac_allocator.evaluator import exact_decision_id
from backend.app.services.pac_allocator.ledger import (
    _ROUNDED_FAMILIES as LEDGER_ROUNDED_FAMILIES,  # single source of truth for which families are rounded
)
from backend.app.services.pac_allocator.models import (
    ExactFeeSchedule,
    ExactOrderCapability,
    ExactOrderRoute,
    ExactPlannerScenario,
)
from backend.app.services.pac_allocator.numeric import ExactRatio

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Expr, Model, Variable

    LinearTerm = float | Expr

__all__ = [
    "CompiledVariables",
    "LedgerPostingScopeError",
    "ScenarioFacts",
    "add_fee_epigraph_constraints",
    "add_funding_activation_constraints",
    "add_funding_pool_constraints",
    "add_ledger_balance_constraints",
    "add_order_activation_constraints",
    "add_order_required_minimum_constraints",
    "build_scenario_facts",
    "buy_pool_currencies",
    "compile_hard_constraints",
    "fx_rate",
    "order_notional",
    "order_prices",
    "planning_fx_rate",
    "valuation_rate",
]


def as_float(value: ExactRatio) -> float:
    """Project one exact rational to a float for the floating SCIP model.

    Only ever used to *search*; every candidate the solver proposes is
    replayed through ``evaluate_exact_candidate`` (pure ``ExactRatio``) before
    it is trusted, so this projection cannot leak into a reported number.
    """
    return value.numerator / value.denominator


@dataclass(frozen=True, slots=True)
class ScenarioFacts:
    """Pure, decision-independent scenario facts, derived only from public
    ``ExactPlannerScenario`` fields (deliberately not ``evaluator.py``'s
    private ``_ScenarioIndex`` — see Step3 §16.9 for why: this module must
    stay buildable without reaching into another module's internals).
    """

    valuation_currency: str
    currency_quantum: dict[str, float]
    fx_rate_by_pair: dict[str, float]
    fx_spread_rate: float
    assets_by_id: dict[str, str]  # asset_id -> quote currency (all this module needs of an Asset)
    mid_native_by_asset: dict[str, float]
    capability_by_key: dict[tuple[str, str], ExactOrderCapability]
    fee_by_key: dict[tuple[str, str], ExactFeeSchedule]


def _fx_pair_key(first: str, second: str) -> str:
    return "/".join(sorted((first, second)))


def fx_rate(facts: ScenarioFacts, source_currency: str, destination_currency: str) -> float:
    """Return units of ``destination_currency`` per unit of ``source_currency``.

    Mirrors ``evaluator._fx_rate`` exactly (same direct-pair-or-inverse
    lookup over the same alphabetically-ordered pair keys) but is re-derived
    here from the public ``ScenarioFacts.fx_rate_by_pair`` rather than
    imported, since the evaluator's version is a private helper.
    """
    if source_currency == destination_currency:
        return 1.0
    rate = facts.fx_rate_by_pair.get(_fx_pair_key(source_currency, destination_currency))
    if rate is None:
        raise KeyError(f"missing direct FX rate for {source_currency}/{destination_currency}")
    return rate if source_currency < destination_currency else 1.0 / rate


def valuation_rate(facts: ScenarioFacts, currency: str) -> float:
    """Units of the scenario's valuation currency per unit of ``currency``."""
    return fx_rate(facts, currency, facts.valuation_currency)


def planning_fx_rate(facts: ScenarioFacts, source_currency: str, destination_currency: str) -> float:
    """Mirror ``numeric.calculate_planning_fx_rate``: the spread rate, capped
    at the triangle through the valuation currency.
    """
    effective_rate = fx_rate(facts, source_currency, destination_currency) * (1.0 - facts.fx_spread_rate)
    return min(effective_rate, valuation_rate(facts, source_currency) / valuation_rate(facts, destination_currency))


def order_prices(facts: ScenarioFacts, route: ExactOrderRoute) -> tuple[float, float]:
    """Return ``(mid_native, execution_native)`` for one order route.

    Mirrors ``evaluator._order_prices``: the execution side applies the
    route's own margin against the Asset's scenario-constant mid price.
    """
    mid_native = facts.mid_native_by_asset[route.asset_id]
    margin = as_float(route.execution_margin_rate)
    execution_native = mid_native * (1.0 + margin) if route.side == "buy" else mid_native * (1.0 - margin)
    return mid_native, execution_native


def order_notional(facts: ScenarioFacts, route: ExactOrderRoute, capability: ExactOrderCapability, measure: LinearTerm) -> LinearTerm:
    """Return the fee-schedule ``notional`` (always quote-currency cash) for
    ``measure = order_step * decision_quanta``, mirroring the ``exact_cash``
    branch evaluator.py's ``_evaluate_orders`` computes per capability kind.
    """
    if capability.kind == "whole_quantity":
        _, execution_native = order_prices(facts, route)
        return measure * execution_native
    return measure


def build_scenario_facts(scenario: ExactPlannerScenario) -> ScenarioFacts:
    fx_rate_by_pair = {item.pair_key: as_float(item.rate) for item in scenario.fx_rates}
    currency_quantum = {item.currency: as_float(item.minor_unit) for item in scenario.currency_specs}
    assets_by_id = {asset.asset_id: asset.quote.price.currency for asset in scenario.assets}
    mid_native_by_asset = {asset.asset_id: as_float(asset.quote.price.amount) / as_float(asset.quote.quote_base_quantity) for asset in scenario.assets}
    capability_by_key: dict[tuple[str, str], ExactOrderCapability] = {}
    fee_by_key: dict[tuple[str, str], ExactFeeSchedule] = {}
    for broker in scenario.brokers:
        for capability in broker.capabilities:
            capability_by_key[(broker.broker_id, capability.capability_id)] = capability
        for fee in broker.fee_schedules:
            fee_by_key[(broker.broker_id, fee.fee_schedule_id)] = fee
    return ScenarioFacts(
        valuation_currency=scenario.valuation_currency,
        currency_quantum=currency_quantum,
        fx_rate_by_pair=fx_rate_by_pair,
        fx_spread_rate=as_float(scenario.fx_spread_rate),
        assets_by_id=assets_by_id,
        mid_native_by_asset=mid_native_by_asset,
        capability_by_key=capability_by_key,
        fee_by_key=fee_by_key,
    )


def buy_pool_currencies(scenario: ExactPlannerScenario, facts: ScenarioFacts, *, broker_id: str, quote_currency: str) -> tuple[str, ...]:
    """Mirror ``evaluator._buy_pool_currencies`` exactly: currencies that hold
    (or can hold) cash at ``broker_id`` and have a direct FX pair to
    ``quote_currency`` — anti-cascade, one hop only.
    """
    candidates: set[str] = set()
    for cash in scenario.existing_cash:
        if cash.broker_id == broker_id:
            candidates.add(cash.selected.currency)
    for route in scenario.funding_routes:
        if route.broker_id == broker_id:
            candidates.add(route.currency)
    for other in scenario.order_routes:
        if other.broker_id == broker_id and other.side == "sell":
            candidates.add(facts.assets_by_id[other.asset_id])
    candidates.discard(quote_currency)
    return tuple(sorted(currency for currency in candidates if _fx_pair_key(currency, quote_currency) in facts.fx_rate_by_pair))


@dataclass(frozen=True, slots=True)
class CompiledVariables:
    """All SCIP decision variables, keyed for both constraint and objective builders."""

    quanta: dict[str, Variable]  # decision_id -> integer var, every DecisionAccess row
    buy_active: dict[str, Variable]  # buy order_route_id -> binary var
    funding_active: dict[str, Variable]  # funding route_id -> binary var
    buy_fee: dict[str, Variable]  # buy order_route_id -> continuous fee var (quote currency), every buy route


def _minimum_value(route: ExactOrderRoute, field: str) -> float:
    # ``ExactOrderMinimum.__post_init__`` already forces ``value == 0`` when
    # ``kind == "none"``, so the raw value is always the right magnitude to
    # compare against ``measure`` directly, exactly as evaluator.py does.
    return as_float(getattr(route, field).value)


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


# --------------------------------------------------------------------------
# Ledger postings, rounded against the plan (Step3 §16.11)
# --------------------------------------------------------------------------


class LedgerPostingScopeError(ValueError):
    """Raised when this module cannot model a scenario's ledger postings
    faithfully: an unmodelled rounded family would actually be posted, or a
    family exists in ``ledger.py`` that we have no detector for. Always a
    loud failure, never a silent exact-expression fallback — that silent
    degradation is precisely what caused the Step3 §16.11 defect.
    """


# The rounded families this module actually builds SCIP terms for. PAC
# ``proportional`` never posts the four SELL/tax families, but that is a
# property of today's scope, not of this module — hence the guard below
# rather than an assumption.
_MODELLED_ROUNDED_FAMILIES: frozenset[str] = frozenset({"fx_credit", "buy_debit", "buy_fee"})


def _scenario_posts_buy(scenario: ExactPlannerScenario, facts: ScenarioFacts) -> bool:
    return any(route.side == "buy" for route in scenario.order_routes)


def _scenario_posts_sell(scenario: ExactPlannerScenario, facts: ScenarioFacts) -> bool:
    return any(route.side == "sell" for route in scenario.order_routes)


def _scenario_posts_fx_credit(scenario: ExactPlannerScenario, facts: ScenarioFacts) -> bool:
    return any(route.side == "buy" and buy_pool_currencies(scenario, facts, broker_id=route.broker_id, quote_currency=facts.assets_by_id[route.asset_id]) for route in scenario.order_routes)


# One detector per rounded family in ``ledger.py``. Keyed so that a family
# added there without a detector here trips ``_require_modelled_rounded_families``
# immediately instead of being silently ignored.
_ROUNDED_FAMILY_DETECTORS = {
    "fx_credit": _scenario_posts_fx_credit,
    "buy_debit": _scenario_posts_buy,
    "buy_fee": _scenario_posts_buy,
    "gross_sell_credit": _scenario_posts_sell,
    "sell_fee": _scenario_posts_sell,
    "broker_withheld_tax": _scenario_posts_sell,
    "self_reserved_tax": _scenario_posts_sell,
}


def _require_modelled_rounded_families(scenario: ExactPlannerScenario, facts: ScenarioFacts) -> None:
    """Fail closed rather than degrade silently.

    Two distinct ways to be wrong, both errors: (1) ``ledger.py`` grew a
    rounded family we cannot even detect, so we cannot know whether this
    scenario posts it; (2) this scenario really does post a rounded family we
    do not model, which would otherwise be summed as an exact expression and
    reintroduce the §16.11 defect in a surface nobody is watching.
    """
    undetectable = set(LEDGER_ROUNDED_FAMILIES) - set(_ROUNDED_FAMILY_DETECTORS)
    if undetectable:
        raise LedgerPostingScopeError(f"ledger.py declares rounded posting families with no detector here: {sorted(undetectable)}; add a detector before compiling any scenario")
    posted = {family for family, detect in _ROUNDED_FAMILY_DETECTORS.items() if family in LEDGER_ROUNDED_FAMILIES and detect(scenario, facts)}
    unmodelled = posted - _MODELLED_ROUNDED_FAMILIES
    if unmodelled:
        raise LedgerPostingScopeError(f"this {scenario.product}/{scenario.policy} scenario posts rounded ledger families this build does not model: {sorted(unmodelled)}")


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


def _posted_units_term(
    model: Model,
    *,
    name: str,
    exact_expr: LinearTerm,
    quantum: float,
    exact_upper: float,
    side: Literal["credit", "debit"],
    active_decision: Variable | None = None,
) -> LinearTerm:
    """Return the **posted** amount of one rounded ledger family, rounded
    against the plan, as ``quantum * units`` for a fresh integer ``units``.

    A credit (``fx_credit``) posts ``floor(exact/quantum)`` units and a debit
    (``buy_debit``, ``buy_fee``) ``ceil(exact/quantum)``, as
    ``ledger._PLAN_ROUNDING`` does, encoded by the non-strict pairs

        credit:  quantum*units <= exact <= quantum*units + quantum
        debit:   quantum*units - quantum <= exact <= quantum*units

    Deliberately **non-strict**. The textbook encoding closes the open edge
    with a small epsilon, but calibrating such an epsilon is itself a
    correctness risk: below SCIP's ``numerics/feastol`` it is absorbed
    anyway, and above the smallest achievable-value-to-multiple separation it
    excludes reachable points — over-pruning, the failure class these posted
    terms exist to remove. The non-strict pair has no epsilon to calibrate
    and is satisfiable for *every* real ``exact``, so it can never prune. Its
    only looseness is at an exact multiple of the quantum, where ``units``
    may also sit one quantum against the plan: one less for a credit, one
    more for a debit. A credit enters every ledger row with a ``+`` sign, a
    debit with a ``-`` sign, and neither appears in an objective, so a
    decision is feasible with some ``units`` exactly when it is feasible with
    the true posting: up to SCIP's feasibility tolerance, the model's feasible
    set is the exact one. The Decimal-exact replay referees that tolerance; a
    point it moves surfaces as a rejection or a top-up, never as a plan.

    ``active_decision`` (FX credits only) adds the ``:active`` row
    ``decision <= upper * units``, ``FX_CREDIT_POSITIVE``: an active
    conversion must post a nonzero credit. The rounding rows alone admit
    ``units = 0`` for any credit below one quantum; with this row such a
    conversion is infeasible, while a credit of at least one quantum keeps its
    true floor ``>= 1`` and is never pruned.

    Every family routed here is a non-negative magnitude by construction (a
    notional over a non-negative measure, a fee variable with ``lb=0``, an FX
    credit over a non-negative debit). The ``:nonneg`` row below *enforces*
    that rather than assuming it, so a future negative-capable flow fails
    loudly instead of being posted by a rule nobody checked.
    """
    units_upper = math.ceil(exact_upper / quantum) + 1
    units = model.addVar(vtype="I", lb=0, ub=units_upper, name=name)
    model.addCons(exact_expr >= 0.0, name=f"{name}:nonneg")
    if side == "credit":
        model.addCons(quantum * units <= exact_expr, name=f"{name}:lo")
        model.addCons(exact_expr <= quantum * units + quantum, name=f"{name}:hi")
    else:
        model.addCons(quantum * units - quantum <= exact_expr, name=f"{name}:lo")
        model.addCons(exact_expr <= quantum * units, name=f"{name}:hi")
    if active_decision is not None:
        model.addCons(active_decision <= active_decision.getUbOriginal() * units, name=f"{name}:active")
    return quantum * units


def add_ledger_balance_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """``NO_SHORT_OR_LEVERAGE`` folding in ``FX_SOURCE_CASH``: every
    Broker×currency ledger cell's final spendable balance must stay >= 0.

    Mirrors ``ledger.reconcile_broker_ledgers``'s
    ``final_spendable = initial_selected + funding_in + fx_credit +
    gross_sell_credit - funding_out - fx_debit - buy_debit - buy_fee -
    sell_fee - broker_withheld_tax - self_reserved_tax`` with every SELL-only
    term at its always-zero value for PAC ``proportional`` (SELL is always
    off): ``gross_sell_credit = sell_fee = broker_withheld_tax =
    self_reserved_tax = 0``.

    **The cell sums POSTED amounts, not exact ones.** ``ledger.py``'s
    ``_ROUNDED_FAMILIES`` are posted to the currency quantum against the plan
    (``ledger.rounded_money_posting``: ``numeric.post_floor`` for a credit,
    ``numeric.post_ceiling`` for a debit), so
    ``fx_credit``/``buy_debit``/``buy_fee`` enter through
    ``_posted_units_term`` rather than as their exact expressions. Summing
    exact amounts here was a real defect (Step3 §16.11): under the HALF_UP
    rule of the time a 9.504 USD exact FX credit posted as 10 USD, and
    treating it as 9.504 wrongly pruned the true optimum; under the floor it
    posts 9, and 9.504 would admit plans the replay rejects.
    ``initial_selected``/``funding_in``/``funding_out``/``fx_debit``
    are exact-flow families (``ledger.py``'s ``_EXACT_FLOW_FAMILIES``) and are
    summed unrounded, which is correct.
    """
    _require_modelled_rounded_families(scenario, facts)
    cells: dict[tuple[str, str], list[LinearTerm]] = defaultdict(list)

    for cash in scenario.existing_cash:
        cells[(cash.broker_id, cash.selected.currency)].append(as_float(cash.selected.amount))

    for route in scenario.funding_routes:
        amount_expr = facts.currency_quantum[route.currency] * variables.quanta[exact_decision_id("funding_transfer", route.route_id)]
        cells[(route.broker_id, route.currency)].append(amount_expr)
        source_cell = _source_cash_cell(scenario, route.source_kind, route.source_id)
        if source_cell is not None:
            cells[source_cell].append(-amount_expr)

    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        quote_currency = facts.assets_by_id[route.asset_id]
        quote_quantum = facts.currency_quantum[quote_currency]
        capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
        order_step = as_float(capability.order_step)
        decision = variables.quanta[exact_decision_id("buy_quantum", route.route_id)]
        measure = order_step * decision
        notional_expr = order_notional(facts, route, capability, measure)
        notional_upper = order_notional(facts, route, capability, order_step * decision.getUbOriginal())

        cells[(route.broker_id, quote_currency)].append(
            -_posted_units_term(
                model,
                name=f"posted_buy_debit:{route.route_id}",
                exact_expr=notional_expr,
                quantum=quote_quantum,
                exact_upper=notional_upper,
                side="debit",
            )
        )
        fee_upper = _fee_variable_upper(facts, route, capability, notional_upper)
        cells[(route.broker_id, quote_currency)].append(
            -_posted_units_term(
                model,
                name=f"posted_buy_fee:{route.route_id}",
                exact_expr=variables.buy_fee[route.route_id],
                quantum=quote_quantum,
                exact_upper=fee_upper,
                side="debit",
            )
        )

        for pool_currency in buy_pool_currencies(scenario, facts, broker_id=route.broker_id, quote_currency=quote_currency):
            # f"{route_id}:{currency}" mirrors evaluator._fx_debit_key exactly (private helper, re-derived not imported).
            fx_decision = variables.quanta[exact_decision_id("fx_debit", f"{route.route_id}:{pool_currency}")]
            debit_expr = facts.currency_quantum[pool_currency] * fx_decision
            cells[(route.broker_id, pool_currency)].append(-debit_expr)
            effective_rate = planning_fx_rate(facts, pool_currency, quote_currency)
            credit_upper = facts.currency_quantum[pool_currency] * fx_decision.getUbOriginal() * effective_rate
            cells[(route.broker_id, quote_currency)].append(
                _posted_units_term(
                    model,
                    name=f"posted_fx_credit:{route.route_id}:{pool_currency}",
                    exact_expr=debit_expr * effective_rate,
                    quantum=quote_quantum,
                    exact_upper=credit_upper,
                    side="credit",
                    active_decision=fx_decision,
                )
            )

    for (broker_id, currency), terms in cells.items():
        model.addCons(sum(terms) >= 0, name=f"ledger_nonnegative:{broker_id}:{currency}")


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


def add_fee_epigraph_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """Linearize ``numeric.calculate_fee``'s ``0 if notional==0 else fixed +
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
    branches is ``calculate_fee`` at every notional: ``explicit_cost``
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


def compile_hard_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """Add every real cross-decision / semi-continuous constraint for one
    PAC ``proportional`` ``primary`` scenario. Box bounds are set on the
    variables themselves by ``compiler.py`` before this is called.
    """
    add_funding_pool_constraints(model, scenario, facts, variables)
    add_ledger_balance_constraints(model, scenario, facts, variables)
    add_order_required_minimum_constraints(model, scenario, facts, variables)
    add_order_activation_constraints(model, scenario, facts, variables)
    add_funding_activation_constraints(model, scenario, facts, variables)
    add_fee_epigraph_constraints(model, scenario, facts, variables)
