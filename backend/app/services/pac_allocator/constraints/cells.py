"""The ledger cells: every Broker x currency balance must stay non-negative, summing the amounts the ledger POSTS (rounded
against the plan), and the guard that fails closed on a rounded family this build does not model.
"""

from __future__ import annotations

import math
from collections import defaultdict
from fractions import Fraction
from typing import TYPE_CHECKING, Literal

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts, as_float, order_notional, planning_fx_rate
from backend.app.services.pac_allocator.constraints.fees import _fee_variable_upper
from backend.app.services.pac_allocator.constraints.funding import _source_cash_cell
from backend.app.services.pac_allocator.evaluation.bounds import transfer_decision_id
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id
from backend.app.services.pac_allocator.evaluation.reachability import fx_decision_specs
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, fx_rate, order_prices, valuation_rate_of
from backend.app.services.pac_allocator.ledger import (
    _ROUNDED_FAMILIES as LEDGER_ROUNDED_FAMILIES,  # single source of truth for which families are rounded
)
from backend.app.services.pac_allocator.models import ExactPlannerScenario
from backend.app.services.pac_allocator.numeric import ExactRatio, calculate_planning_fx_rate

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model, Variable

    from backend.app.services.pac_allocator.constraints.facts import LinearTerm


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
    return bool(facts.fx_decisions)


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


def _exact_gap(generators: tuple[ExactRatio, ...], quantum: ExactRatio) -> float:
    """The smallest positive distance between an exact amount and a multiple of ``quantum``, from the data (P5).

    The exact amount of a posting is an integer combination of ``generators`` (a route's step, a fee's parts, a conversion's
    rate times the source quantum), so ``exact − quantum·units`` lives on the lattice of their rational gcd with the quantum:
    when it is not zero it is at least that gcd.

    No threshold, however fine the gcd (the B2 review, 1(c)): EUR → USD at 1.085 with a 1 % spread steps by 1/2 000 000 of a
    dollar, the common case for an FX credit. A tightened row cannot prune a true point: its slack is ``>= 0`` exactly, and the
    float error of the row is far below SCIP's feasibility tolerance.
    """
    values = [Fraction(abs(item.numerator), item.denominator) for item in (*generators, quantum) if item.numerator != 0]
    gap = values[0]
    for value in values[1:]:
        gap = Fraction(math.gcd(gap.numerator * value.denominator, value.numerator * gap.denominator), gap.denominator * value.denominator)
    return float(gap)


