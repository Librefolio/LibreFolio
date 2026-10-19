"""The exact scenario index: FX and valuation rates, validated entity and route references, valuation and currency conversion, order prices and the lookups of funding sources."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from backend.app.services.financial_math.fx_rates import oriented_rate
from backend.app.services.pac_allocator.evaluation.errors import ExactScenarioContractError
from backend.app.services.pac_allocator.evaluation.keys import fx_pair_key
from backend.app.services.pac_allocator.models import (
    ExactAsset,
    ExactAssetTax,
    ExactBroker,
    ExactContribution,
    ExactCostBasis,
    ExactExistingCash,
    ExactFeeSchedule,
    ExactFundingRoute,
    ExactHolding,
    ExactOrderCapability,
    ExactOrderRoute,
    ExactPlannerScenario,
    ExactWithholding,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
)

_EXACT_ZERO = ExactRatio(0)
_EXACT_ONE = ExactRatio(1)


@dataclass(frozen=True, slots=True)
class _OrderPrices:
    source_unit: ExactRatio
    mid_native: ExactRatio
    execution_native: ExactRatio


@dataclass(frozen=True, slots=True)
class ScenarioIndex:
    valuation_currency: str
    currency_quantum: dict[str, ExactRatio]
    valuation_rate: dict[str, ExactRatio]
    assets: dict[str, ExactAsset]
    brokers: dict[str, ExactBroker]
    capabilities: dict[tuple[str, str], ExactOrderCapability]
    fees: dict[tuple[str, str], ExactFeeSchedule]
    holdings: dict[tuple[str, str], ExactHolding]
    existing_cash: dict[str, ExactExistingCash]
    contributions: dict[str, ExactContribution]
    funding_routes: dict[str, ExactFundingRoute]
    order_routes: dict[str, ExactOrderRoute]
    fx_rate_by_pair: dict[str, ExactRatio]
    target_weights: dict[str, ExactRatio]
    cost_basis: dict[str, ExactCostBasis]
    asset_tax: dict[str, ExactAssetTax]
    withholding: dict[str, ExactWithholding]


def exact_scenario_fingerprint(scenario: ExactPlannerScenario) -> str:
    """Hash the immutable canonical scenario without projecting through float."""
    if not isinstance(scenario, ExactPlannerScenario):
        raise ExactScenarioContractError("exact scenario fingerprint requires ExactPlannerScenario")
    return sha256(repr(scenario).encode("utf-8")).hexdigest()


def _fx_rate_by_pair_map(
    scenario: ExactPlannerScenario,
) -> dict[str, ExactRatio]:
    fx_rate_by_pair: dict[str, ExactRatio] = {}
    for item in scenario.fx_rates:
        if item.pair_key in fx_rate_by_pair:
            raise ExactScenarioContractError(f"duplicate FX rate pair {item.pair_key}")
        fx_rate_by_pair[item.pair_key] = item.rate
    return fx_rate_by_pair


def fx_rate(
    fx_rate_by_pair: Mapping[str, ExactRatio],
    source_currency: str,
    destination_currency: str,
) -> ExactRatio:
    if source_currency == destination_currency:
        return _EXACT_ONE
    rate = fx_rate_by_pair.get(fx_pair_key(source_currency, destination_currency))
    if rate is None:
        raise ExactScenarioContractError(f"missing direct FX rate for {source_currency}/{destination_currency}")
    return oriented_rate(rate, source_currency, destination_currency)


def _valuation_rate_map(
    scenario: ExactPlannerScenario,
    fx_rate_by_pair: Mapping[str, ExactRatio],
    referenced_currencies: Iterable[str],
) -> dict[str, ExactRatio]:
    valuation_rate = {scenario.valuation_currency: _EXACT_ONE}
    for currency in referenced_currencies:
        if currency in valuation_rate:
            continue
        valuation_rate[currency] = fx_rate(
            fx_rate_by_pair,
            currency,
            scenario.valuation_currency,
        )
    return valuation_rate


def _sell_context_maps(
    scenario: ExactPlannerScenario,
) -> tuple[
    dict[str, ExactCostBasis],
    dict[str, ExactAssetTax],
    dict[str, ExactWithholding],
]:
    if scenario.sell_context is None:
        return {}, {}, {}
    return (
        {item.holding_id: item for item in scenario.sell_context.cost_basis},
        {item.asset_id: item for item in scenario.sell_context.asset_tax},
        {item.broker_id: item for item in scenario.sell_context.withholding},
    )


def _referenced_currencies(
    scenario: ExactPlannerScenario,
    fees: Mapping[tuple[str, str], ExactFeeSchedule],
) -> set[str]:
    result = {
        scenario.valuation_currency,
        *(asset.quote.price.currency for asset in scenario.assets),
        *(item.available.currency for item in scenario.existing_cash),
        *(item.amount.currency for item in scenario.contributions),
        *(item.currency for item in scenario.funding_routes),
        *(item.fixed_fee.currency for item in fees.values()),
    }
    if scenario.sell_context is not None:
        result.update(item.average_unit_cost.currency for item in scenario.sell_context.cost_basis)
        result.update(item.fiscal_currency for item in scenario.sell_context.asset_tax)
        result.update(item.fiscal_currency for item in scenario.sell_context.withholding)
    return result


def _validate_currency_coverage(
    *,
    referenced_currencies: set[str],
    currency_quantum: Mapping[str, ExactRatio],
    valuation_rate: Mapping[str, ExactRatio],
) -> None:
    missing_specs = referenced_currencies - currency_quantum.keys()
    missing_rates = referenced_currencies - valuation_rate.keys()
    if missing_specs:
        raise ExactScenarioContractError(f"missing currency specs: {', '.join(sorted(missing_specs))}")
    if missing_rates:
        raise ExactScenarioContractError(f"missing valuation rates: {', '.join(sorted(missing_rates))}")


def _validate_funding_route_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
) -> None:
    for route in scenario.funding_routes:
        broker = index.brokers.get(route.broker_id)
        if broker is None:
            raise ExactScenarioContractError(f"funding route {route.route_id} references unknown Broker")
        if broker.active is False:
            raise ExactScenarioContractError(f"funding route {route.route_id} references inactive Broker")
        sources = index.existing_cash if route.source_kind == "existing_cash" else index.contributions
        if route.source_id not in sources:
            raise ExactScenarioContractError(f"funding route {route.route_id} references unknown source")
        if route.source_kind == "existing_cash":
            source_broker_id = index.existing_cash[route.source_id].broker_id
            if index.brokers[source_broker_id].active is False:
                raise ExactScenarioContractError(f"funding route {route.route_id} references " "inactive source Broker")
        if (
            _source_currency(
                index,
                route.source_kind,
                route.source_id,
            )
            != route.currency
        ):
            raise ExactScenarioContractError(f"funding route {route.route_id} changes source currency")


def _validate_order_route_units(
    route: ExactOrderRoute,
    capability: ExactOrderCapability,
    fee: ExactFeeSchedule,
    quote_currency: str,
) -> None:
    _validate_capability_step(capability)
    expected_minimum_kind = "whole_quantity" if capability.kind == "whole_quantity" else "monetary_amount"
    expected_cap_kind = "quantity" if capability.kind == "whole_quantity" else "notional"
    for field_name in ("minimum_if_active", "required_minimum"):
        minimum = getattr(route, field_name)
        if minimum.kind not in {"none", expected_minimum_kind}:
            raise ExactScenarioContractError(f"order route {route.route_id} has incompatible {field_name}")
        if minimum.kind == "monetary_amount" and minimum.currency != quote_currency:
            raise ExactScenarioContractError(f"order route {route.route_id} has cross-currency {field_name}")
    if route.cap is not None and route.cap.kind != expected_cap_kind:
        raise ExactScenarioContractError(f"order route {route.route_id} has incompatible cap unit")
    if route.cap is not None and route.cap.kind == "notional" and route.cap.currency != quote_currency:
        raise ExactScenarioContractError(f"order route {route.route_id} has cross-currency cap")
    if fee.fixed_fee.currency != quote_currency:
        raise ExactScenarioContractError(f"order route {route.route_id} has cross-currency fee schedule")


def _validate_capability_step(
    capability: ExactOrderCapability,
) -> None:
    if capability.kind == "whole_quantity" and capability.order_step.denominator != 1:
        raise ExactScenarioContractError(f"whole-quantity capability {capability.capability_id} " "requires an integer step")


def _validate_sell_route_context(
    route: ExactOrderRoute,
    quote_currency: str,
    index: ScenarioIndex,
) -> None:
    if route.side != "sell":
        return
    holding = index.holdings.get((route.asset_id, route.broker_id))
    if holding is None:
        raise ExactScenarioContractError(f"SELL route {route.route_id} has no Asset×Broker holding")
    cost_basis = index.cost_basis.get(holding.holding_id)
    asset_tax = index.asset_tax.get(route.asset_id)
    withholding = index.withholding.get(route.broker_id)
    if cost_basis is None or asset_tax is None or withholding is None:
        raise ExactScenarioContractError(f"SELL route {route.route_id} lacks WAC, tax, or withholding facts")
    if asset_tax.fiscal_currency != quote_currency or withholding.fiscal_currency != quote_currency:
        raise ExactScenarioContractError(f"SELL route {route.route_id} requires one native fiscal currency")
    convert_currency(
        index,
        cost_basis.average_unit_cost.amount,
        cost_basis.average_unit_cost.currency,
        quote_currency,
    )


def _validate_order_route_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
) -> None:
    for route in scenario.order_routes:
        broker = index.brokers.get(route.broker_id)
        if route.asset_id not in index.assets or broker is None:
            raise ExactScenarioContractError(f"order route {route.route_id} references an unknown entity")
        if broker.active is False:
            raise ExactScenarioContractError(f"order route {route.route_id} references inactive Broker")
        capability = index.capabilities.get((route.broker_id, route.capability_id))
        fee = index.fees.get((route.broker_id, route.fee_schedule_id))
        if capability is None or fee is None:
            raise ExactScenarioContractError(f"order route {route.route_id} lacks capability or fee schedule")
        if fee.capability_id != capability.capability_id or fee.side != route.side:
            raise ExactScenarioContractError(f"order route {route.route_id} has an incompatible fee schedule")
        asset = index.assets[route.asset_id]
        quote_currency = asset.quote.price.currency
        _validate_order_route_units(route, capability, fee, quote_currency)
        _validate_sell_route_context(route, quote_currency, index)
        order_prices(index, route)


def _validate_static_entity_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
) -> None:
    for holding in scenario.holdings:
        if holding.asset_id not in index.assets or holding.broker_id not in index.brokers:
            raise ExactScenarioContractError(f"holding {holding.holding_id} references an unknown entity")
    for cash in scenario.existing_cash:
        if cash.broker_id not in index.brokers:
            raise ExactScenarioContractError(f"cash source {cash.cash_id} references an unknown Broker")
        if index.brokers[cash.broker_id].active is False and cash.selected.amount > _EXACT_ZERO:
            raise ExactScenarioContractError(f"selected cash source {cash.cash_id} references inactive Broker")
    holding_ids = {item.holding_id for item in scenario.holdings}
    if not set(index.cost_basis).issubset(holding_ids):
        raise ExactScenarioContractError("SELL cost basis references an unknown holding")
    if not set(index.asset_tax).issubset(index.assets):
        raise ExactScenarioContractError("SELL tax facts reference an unknown Asset")
    if not set(index.withholding).issubset(index.brokers):
        raise ExactScenarioContractError("SELL withholding references an unknown Broker")


def build_scenario_index(scenario: ExactPlannerScenario) -> ScenarioIndex:
    currency_quantum = {item.currency: item.minor_unit for item in scenario.currency_specs}
    fx_rate_by_pair = _fx_rate_by_pair_map(scenario)
    assets = {item.asset_id: item for item in scenario.assets}
    brokers = {item.broker_id: item for item in scenario.brokers}
    capabilities = {(broker.broker_id, capability.capability_id): capability for broker in scenario.brokers for capability in broker.capabilities}
    fees = {(broker.broker_id, fee.fee_schedule_id): fee for broker in scenario.brokers for fee in broker.fee_schedules}
    holdings = {(item.asset_id, item.broker_id): item for item in scenario.holdings}
    existing_cash = {item.cash_id: item for item in scenario.existing_cash}
    contributions = {item.contribution_id: item for item in scenario.contributions}
    funding_routes = {item.route_id: item for item in scenario.funding_routes}
    order_routes = {item.route_id: item for item in scenario.order_routes}
    target_weights = {item.asset_id: item.weight for item in scenario.target_weights}
    cost_basis, asset_tax, withholding = _sell_context_maps(scenario)
    referenced_currencies = _referenced_currencies(scenario, fees)
    valuation_rate = _valuation_rate_map(
        scenario,
        fx_rate_by_pair,
        referenced_currencies,
    )
    result = ScenarioIndex(
        valuation_currency=scenario.valuation_currency,
        currency_quantum=currency_quantum,
        valuation_rate=valuation_rate,
        assets=assets,
        brokers=brokers,
        capabilities=capabilities,
        fees=fees,
        holdings=holdings,
        existing_cash=existing_cash,
        contributions=contributions,
        funding_routes=funding_routes,
        order_routes=order_routes,
        fx_rate_by_pair=fx_rate_by_pair,
        target_weights=target_weights,
        cost_basis=cost_basis,
        asset_tax=asset_tax,
        withholding=withholding,
    )
    _validate_currency_coverage(
        referenced_currencies=referenced_currencies,
        currency_quantum=currency_quantum,
        valuation_rate=valuation_rate,
    )
    _validate_static_entity_refs(scenario, result)
    _validate_funding_route_refs(scenario, result)
    _validate_order_route_refs(scenario, result)
    return result


def valuation_rate_of(index: ScenarioIndex, currency: str) -> ExactRatio:
    try:
        return index.valuation_rate[currency]
    except KeyError as error:
        raise ExactScenarioContractError(f"no valuation rate for {currency}") from error


def to_valuation(
    index: ScenarioIndex,
    amount: ExactRatio,
    currency: str,
) -> ExactRatio:
    return amount * valuation_rate_of(index, currency)


def convert_currency(
    index: ScenarioIndex,
    amount: ExactRatio,
    source_currency: str,
    destination_currency: str,
) -> ExactRatio:
    return amount * fx_rate(index.fx_rate_by_pair, source_currency, destination_currency)


def order_prices(
    index: ScenarioIndex,
    route: ExactOrderRoute,
) -> _OrderPrices:
    asset = index.assets[route.asset_id]
    mid_native = asset.quote.price.amount / asset.quote.quote_base_quantity
    if route.side == "buy":
        execution_native = mid_native * (_EXACT_ONE + route.execution_margin_rate)
    else:
        execution_native = mid_native * (_EXACT_ONE - route.execution_margin_rate)
    if execution_native <= _EXACT_ZERO:
        raise ExactScenarioContractError(f"order route {route.route_id} has a nonpositive execution price")
    return _OrderPrices(
        source_unit=mid_native,
        mid_native=mid_native,
        execution_native=execution_native,
    )


def source_selected(
    index: ScenarioIndex,
    kind: str,
    source_id: str,
) -> ExactRatio:
    if kind == "existing_cash":
        return index.existing_cash[source_id].selected.amount
    if kind == "contribution":
        return index.contributions[source_id].amount.amount
    raise ExactScenarioContractError(f"unknown funding source kind: {kind}")


def _source_currency(
    index: ScenarioIndex,
    kind: str,
    source_id: str,
) -> str:
    if kind == "existing_cash":
        return index.existing_cash[source_id].selected.currency
    if kind == "contribution":
        return index.contributions[source_id].amount.currency
    raise ExactScenarioContractError(f"unknown funding source kind: {kind}")


def source_broker(
    index: ScenarioIndex,
    kind: str,
    source_id: str,
) -> str | None:
    if kind == "existing_cash":
        return index.existing_cash[source_id].broker_id
    if kind == "contribution":
        return None
    raise ExactScenarioContractError(f"unknown funding source kind: {kind}")
