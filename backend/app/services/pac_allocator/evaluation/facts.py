"""Constraint facts and objective values of a replayed candidate: the value, the bounds and the outcome of every rule, and the score of every objective."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from backend.app.services.pac_allocator.evaluation.economics import EconomicState, evaluate_economic_state
from backend.app.services.pac_allocator.evaluation.errors import ExactPolicyContractError
from backend.app.services.pac_allocator.evaluation.keys import asset_broker_key, exact_decision_id, is_quantum_multiple
from backend.app.services.pac_allocator.evaluation.limits import resolve_scenario_limits
from backend.app.services.pac_allocator.evaluation.reachability import fx_decision_specs, fx_relay_groups
from backend.app.services.pac_allocator.evaluation.references import ledger_keys
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex, fx_rate, order_prices, source_broker, to_valuation, valuation_rate_of
from backend.app.services.pac_allocator.ledger import (
    rounded_money_posting,
)
from backend.app.services.pac_allocator.models import (
    Checkpoint,
    DecisionFamily,
    ExactBrokerLedgerEvaluation,
    ExactObjectiveCode,
    ExactOrderRoute,
    ExactPlannerScenario,
    ExactPolicyView,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
    calculate_fx_credit,
)

_EXACT_ZERO = ExactRatio(0)
_EXACT_ONE = ExactRatio(1)


@dataclass(frozen=True, slots=True)
class _ConstraintFact:
    value: ExactRatio
    lower_bound: ExactRatio | None
    upper_bound: ExactRatio | None
    satisfied: bool


def _bool_fact(satisfied: bool) -> _ConstraintFact:
    return _ConstraintFact(
        value=_EXACT_ONE if satisfied else _EXACT_ZERO,
        lower_bound=_EXACT_ONE,
        upper_bound=_EXACT_ONE,
        satisfied=satisfied,
    )


def _constraint_id(code: str, key: str) -> str:
    return f"constraint:{code.lower()}:{key}"


def _minimum_value(route: ExactOrderRoute, field: str) -> ExactRatio:
    minimum = getattr(route, field)
    return minimum.value


def _funding_constraint_facts(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    quanta: Mapping[str, int],
    state: EconomicState,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts: dict[str, _ConstraintFact] = {}
    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        facts[
            _constraint_id(
                "SELECTED_WITHIN_AVAILABLE",
                f"existing_cash:{cash.cash_id}",
            )
        ] = _ConstraintFact(
            value=cash.selected.amount,
            lower_bound=_EXACT_ZERO,
            upper_bound=cash.available.amount,
            satisfied=cash.selected.amount <= cash.available.amount,
        )
    for source in state.funding_sources:
        check_budget(checkpoint)
        key = f"{source.source_kind}:{source.source_id}"
        facts[_constraint_id("FUNDING_WITHIN_SELECTED", key)] = _ConstraintFact(
            value=source.transferred,
            lower_bound=_EXACT_ZERO,
            upper_bound=source.selected,
            satisfied=source.transferred <= source.selected,
        )
        conservation_delta = source.selected - source.transferred - source.remaining
        facts[_constraint_id("FUNDING_SOURCE_CONSERVATION", key)] = _ConstraintFact(
            value=conservation_delta,
            lower_bound=_EXACT_ZERO,
            upper_bound=_EXACT_ZERO,
            satisfied=conservation_delta == _EXACT_ZERO,
        )
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        decision_id = exact_decision_id(
            "funding_transfer",
            route.route_id,
        )
        amount = index.currency_quantum[route.currency] * quanta[decision_id]
        source_broker_id = source_broker(
            index,
            route.source_kind,
            route.source_id,
        )
        self_transfer = source_broker_id is not None and source_broker_id == route.broker_id
        facts[_constraint_id("NO_SELF_TRANSFER", route.route_id)] = _ConstraintFact(
            value=amount if self_transfer else _EXACT_ZERO,
            lower_bound=_EXACT_ZERO,
            upper_bound=_EXACT_ZERO,
            satisfied=not self_transfer or amount == _EXACT_ZERO,
        )
    source_conservation = all(item.selected == item.transferred + item.remaining for item in state.funding_sources)
    facts[_constraint_id("NO_DOUBLE_COUNT", "global")] = _bool_fact(source_conservation)
    return facts


def _fx_constraint_facts(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    state: EconomicState,
    ledger_rows: Mapping[
        tuple[str, str],
        ExactBrokerLedgerEvaluation,
    ],
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts: dict[str, _ConstraintFact] = {}
    fx_actions = {item.decision_id: item for item in state.fx}
    for spec in fx_decision_specs(scenario, index, checkpoint):
        check_budget(checkpoint)
        currency, quote_currency, key = spec.source_currency, spec.destination_currency, spec.key
        action = fx_actions.get(spec.decision_id)
        source_debit = action.source_debit if action is not None else _EXACT_ZERO
        exact_credit = action.exact_destination_credit if action is not None else _EXACT_ZERO
        posted_credit = action.posted_destination_credit if action is not None else _EXACT_ZERO
        approved_rate = fx_rate(index.fx_rate_by_pair, currency, quote_currency)
        expected_exact = calculate_fx_credit(
            source_debit=source_debit,
            approved_rate=approved_rate,
            spread=scenario.fx_spread_rate,
            source_valuation_rate=valuation_rate_of(index, currency),
            destination_valuation_rate=valuation_rate_of(index, quote_currency),
        )
        expected_posted = (
            rounded_money_posting(
                posting_id="constraint-only",
                family="fx_credit",
                broker_id=spec.broker_id,
                currency=quote_currency,
                exact_amount=expected_exact,
                quantum=index.currency_quantum[quote_currency],
            ).posted_amount
            if expected_exact != _EXACT_ZERO
            else _EXACT_ZERO
        )
        coupling_delta = posted_credit - expected_posted
        facts[_constraint_id("FX_DEBIT_CREDIT_COUPLED", key)] = _ConstraintFact(
            value=coupling_delta,
            lower_bound=_EXACT_ZERO,
            upper_bound=_EXACT_ZERO,
            satisfied=(exact_credit == expected_exact and coupling_delta == _EXACT_ZERO),
        )
        facts[_constraint_id("FX_CREDIT_POSITIVE", key)] = _ConstraintFact(
            value=posted_credit,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=(action is None or posted_credit > _EXACT_ZERO),
        )
        native_quantized = is_quantum_multiple(
            source_debit,
            index.currency_quantum[currency],
        )
        facts[_constraint_id("FX_NATIVE_QUANTUM", key)] = _ConstraintFact(
            value=source_debit,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=native_quantized,
        )
        source_ledger = ledger_rows[(spec.broker_id, currency)]
        facts[_constraint_id("FX_SOURCE_CASH", key)] = _ConstraintFact(
            value=source_ledger.final_spendable,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=source_ledger.final_spendable >= _EXACT_ZERO,
        )
    return facts


def _fx_relay_constraint_facts(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    state: EconomicState,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    """V7: on a Broker a currency that receives a conversion does not give one (``FX_NO_RELAY``).

    The fact counts the sides in use, 0 to 2: some conversion into the currency, some conversion out of it. A relay, one of each,
    burns cash and no optimum needs it: the planning rate never beats the triangle, credits are floored, and a buy is never paid
    through a chain. Converting back and forth in one pair is the shortest relay.
    """
    active = {item.decision_id for item in state.fx if item.quanta > 0}
    facts: dict[str, _ConstraintFact] = {}
    for group in fx_relay_groups(fx_decision_specs(scenario, index, checkpoint)):
        check_budget(checkpoint)
        sides = ExactRatio(sum(1 for side in (group.receiving, group.giving) if any(spec.decision_id in active for spec in side)))
        facts[_constraint_id("FX_NO_RELAY", group.key)] = _ConstraintFact(value=sides, lower_bound=_EXACT_ZERO, upper_bound=ExactRatio(1), satisfied=sides <= ExactRatio(1))
    return facts


def _limit_constraint_facts(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    state: EconomicState,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    """V5 for every limited entry (A3), on limits resolved against ``fixed_reference``.

    The final value of an Asset is ``ExactAssetEvaluation.final_value``; of a cash cell, its final spendable cash valued in
    the valuation currency. A violation is never a rounding deficit: the code is not among the four ``evaluator`` accepts for a
    top-up (D9). There is no cap on «uninvested» cash: fees a plan has to pay are not uninvested, and a cash maximum on a
    cell already says how much may be left in it.
    """
    facts: dict[str, _ConstraintFact] = {}
    resolved = resolve_scenario_limits(scenario, state.accounting.fixed_reference)
    final_value = {item.asset_id: item.final_value for item in state.assets}
    final_cash = {(row.broker_id, row.currency): to_valuation(index, row.final_spendable, row.currency) for row in state.ledgers}
    for entry, bounds in resolved.by_entry.items():
        check_budget(checkpoint)
        value = final_value[entry.asset_id] if entry.kind == "asset" else final_cash[(entry.broker_id, entry.currency)]
        satisfied = (bounds.minimum is None or value >= bounds.minimum) and (bounds.maximum is None or value <= bounds.maximum)
        contradictory = bounds.minimum is not None and bounds.maximum is not None and bounds.minimum > bounds.maximum
        # A minimum above its maximum is refused before the calculation (``limits.check_minimum_above_maximum``); a replay that
        # meets one anyway reports it unsatisfiable, and publishes the minimum alone: a fact's bounds must be ordered.
        facts[_constraint_id("ENTRY_VALUE_WITHIN_LIMITS", entry.key)] = _ConstraintFact(
            value=value,
            lower_bound=bounds.minimum,
            upper_bound=None if contradictory else bounds.maximum,
            satisfied=satisfied and not contradictory,
        )
    return facts


def _order_route_constraint_facts(
    *,
    route: ExactOrderRoute,
    index: ScenarioIndex,
    quanta: Mapping[str, int],
) -> dict[str, _ConstraintFact]:
    capability = index.capabilities[(route.broker_id, route.capability_id)]
    family: DecisionFamily = "buy_quantum" if route.side == "buy" else "sell_quantum"
    decision_quanta = quanta[exact_decision_id(family, route.route_id)]
    measure = capability.order_step * decision_quanta
    active = decision_quanta > 0
    active_floor = max(
        capability.order_step,
        _minimum_value(route, "minimum_if_active"),
    )
    prices = order_prices(index, route)
    price_order_safe = prices.mid_native <= prices.execution_native if route.side == "buy" else prices.execution_native <= prices.mid_native
    return {
        _constraint_id(
            "ORDER_QUANTIZED",
            route.route_id,
        ): _ConstraintFact(
            value=measure,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=is_quantum_multiple(
                measure,
                capability.order_step,
            ),
        ),
        _constraint_id(
            "ORDER_MIN_IF_ACTIVE",
            route.route_id,
        ): _ConstraintFact(
            value=measure,
            lower_bound=active_floor if active else _EXACT_ZERO,
            upper_bound=None,
            satisfied=not active or measure >= active_floor,
        ),
        _constraint_id("ORDER_CAP", route.route_id): _ConstraintFact(
            value=measure,
            lower_bound=_EXACT_ZERO,
            upper_bound=route.cap.value if route.cap is not None else None,
            satisfied=route.cap is None or measure <= route.cap.value,
        ),
        _constraint_id(
            "ORDER_SIDE_ALLOWED",
            route.route_id,
        ): _bool_fact((route.side == "buy" and family == "buy_quantum") or (route.side == "sell" and family == "sell_quantum")),
        _constraint_id(
            "NO_IMPLICIT_ROUTE",
            route.route_id,
        ): _bool_fact(True),
        _constraint_id(
            "FX_RATE_ORDER_SAFE",
            route.route_id,
        ): _bool_fact(price_order_safe),
    }


def _order_constraint_facts(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    quanta: Mapping[str, int],
    state: EconomicState,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts = {}
    actions = {item.route_id: item for item in state.orders}
    for route in scenario.order_routes:
        check_budget(checkpoint)
        facts.update(
            _order_route_constraint_facts(
                route=route,
                index=index,
                quanta=quanta,
            )
        )
        if route.side == "sell":
            action = actions.get(route.route_id)
            net = action.posted_cash_amount - action.posted_fee - action.posted_tax_reserve if action is not None else _EXACT_ZERO
            facts[
                _constraint_id(
                    "SELL_NET_POSITIVE",
                    route.route_id,
                )
            ] = _ConstraintFact(
                value=net,
                lower_bound=_EXACT_ZERO,
                upper_bound=None,
                satisfied=action is None or net > _EXACT_ZERO,
            )
        else:
            action = actions.get(route.route_id)
            posted_debit = action.posted_cash_amount if action is not None else _EXACT_ZERO
            facts[
                _constraint_id(
                    "BUY_DEBIT_POSITIVE",
                    route.route_id,
                )
            ] = _ConstraintFact(
                value=posted_debit,
                lower_bound=_EXACT_ZERO,
                upper_bound=None,
                satisfied=(action is None or posted_debit > _EXACT_ZERO),
            )
    return facts


def _position_constraint_facts(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    state: EconomicState,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts = {}
    ledger_rows = {(item.broker_id, item.currency): item for item in state.ledgers}
    for broker_id, currency in ledger_keys(scenario, index):
        check_budget(checkpoint)
        row = ledger_rows[(broker_id, currency)]
        key = f"{broker_id}:{currency}"
        facts[_constraint_id("SPENDABLE_CASH_NONNEGATIVE", key)] = _ConstraintFact(
            value=row.final_spendable,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=row.final_spendable >= _EXACT_ZERO,
        )
        physical_delta = row.final_physical - row.final_spendable - row.self_reserved_tax
        facts[_constraint_id("PHYSICAL_CASH_RECONCILED", key)] = _ConstraintFact(
            value=physical_delta,
            lower_bound=_EXACT_ZERO,
            upper_bound=_EXACT_ZERO,
            satisfied=physical_delta == _EXACT_ZERO,
        )
    for holding in state.holdings:
        check_budget(checkpoint)
        constraint_key = asset_broker_key(holding.asset_id, holding.broker_id)
        facts[
            _constraint_id(
                "FINAL_QUANTITY_NONNEGATIVE",
                constraint_key,
            )
        ] = _ConstraintFact(
            value=holding.final_quantity,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=holding.final_quantity >= _EXACT_ZERO,
        )
        facts[_constraint_id("SELL_WITHIN_INVENTORY", constraint_key)] = _ConstraintFact(
            value=holding.sell_quantity,
            lower_bound=_EXACT_ZERO,
            upper_bound=(holding.initial_quantity + holding.buy_quantity),
            satisfied=(holding.sell_quantity <= holding.initial_quantity + holding.buy_quantity),
        )
    asset_rows = {item.asset_id: item for item in state.assets}
    for asset in scenario.assets:
        check_budget(checkpoint)
        result = asset_rows[asset.asset_id]
        buy_active = any(order.asset_id == asset.asset_id and order.side == "buy" for order in state.orders)
        sell_active = any(order.asset_id == asset.asset_id and order.side == "sell" for order in state.orders)
        facts[
            _constraint_id(
                "FINAL_VALUE_NONNEGATIVE",
                asset.asset_id,
            )
        ] = _ConstraintFact(
            value=result.final_value,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=result.final_value >= _EXACT_ZERO,
        )
        facts[
            _constraint_id(
                "NO_ASSET_BUY_AND_SELL",
                asset.asset_id,
            )
        ] = _bool_fact(not (buy_active and sell_active))
    return facts


def _global_constraint_facts(  # noqa: C901 — flat sequential global facts, each scan threaded with an explicit checkpoint budget check
    scenario: ExactPlannerScenario,
    state: EconomicState,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts = {
        _constraint_id(
            "ROUTE_DECLARED",
            "global",
        ): _bool_fact(True)
    }
    asset_reconciliation = True
    for item in state.assets:
        check_budget(checkpoint)
        if item.final_value != item.current_value + item.buy_mid_value - item.sell_mid_value:
            asset_reconciliation = False
    facts[_constraint_id("COST_NOT_INVESTMENT", "global")] = _bool_fact(asset_reconciliation)
    expected_sell_postings: set[str] = set()
    for order in state.orders:
        check_budget(checkpoint)
        if order.side == "sell" and order.exact_cash_amount != _EXACT_ZERO:
            expected_sell_postings.add(f"gross-sell-credit:{order.route_id}")
    posting_ids: list[str] = []
    actual_sell_postings: set[str] = set()
    for item in state.postings:
        check_budget(checkpoint)
        posting_ids.append(item.posting_id)
        if item.family == "gross_sell_credit":
            actual_sell_postings.add(item.posting_id)
    sell_posted_once = len(posting_ids) == len(set(posting_ids)) and expected_sell_postings == actual_sell_postings
    facts[_constraint_id("SELL_POSTED_ONCE", "global")] = _bool_fact(sell_posted_once)
    rounding_within = abs(state.accounting.rounding_adjustment) <= state.accounting.rounding_bound and state.accounting.shortfall >= -state.accounting.rounding_bound
    facts[_constraint_id("ROUNDING_BOUND", "global")] = _ConstraintFact(
        value=abs(state.accounting.rounding_adjustment),
        lower_bound=_EXACT_ZERO,
        upper_bound=state.accounting.rounding_bound,
        satisfied=rounding_within,
    )
    facts[_constraint_id("ACCOUNTING_IDENTITY", "global")] = _ConstraintFact(
        value=state.accounting.identity_delta,
        lower_bound=_EXACT_ZERO,
        upper_bound=_EXACT_ZERO,
        satisfied=(state.accounting.identity_delta == _EXACT_ZERO),
    )
    no_short_or_leverage = True
    for row in state.ledgers:
        check_budget(checkpoint)
        if row.final_spendable < _EXACT_ZERO:
            no_short_or_leverage = False
    for row in state.holdings:
        check_budget(checkpoint)
        if row.final_quantity < _EXACT_ZERO:
            no_short_or_leverage = False
    facts[_constraint_id("NO_SHORT_OR_LEVERAGE", "global")] = _bool_fact(no_short_or_leverage)
    if scenario.product == "rebalancer":
        rebalancer_nonempty = state.accounting.current_invested > _EXACT_ZERO and state.accounting.final_invested > _EXACT_ZERO
        facts[_constraint_id("REBALANCER_NONEMPTY", "global")] = _ConstraintFact(
            value=state.accounting.final_invested,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=rebalancer_nonempty,
        )
    return facts


def _sell_extension_constraint_facts(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    view: ExactPolicyView,
    quanta: Mapping[str, int],
    state: EconomicState,
    baseline_state: EconomicState | None,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    if baseline_state is None:
        raise ExactPolicyContractError("SELL extension constraints require baseline facts")
    facts = {}
    baseline_assets = {item.asset_id: item for item in baseline_state.assets}
    baseline_buy_assets = {order.asset_id for order in baseline_state.orders if order.side == "buy"}
    active_order_ids = {order.route_id for order in state.orders}
    for route in scenario.order_routes:
        if route.side != "sell":
            continue
        check_budget(checkpoint)
        eligible = baseline_assets[route.asset_id].residual > _EXACT_ZERO and route.asset_id not in baseline_buy_assets
        facts[_constraint_id("SELL_ELIGIBLE", route.route_id)] = _bool_fact(route.route_id not in active_order_ids or eligible)
    sell_active = any(order.side == "sell" for order in state.orders)
    incremental_buy = any(item.family == "buy_quantum" and quanta[item.decision_id] > item.baseline_quanta for item in view.decisions)
    no_sell_fundable = True
    if sell_active:
        no_sell_quanta = dict(quanta)
        for item in view.decisions:
            check_budget(checkpoint)
            if item.family == "sell_quantum":
                no_sell_quanta[item.decision_id] = 0
        no_sell_state = evaluate_economic_state(
            scenario,
            index,
            no_sell_quanta,
            checkpoint,
        )
        no_sell_fundable = all(row.final_spendable >= _EXACT_ZERO for row in no_sell_state.ledgers)
    facts[
        _constraint_id(
            "SELL_FUNDS_INCREMENTAL_BUY",
            "global",
        )
    ] = _bool_fact(not sell_active or (incremental_buy and not no_sell_fundable))
    return facts


def constraint_facts(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    view: ExactPolicyView,
    quanta: Mapping[str, int],
    state: EconomicState,
    baseline_state: EconomicState | None,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts = _funding_constraint_facts(
        scenario,
        index,
        quanta,
        state,
        checkpoint,
    )
    ledger_rows = {(item.broker_id, item.currency): item for item in state.ledgers}
    facts.update(
        _fx_constraint_facts(
            scenario=scenario,
            index=index,
            state=state,
            ledger_rows=ledger_rows,
            checkpoint=checkpoint,
        )
    )
    facts.update(_fx_relay_constraint_facts(scenario=scenario, index=index, state=state, checkpoint=checkpoint))
    facts.update(_limit_constraint_facts(scenario=scenario, index=index, state=state, checkpoint=checkpoint))
    facts.update(
        _order_constraint_facts(
            scenario,
            index,
            quanta,
            state,
            checkpoint,
        )
    )
    facts.update(
        _position_constraint_facts(
            scenario,
            index,
            state,
            checkpoint,
        )
    )
    facts.update(_global_constraint_facts(scenario, state, checkpoint))
    if view.purpose == "sell_extension":
        facts.update(
            _sell_extension_constraint_facts(
                scenario=scenario,
                index=index,
                view=view,
                quanta=quanta,
                state=state,
                baseline_state=baseline_state,
                checkpoint=checkpoint,
            )
        )
    return facts


def objective_value_map(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    view: ExactPolicyView,
    quanta: Mapping[str, int],
    state: EconomicState,
    baseline_state: EconomicState | None,
    checkpoint: Checkpoint | None,
) -> dict[ExactObjectiveCode, ExactRatio]:
    fixed_l2 = sum(
        (asset.residual.square() for asset in state.assets),
        _EXACT_ZERO,
    )
    turnover = sum(
        (order.mid_value for order in state.orders),
        _EXACT_ZERO,
    )
    active_order_rows = len(state.orders)
    active_buy_routes: dict[str, int] = defaultdict(int)
    for order in state.orders:
        check_budget(checkpoint)
        if order.side == "buy":
            active_buy_routes[order.asset_id] += 1
    split_asset_count = sum(count > 1 for count in active_buy_routes.values())

    route_priority = 0
    for transfer in state.funding_transfers:
        check_budget(checkpoint)
        route_priority += index.funding_routes[transfer.route_id].priority
    for order in state.orders:
        check_budget(checkpoint)
        route_priority += index.order_routes[order.route_id].priority

    incremental_cost = state.costs.explicit_cost
    incremental_order_rows = active_order_rows
    if baseline_state is not None:
        incremental_cost -= baseline_state.costs.explicit_cost
        baseline_active_order_ids = {order.decision_id for order in baseline_state.orders}
        incremental_order_rows = sum(order.decision_id not in baseline_active_order_ids for order in state.orders)

    values: dict[ExactObjectiveCode, ExactRatio] = {
        "fixed_l2": fixed_l2,
        "shortfall": state.accounting.shortfall,
        "turnover": turnover,
        "explicit_cost": state.costs.explicit_cost,
        "incremental_cost": incremental_cost,
        "split_asset_count": ExactRatio(split_asset_count),
        "active_order_rows": ExactRatio(active_order_rows),
        "incremental_order_rows": ExactRatio(incremental_order_rows),
        "route_priority": ExactRatio(route_priority),
    }
    expected = {item.code for item in view.objectives}
    if not expected.issubset(values):
        raise ExactPolicyContractError("policy view contains an unsupported exact objective")
    return values
