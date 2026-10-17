"""Finite upper bounds of every decision (funding transfers, FX debits, orders), the invested and selected values they rest on, and the decision rows a policy view must expose."""

from __future__ import annotations

from collections.abc import Mapping

from backend.app.services.pac_allocator.evaluation.errors import ExactPolicyContractError
from backend.app.services.pac_allocator.evaluation.keys import candidate_quanta, entity_refs, exact_decision_id, floor_units, fx_debit_key
from backend.app.services.pac_allocator.evaluation.reachability import buy_pool_currencies
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex, order_prices, source_broker, source_selected, to_valuation
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    Checkpoint,
    DecisionFamily,
    EntityRef,
    ExactPlannerScenario,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
)

_EXACT_ZERO = ExactRatio(0)
_EXACT_TWO = ExactRatio(2)


def current_invested(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> ExactRatio:
    total = _EXACT_ZERO
    for holding in scenario.holdings:
        check_budget(checkpoint)
        asset = index.assets[holding.asset_id]
        source_unit = asset.quote.price.amount / asset.quote.quote_base_quantity
        total += to_valuation(
            index,
            holding.planning_quantity * source_unit,
            asset.quote.price.currency,
        )
    return total


def selected_funding(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> ExactRatio:
    total = _EXACT_ZERO
    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        total += to_valuation(
            index,
            cash.selected.amount,
            cash.selected.currency,
        )
    for contribution in scenario.contributions:
        check_budget(checkpoint)
        total += to_valuation(
            index,
            contribution.amount.amount,
            contribution.amount.currency,
        )
    return total


def _funding_upper_bounds(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> dict[str, int]:
    bounds: dict[str, int] = {}
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        selected_amount = source_selected(
            index,
            route.source_kind,
            route.source_id,
        )
        quantum = index.currency_quantum[route.currency]
        source_broker_id = source_broker(
            index,
            route.source_kind,
            route.source_id,
        )
        maximum = min(route.transfer_cap.amount, selected_amount)
        if source_broker_id == route.broker_id:
            maximum = _EXACT_ZERO
        bounds[exact_decision_id("funding_transfer", route.route_id)] = floor_units(maximum, quantum)
    return bounds


def _total_resource_bound(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> ExactRatio:
    current = current_invested(scenario, index, checkpoint)
    selected = selected_funding(scenario, index, checkpoint)
    # Postings round against the plan, so no rounding adds resources any more.
    # The half-quantum margin below predates that rule: it only widens the
    # decision boxes by a few quanta, and keeping it keeps them, and the
    # oracle's enumeration domains, stable.
    favorable_rounding_bound = _EXACT_ZERO
    for route in scenario.order_routes:
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        if route.side == "buy":
            for currency in buy_pool_currencies(
                scenario,
                index,
                broker_id=route.broker_id,
                quote_currency=quote_currency,
                checkpoint=checkpoint,
            ):
                favorable_rounding_bound += to_valuation(
                    index,
                    index.currency_quantum[quote_currency] / _EXACT_TWO,
                    quote_currency,
                ) + to_valuation(
                    index,
                    index.currency_quantum[currency],
                    currency,
                )
        posting_count = 2 if route.side == "buy" else 3
        favorable_rounding_bound += to_valuation(
            index,
            (index.currency_quantum[quote_currency] * posting_count / _EXACT_TWO),
            quote_currency,
        )
    return current + selected + favorable_rounding_bound


def _fx_upper_bounds(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    resource_bound: ExactRatio,
    checkpoint: Checkpoint | None,
) -> dict[str, int]:
    bounds = {}
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            native_bound = resource_bound / index.valuation_rate[currency]
            bounds[exact_decision_id("fx_debit", fx_debit_key(route.route_id, currency))] = floor_units(
                native_bound,
                index.currency_quantum[currency],
            )
    return bounds


def _order_upper_bounds(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    resource_bound: ExactRatio,
    checkpoint: Checkpoint | None,
) -> dict[str, int]:
    bounds = {}
    for route in scenario.order_routes:
        check_budget(checkpoint)
        capability = index.capabilities[(route.broker_id, route.capability_id)]
        quote_currency = index.assets[route.asset_id].quote.price.currency
        if route.side == "buy":
            native_resource = resource_bound / index.valuation_rate[quote_currency]
            maximum = native_resource / order_prices(index, route).execution_native if capability.kind == "whole_quantity" else native_resource
        else:
            holding = index.holdings.get((route.asset_id, route.broker_id))
            if holding is None:
                maximum = _EXACT_ZERO
            elif capability.kind == "whole_quantity":
                maximum = holding.planning_quantity
            else:
                maximum = holding.planning_quantity * order_prices(index, route).execution_native
        # A route without a cap of its own keeps the resource (buy) or holding (sell) bound.
        if route.cap is not None:
            maximum = min(maximum, route.cap.value)
        family: DecisionFamily = "buy_quantum" if route.side == "buy" else "sell_quantum"
        bounds[exact_decision_id(family, route.route_id)] = floor_units(
            maximum,
            capability.order_step,
        )
    return bounds


def decision_upper_bounds(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> dict[str, int]:
    bounds = _funding_upper_bounds(scenario, index, checkpoint)
    resource_bound = _total_resource_bound(
        scenario,
        index,
        checkpoint,
    )
    bounds.update(
        _fx_upper_bounds(
            scenario,
            index,
            resource_bound,
            checkpoint,
        )
    )
    bounds.update(
        _order_upper_bounds(
            scenario,
            index,
            resource_bound,
            checkpoint,
        )
    )
    return bounds


def expected_decision_rows(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[tuple[str, DecisionFamily, tuple[EntityRef, ...]], ...]:
    rows: list[tuple[str, DecisionFamily, tuple[EntityRef, ...]]] = []
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        rows.append(
            (
                exact_decision_id("funding_transfer", route.route_id),
                "funding_transfer",
                entity_refs(
                    ("funding_route", route.route_id),
                    ("funding_source", f"{route.source_kind}:{route.source_id}"),
                ),
            )
        )
    for route in scenario.order_routes:
        check_budget(checkpoint)
        if route.side != "buy":
            continue
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            rows.append(
                (
                    exact_decision_id("fx_debit", fx_debit_key(route.route_id, currency)),
                    "fx_debit",
                    entity_refs(
                        ("order_route", route.route_id),
                        ("currency", currency),
                    ),
                )
            )
    for route in scenario.order_routes:
        check_budget(checkpoint)
        family: DecisionFamily = "buy_quantum" if route.side == "buy" else "sell_quantum"
        rows.append(
            (
                exact_decision_id(family, route.route_id),
                family,
                entity_refs(
                    ("asset", route.asset_id),
                    ("broker", route.broker_id),
                    ("order_route", route.route_id),
                ),
            )
        )
    return tuple(sorted(rows, key=lambda item: item[0]))


def validated_baseline_quanta(
    *,
    baseline: CandidateActionVector | None,
    expected_ids: tuple[str, ...],
    upper_bounds: Mapping[str, int],
    required: bool,
) -> dict[str, int]:
    if baseline is None:
        if required:
            raise ExactPolicyContractError("this policy purpose requires a complete baseline candidate")
        return dict.fromkeys(expected_ids, 0)
    baseline_ids = tuple(sorted(item.decision_id for item in baseline.decisions))
    if baseline_ids != expected_ids:
        raise ExactPolicyContractError("baseline candidate must contain every expected decision " "exactly once")
    values = candidate_quanta(baseline)
    for decision_id, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > upper_bounds[decision_id]:
            raise ExactPolicyContractError(f"baseline decision {decision_id} lies outside its finite domain")
    return values