def _posted_units_term(
    model: Model,
    *,
    name: str,
    exact_expr: LinearTerm,
    quantum: float,
    exact_upper: float,
    side: Literal["credit", "debit"],
    active_decision: Variable | None = None,
    gap: float | None = None,
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
    debit with a ``-`` sign, and in the PAC neither appears in an objective, so a
    decision is feasible with some ``units`` exactly when it is feasible with
    the true posting (in the Rebalancer they do, in ``F − W``: see ``gap``): up to SCIP's feasibility tolerance, the model's feasible
    set is the exact one. The Decimal-exact replay referees that tolerance; a
    point it moves surfaces as a rejection or a top-up, never as a plan.

    ``gap`` (the Rebalancer only, B2 of project 67): the pair becomes strict, exactly. In the PAC nothing gains from a posting
    one unit against the plan; in the Rebalancer the distance does, when a cash cell with a target holds more than its target
    (lowering its cash shortens ``D``). With ``gap`` the far row is ``quantum*units <= exact + quantum - gap`` for a debit and
    ``exact <= quantum*units + quantum - gap`` for a credit: no epsilon, since every amount ``exact - quantum*units`` that is
    not zero is at least ``gap`` (``_exact_gap``), and ``units`` is the true posting.

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
    far = quantum if gap is None else quantum - gap
    if side == "credit":
        model.addCons(quantum * units <= exact_expr, name=f"{name}:lo")
        model.addCons(exact_expr <= quantum * units + far, name=f"{name}:hi")
    else:
        model.addCons(quantum * units - far <= exact_expr, name=f"{name}:lo")
        model.addCons(exact_expr <= quantum * units, name=f"{name}:hi")
    if active_decision is not None:
        model.addCons(active_decision <= active_decision.getUbOriginal() * units, name=f"{name}:active")
    return quantum * units


def add_ledger_balance_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> dict[tuple[str, str], list[LinearTerm]]:
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
    Returns the terms of every cell (A3: V5 on cash reads the same sums), by (Broker, currency).

    ``initial_selected``/``funding_in``/``funding_out``/``fx_debit``
    are exact-flow families (``ledger.py``'s ``_EXACT_FLOW_FAMILIES``) and are
    summed unrounded, which is correct.
    """
    _require_modelled_rounded_families(scenario, facts)
    cells: dict[tuple[str, str], list[LinearTerm]] = defaultdict(list)
    gaps = _rebalancer_posting_gaps(scenario) if scenario.product == "rebalancer" else {}

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
                gap=gaps.get(("buy_debit", route.route_id)),
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
                gap=gaps.get(("buy_fee", route.route_id)),
            )
        )

    for spec in facts.fx_decisions:
        fx_decision = variables.quanta[spec.decision_id]
        debit_expr = facts.currency_quantum[spec.source_currency] * fx_decision
        cells[(spec.broker_id, spec.source_currency)].append(-debit_expr)
        effective_rate = planning_fx_rate(facts, spec.source_currency, spec.destination_currency)
        credit_upper = facts.currency_quantum[spec.source_currency] * fx_decision.getUbOriginal() * effective_rate
        cells[(spec.broker_id, spec.destination_currency)].append(
            _posted_units_term(
                model,
                name=f"posted_fx_credit:{spec.key}",
                exact_expr=debit_expr * effective_rate,
                quantum=facts.currency_quantum[spec.destination_currency],
                exact_upper=credit_upper,
                side="credit",
                active_decision=fx_decision,
                gap=gaps.get(("fx_credit", spec.decision_id)),
            )
        )

    # Transfers between Brokers (A2): exact flows, as funding is, out of the source cell and into the destination cell.
    for lane in scenario.transfer_lanes:
        moved = facts.currency_quantum[lane.currency] * variables.quanta[transfer_decision_id(lane)]
        cells[(lane.source_broker_id, lane.currency)].append(-moved)
        cells[(lane.destination_broker_id, lane.currency)].append(moved)

    for (broker_id, currency), terms in cells.items():
        model.addCons(sum(terms) >= 0, name=f"ledger_nonnegative:{broker_id}:{currency}")
    return cells


def _rebalancer_posting_gaps(scenario: ExactPlannerScenario) -> dict[tuple[str, str], float]:
    """The exact gap of every rounded posting of a Rebalancer scenario (``_exact_gap``), keyed by family and route or decision.

    * a buy debit is ``step`` times the quanta (an amount route) or ``step`` units at the execution price;
    * a buy fee is zero or ``fixed`` plus one of ``floor``, ``rate`` times the notional, ``cap``;
    * an FX credit is the source quantum times the quanta times the planning rate.
    """
    index = build_scenario_index(scenario)
    gaps: dict[tuple[str, str], float] = {}
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        capability = index.capabilities[(route.broker_id, route.capability_id)]
        fee = index.fees[(route.broker_id, route.fee_schedule_id)]
        quantum = index.currency_quantum[index.assets[route.asset_id].quote.price.currency]
        step = capability.order_step if capability.kind == "monetary_amount" else capability.order_step * order_prices(index, route).execution_native
        gaps[("buy_debit", route.route_id)] = _exact_gap((step,), quantum)
        fee_parts = (fee.fixed_fee.amount, fee.minimum_fee.amount, fee.proportional_rate * step, *((fee.maximum_fee.amount,) if fee.maximum_fee is not None else ()))
        gaps[("buy_fee", route.route_id)] = _exact_gap(fee_parts, quantum)
    for spec in fx_decision_specs(scenario, index, None):
        rate = calculate_planning_fx_rate(
            approved_rate=fx_rate(index.fx_rate_by_pair, spec.source_currency, spec.destination_currency),
            spread=scenario.fx_spread_rate,
            source_valuation_rate=valuation_rate_of(index, spec.source_currency),
            destination_valuation_rate=valuation_rate_of(index, spec.destination_currency),
        )
        gaps[("fx_credit", spec.decision_id)] = _exact_gap((index.currency_quantum[spec.source_currency] * rate,), index.currency_quantum[spec.destination_currency])
    return gaps
