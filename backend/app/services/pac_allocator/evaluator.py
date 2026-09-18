"""Decimal P1 arithmetic for PAC budgets and portfolio target gaps."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, localcontext
from hashlib import sha256

from backend.app.services.pac_allocator.ledger import (
    exact_flow_posting,
    reconcile_broker_ledgers,
    rounded_money_posting,
)
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    Checkpoint,
    ConstraintRef,
    DecisionAccess,
    DecisionFamily,
    DecisionMode,
    EntityRef,
    ExactAccountingEvaluation,
    ExactAsset,
    ExactAssetEvaluation,
    ExactAssetTax,
    ExactBroker,
    ExactBrokerLedgerEvaluation,
    ExactConflict,
    ExactConstraintCode,
    ExactConstraintEvaluation,
    ExactContribution,
    ExactCostBasis,
    ExactCostEvaluation,
    ExactEvaluation,
    ExactExistingCash,
    ExactFeeSchedule,
    ExactFundingRoute,
    ExactFundingSourceEvaluation,
    ExactFundingTransferEvaluation,
    ExactFxEvaluation,
    ExactHolding,
    ExactHoldingEvaluation,
    ExactLedgerPosting,
    ExactObjectiveCode,
    ExactObjectiveEvaluation,
    ExactOrderCapability,
    ExactOrderEvaluation,
    ExactOrderRoute,
    ExactPlannerScenario,
    ExactPolicyPurpose,
    ExactPolicyView,
    ExactUnit,
    ExactWithholding,
    HoldingEvaluation,
    InstrumentEvaluation,
    LedgerPostingFamily,
    MoneyEvaluation,
    NormalizationResult,
    ObjectiveRef,
    PacEvaluation,
    PacNormalizationResult,
    ParsedContributionVector,
    ParsedMoneyVector,
    ParsedValue,
    ProofRequirement,
    RebalanceEvaluation,
    RebalanceNormalizationResult,
    SellIrreducibilityGateRef,
    TieBreakRef,
    check_budget,
    unavailable_reason,
)
from backend.app.services.pac_allocator.numeric import (
    HUNDRED,
    ZERO,
    ExactRatio,
    calculate_effective_fx_rate,
    calculate_fee,
    calculate_fx_credit,
    calculate_tax_reserve,
    calculate_taxable_gain,
    decimal_context,
    exact_holding_value,
)


def reporting_value(
    amount: ParsedValue[Decimal],
    currency: str | None,
    state: NormalizationResult,
) -> ParsedValue[Decimal]:
    """Value a supplied fact; never exchange or route native cash."""
    reason = unavailable_reason((amount, state.report_currency))
    if reason is not None:
        return ParsedValue(None, reason)
    if currency is None:
        raise RuntimeError("Available native amount has no currency")
    value = amount.require()
    if currency == state.report_currency.require() or value == ZERO:
        return ParsedValue(value)
    rate = state.rate_map().get(currency)
    if rate is None:
        return ParsedValue(None, "input_missing")
    if not rate.available:
        return ParsedValue(None, rate.reason or "dependency_unavailable")
    return ParsedValue(value * rate.require())


def _sum_values(values: tuple[ParsedValue[Decimal], ...]) -> ParsedValue[Decimal]:
    reason = unavailable_reason(values)
    if reason is not None:
        return ParsedValue(None, reason)
    return ParsedValue(sum((value.require() for value in values), ZERO))


def _money_total(
    vector: ParsedMoneyVector | ParsedContributionVector,
    state: NormalizationResult,
    checkpoint: Checkpoint | None,
) -> ParsedValue[Decimal]:
    if vector.reason is not None:
        return ParsedValue(None, vector.reason)
    if not state.report_currency.available:
        return ParsedValue(
            None,
            state.report_currency.reason or "input_missing",
        )
    converted = []
    for currency, amount in vector.amount_entries():
        check_budget(checkpoint)
        converted.append(reporting_value(ParsedValue(amount), currency, state))
    return _sum_values(tuple(converted))


def _evaluate_money(
    state: NormalizationResult,
    checkpoint: Checkpoint | None,
) -> MoneyEvaluation:
    existing = _money_total(state.cash, state, checkpoint)
    contributions = _money_total(state.contributions, state, checkpoint)
    if not state.currency_domain_valid:
        combined = ParsedValue(None, "outside_p1_domain")
    else:
        combined = _sum_values((existing, contributions))
    return MoneyEvaluation(existing, contributions, combined)


def evaluate_pac_budget(
    state: PacNormalizationResult,
    *,
    checkpoint: Checkpoint | None = None,
) -> PacEvaluation:
    """Allocate reporting budget by target; do not derive orders or quantities."""
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        money = _evaluate_money(state, checkpoint)
        allocations = []
        for target in state.targets:
            check_budget(checkpoint)
            reason = unavailable_reason((money.combined_cash, target.percent))
            if reason is None and state.asset_identity_valid and state.target_identity_valid and state.targets_valid:
                allocations.append(ParsedValue(money.combined_cash.require() * target.percent.require() / HUNDRED))
            else:
                allocations.append(
                    ParsedValue(
                        None,
                        reason or state.target_total.reason or "input_invalid",
                    )
                )
        check_budget(checkpoint)
        return PacEvaluation(money, tuple(allocations))


def evaluate_rebalancing(
    state: RebalanceNormalizationResult,
    *,
    checkpoint: Checkpoint | None = None,
) -> RebalanceEvaluation:
    """Aggregate canonical instruments and compare them with final targets."""
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        holding_values = []
        by_instrument: dict[str, list[int]] = defaultdict(list)
        for index, holding in enumerate(state.holdings):
            check_budget(checkpoint)
            by_instrument[holding.instrument_key].append(index)
            reason = unavailable_reason(
                (
                    holding.quantity,
                    holding.quote.price,
                    holding.quote.currency,
                    holding.quote.basis,
                )
            )
            if not holding.quote.date_valid:
                reason = "input_invalid"
            if reason is None:
                native = ParsedValue(
                    exact_holding_value(
                        holding.quantity.require(),
                        holding.quote.price.require(),
                        holding.quote.basis.require(),
                    )
                )
            else:
                native = ParsedValue(None, reason)
            holding_values.append(
                HoldingEvaluation(
                    native_value=native,
                    reporting_value=reporting_value(
                        native,
                        holding.quote.currency.value,
                        state,
                    ),
                )
            )

        if not holding_values:
            invested = ParsedValue(None, "input_missing")
        elif not state.row_identity_valid:
            invested = ParsedValue(None, "input_invalid")
        else:
            invested = _sum_values(tuple(value.reporting_value for value in holding_values))

        instruments = []
        gap_numerators: list[Decimal] = []
        for target in state.targets:
            check_budget(checkpoint)
            indices = by_instrument.get(target.instrument_key, [])
            current_values = tuple(holding_values[index].reporting_value for index in indices)
            current = _sum_values(current_values) if current_values else ParsedValue(None, "input_invalid")
            target_reason = unavailable_reason((invested, target.percent))
            if target_reason is None and state.target_identity_valid and state.targets_valid:
                target_value = ParsedValue(invested.require() * target.percent.require() / HUNDRED)
            else:
                target_value = ParsedValue(
                    None,
                    target_reason or state.target_total.reason or "input_invalid",
                )
            gap_reason = unavailable_reason((target_value, current))
            value_gap = ParsedValue(target_value.require() - current.require()) if gap_reason is None else ParsedValue(None, gap_reason)
            gap_numerator = None
            if value_gap.available and invested.available and invested.require() > ZERO:
                gap_numerator = target.percent.require() * invested.require() - HUNDRED * current.require()
                gap_numerators.append(gap_numerator)
            instruments.append(
                InstrumentEvaluation(
                    instrument_key=target.instrument_key,
                    current_reporting=current,
                    target_value_reporting=target_value,
                    value_gap_reporting=value_gap,
                    gap_numerator=gap_numerator,
                )
            )

        complete_gaps = state.targets_valid and len(gap_numerators) == len(state.targets) and bool(state.targets)
        maximum = max(abs(value) for value in gap_numerators) if complete_gaps else None
        squared = sum((value * value for value in gap_numerators), ZERO) if complete_gaps else None
        money = _evaluate_money(state, checkpoint)
        check_budget(checkpoint)
        return RebalanceEvaluation(
            holdings=tuple(holding_values),
            instruments=tuple(instruments),
            invested=invested,
            money=money,
            max_gap_numerator=maximum,
            squared_gap_numerator=squared,
        )


# Planner v2 exact evaluator -------------------------------------------------

_EXACT_ZERO = ExactRatio(0)
_EXACT_ONE = ExactRatio(1)
_EXACT_TWO = ExactRatio(2)

_DECISION_PREFIX: dict[DecisionFamily, str] = {
    "funding_transfer": "funding",
    "fx_debit": "fx",
    "buy_quantum": "buy",
    "sell_quantum": "sell",
}


class ExactEvaluatorError(ValueError):
    """Base error for malformed exact evaluator contracts."""


class ExactScenarioContractError(ExactEvaluatorError):
    """Raised when a caller bypasses the normalizer with inconsistent facts."""


class ExactPolicyContractError(ExactEvaluatorError):
    """Raised when an exact policy view cannot represent the requested phase."""


@dataclass(frozen=True, slots=True)
class _OrderPrices:
    source_unit: ExactRatio
    mid_native: ExactRatio
    execution_native: ExactRatio


@dataclass(frozen=True, slots=True)
class _ConstraintFact:
    value: ExactRatio
    lower_bound: ExactRatio | None
    upper_bound: ExactRatio | None
    satisfied: bool


@dataclass(frozen=True, slots=True)
class _ScenarioIndex:
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


@dataclass(frozen=True, slots=True)
class _EconomicState:
    postings: tuple[ExactLedgerPosting, ...]
    funding_transfers: tuple[ExactFundingTransferEvaluation, ...]
    funding_sources: tuple[ExactFundingSourceEvaluation, ...]
    fx: tuple[ExactFxEvaluation, ...]
    orders: tuple[ExactOrderEvaluation, ...]
    ledgers: tuple[ExactBrokerLedgerEvaluation, ...]
    holdings: tuple[ExactHoldingEvaluation, ...]
    assets: tuple[ExactAssetEvaluation, ...]
    accounting: ExactAccountingEvaluation
    costs: ExactCostEvaluation


def exact_decision_id(family: DecisionFamily, entity_id: str) -> str:
    """Return the stable W1 decision identifier shared by views and candidates."""
    if family not in _DECISION_PREFIX:
        raise ExactPolicyContractError(f"unknown decision family: {family}")
    if not entity_id:
        raise ExactPolicyContractError("decision entity ID must not be empty")
    return f"{_DECISION_PREFIX[family]}:{entity_id}"


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


def _fx_pair_key(first: str, second: str) -> str:
    return "/".join(sorted((first, second)))


def _fx_rate(
    fx_rate_by_pair: Mapping[str, ExactRatio],
    source_currency: str,
    destination_currency: str,
) -> ExactRatio:
    if source_currency == destination_currency:
        return _EXACT_ONE
    rate = fx_rate_by_pair.get(_fx_pair_key(source_currency, destination_currency))
    if rate is None:
        raise ExactScenarioContractError(f"missing direct FX rate for {source_currency}/{destination_currency}")
    return rate if source_currency < destination_currency else _EXACT_ONE / rate


def _valuation_rate_map(
    scenario: ExactPlannerScenario,
    fx_rate_by_pair: Mapping[str, ExactRatio],
    referenced_currencies: Iterable[str],
) -> dict[str, ExactRatio]:
    valuation_rate = {scenario.valuation_currency: _EXACT_ONE}
    for currency in referenced_currencies:
        if currency in valuation_rate:
            continue
        valuation_rate[currency] = _fx_rate(
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
    index: _ScenarioIndex,
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
    if route.cap.kind != expected_cap_kind:
        raise ExactScenarioContractError(f"order route {route.route_id} has incompatible cap unit")
    if route.cap.kind == "notional" and route.cap.currency != quote_currency:
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
    index: _ScenarioIndex,
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
    _convert_currency(
        index,
        cost_basis.average_unit_cost.amount,
        cost_basis.average_unit_cost.currency,
        quote_currency,
    )


def _validate_order_route_refs(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
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
        _order_prices(index, route)


def _validate_static_entity_refs(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
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


def _build_scenario_index(scenario: ExactPlannerScenario) -> _ScenarioIndex:
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
    result = _ScenarioIndex(
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


def _to_valuation(
    index: _ScenarioIndex,
    amount: ExactRatio,
    currency: str,
) -> ExactRatio:
    try:
        return amount * index.valuation_rate[currency]
    except KeyError as error:
        raise ExactScenarioContractError(f"no valuation rate for {currency}") from error


def _convert_currency(
    index: _ScenarioIndex,
    amount: ExactRatio,
    source_currency: str,
    destination_currency: str,
) -> ExactRatio:
    return amount * _fx_rate(index.fx_rate_by_pair, source_currency, destination_currency)


def _order_prices(
    index: _ScenarioIndex,
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


def _source_key(kind: str, source_id: str) -> tuple[str, str]:
    return kind, source_id


def _source_selected(
    index: _ScenarioIndex,
    kind: str,
    source_id: str,
) -> ExactRatio:
    if kind == "existing_cash":
        return index.existing_cash[source_id].selected.amount
    if kind == "contribution":
        return index.contributions[source_id].amount.amount
    raise ExactScenarioContractError(f"unknown funding source kind: {kind}")


def _source_currency(
    index: _ScenarioIndex,
    kind: str,
    source_id: str,
) -> str:
    if kind == "existing_cash":
        return index.existing_cash[source_id].selected.currency
    if kind == "contribution":
        return index.contributions[source_id].amount.currency
    raise ExactScenarioContractError(f"unknown funding source kind: {kind}")


def _source_broker(
    index: _ScenarioIndex,
    kind: str,
    source_id: str,
) -> str | None:
    if kind == "existing_cash":
        return index.existing_cash[source_id].broker_id
    if kind == "contribution":
        return None
    raise ExactScenarioContractError(f"unknown funding source kind: {kind}")


def _can_reach_buy(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    *,
    broker_id: str,
    currency: str,
    checkpoint: Checkpoint | None,
) -> bool:
    positive_targets: set[str] = set()
    for item in scenario.target_weights:
        check_budget(checkpoint)
        if item.weight > _EXACT_ZERO:
            positive_targets.add(item.asset_id)
    for route in scenario.order_routes:
        check_budget(checkpoint)
        if route.side != "buy" or route.broker_id != broker_id or route.asset_id not in positive_targets or route.cap.value <= _EXACT_ZERO:
            continue
        quote_currency = index.assets[route.asset_id].quote.price.currency
        if currency == quote_currency or _fx_pair_key(currency, quote_currency) in index.fx_rate_by_pair:
            return True
    return False


def _source_reachability(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    transferred_by_route: Mapping[str, ExactRatio],
    *,
    source_kind: str,
    source_id: str,
    source_broker_id: str | None,
    source_currency: str,
    remaining: ExactRatio,
    checkpoint: Checkpoint | None,
) -> tuple[ExactRatio, ExactRatio]:
    # `remaining` may be negative on an overcommitted source (transferred >
    # selected); that violation is reported separately via the
    # FUNDING_WITHIN_SELECTED fact. The reachable/trapped split always
    # operates on the nonnegative floor of `remaining` so both outputs stay
    # nonnegative and reconcile with `ExactFundingSourceEvaluation`'s
    # invariant, instead of raising before the violation can be reported.
    effective_remaining = max(remaining, _EXACT_ZERO)
    if source_broker_id is not None and _can_reach_buy(
        scenario,
        index,
        broker_id=source_broker_id,
        currency=source_currency,
        checkpoint=checkpoint,
    ):
        return effective_remaining, _EXACT_ZERO
    capacity = _EXACT_ZERO
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        if route.source_kind != source_kind or route.source_id != source_id:
            continue
        if not _can_reach_buy(scenario, index, broker_id=route.broker_id, currency=route.currency, checkpoint=checkpoint):
            continue
        unused = route.transfer_cap.amount - transferred_by_route.get(route.route_id, _EXACT_ZERO)
        if unused > _EXACT_ZERO:
            capacity += unused
    reachable = min(effective_remaining, capacity)
    trapped = effective_remaining - reachable
    return reachable, trapped


def _buy_pool_currencies(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    *,
    broker_id: str,
    quote_currency: str,
    checkpoint: Checkpoint | None,
) -> tuple[str, ...]:
    """Return the other currencies whose cash can fund a BUY at ``broker_id``.

    Candidates are currencies that actually hold (or can hold) cash at this
    Broker: existing cash, funding-route destinations, and other SELL
    routes' proceeds at the same Broker. Only currencies with a known direct
    FX pair to ``quote_currency`` qualify (anti-cascade: a pool currency must
    convert in one direct hop, never through a chain).
    """
    candidates: set[str] = set()
    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        if cash.broker_id == broker_id:
            candidates.add(cash.selected.currency)
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        if route.broker_id == broker_id:
            candidates.add(route.currency)
    for other in scenario.order_routes:
        check_budget(checkpoint)
        if other.broker_id == broker_id and other.side == "sell":
            candidates.add(index.assets[other.asset_id].quote.price.currency)
    candidates.discard(quote_currency)
    return tuple(sorted(currency for currency in candidates if _fx_pair_key(currency, quote_currency) in index.fx_rate_by_pair))


def _fx_debit_key(route_id: str, currency: str) -> str:
    return f"{route_id}:{currency}"


def _asset_broker_key(asset_id: str, broker_id: str) -> str:
    """Collision-free composite key: both components are arbitrary-length
    free-form identifiers that may themselves contain ``:`` or ``/``, so a
    plain ``f"{asset_id}:{broker_id}"`` join is ambiguous (e.g. ``("a", "b:c")``
    vs ``("a:b", "c")``). Length-prefixing each component removes the
    ambiguity regardless of its contents.
    """
    return f"{len(asset_id)}:{asset_id}{len(broker_id)}:{broker_id}"


def _floor_units(value: ExactRatio, quantum: ExactRatio) -> int:
    if value < _EXACT_ZERO or quantum <= _EXACT_ZERO:
        raise ExactPolicyContractError("finite decision bounds require nonnegative value and positive quantum")
    ratio = value / quantum
    return ratio.numerator // ratio.denominator


def _is_quantum_multiple(value: ExactRatio, quantum: ExactRatio) -> bool:
    if quantum <= _EXACT_ZERO:
        return False
    return (value / quantum).denominator == 1


def _entity_refs(*items: tuple[str, str]) -> tuple[EntityRef, ...]:
    return tuple(EntityRef(kind=kind, entity_id=entity_id) for kind, entity_id in sorted(items))


def _current_invested(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> ExactRatio:
    total = _EXACT_ZERO
    for holding in scenario.holdings:
        check_budget(checkpoint)
        asset = index.assets[holding.asset_id]
        source_unit = asset.quote.price.amount / asset.quote.quote_base_quantity
        total += _to_valuation(
            index,
            holding.planning_quantity * source_unit,
            asset.quote.price.currency,
        )
    return total


def _selected_funding(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> ExactRatio:
    total = _EXACT_ZERO
    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        total += _to_valuation(
            index,
            cash.selected.amount,
            cash.selected.currency,
        )
    for contribution in scenario.contributions:
        check_budget(checkpoint)
        total += _to_valuation(
            index,
            contribution.amount.amount,
            contribution.amount.currency,
        )
    return total


def _funding_upper_bounds(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> dict[str, int]:
    bounds: dict[str, int] = {}
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        source_selected = _source_selected(
            index,
            route.source_kind,
            route.source_id,
        )
        quantum = index.currency_quantum[route.currency]
        source_broker_id = _source_broker(
            index,
            route.source_kind,
            route.source_id,
        )
        maximum = min(route.transfer_cap.amount, source_selected)
        if source_broker_id == route.broker_id:
            maximum = _EXACT_ZERO
        bounds[exact_decision_id("funding_transfer", route.route_id)] = _floor_units(maximum, quantum)
    return bounds


def _total_resource_bound(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> ExactRatio:
    current = _current_invested(scenario, index, checkpoint)
    selected = _selected_funding(scenario, index, checkpoint)
    favorable_rounding_bound = _EXACT_ZERO
    for route in scenario.order_routes:
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        if route.side == "buy":
            for currency in _buy_pool_currencies(
                scenario,
                index,
                broker_id=route.broker_id,
                quote_currency=quote_currency,
                checkpoint=checkpoint,
            ):
                favorable_rounding_bound += _to_valuation(
                    index,
                    index.currency_quantum[quote_currency] / _EXACT_TWO,
                    quote_currency,
                ) + _to_valuation(
                    index,
                    index.currency_quantum[currency],
                    currency,
                )
        posting_count = 2 if route.side == "buy" else 3
        favorable_rounding_bound += _to_valuation(
            index,
            (index.currency_quantum[quote_currency] * posting_count / _EXACT_TWO),
            quote_currency,
        )
    return current + selected + favorable_rounding_bound


def _fx_upper_bounds(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    resource_bound: ExactRatio,
    checkpoint: Checkpoint | None,
) -> dict[str, int]:
    bounds = {}
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in _buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            native_bound = resource_bound / index.valuation_rate[currency]
            bounds[exact_decision_id("fx_debit", _fx_debit_key(route.route_id, currency))] = _floor_units(
                native_bound,
                index.currency_quantum[currency],
            )
    return bounds


def _order_upper_bounds(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    resource_bound: ExactRatio,
    checkpoint: Checkpoint | None,
) -> dict[str, int]:
    bounds = {}
    for route in scenario.order_routes:
        check_budget(checkpoint)
        capability = index.capabilities[(route.broker_id, route.capability_id)]
        quote_currency = index.assets[route.asset_id].quote.price.currency
        maximum = route.cap.value
        if route.side == "buy":
            native_resource = resource_bound / index.valuation_rate[quote_currency]
            resource_measure = native_resource / _order_prices(index, route).execution_native if capability.kind == "whole_quantity" else native_resource
            maximum = min(maximum, resource_measure)
        else:
            holding = index.holdings.get((route.asset_id, route.broker_id))
            if holding is None:
                maximum = _EXACT_ZERO
            elif capability.kind == "whole_quantity":
                maximum = min(maximum, holding.planning_quantity)
            else:
                maximum = min(
                    maximum,
                    holding.planning_quantity * _order_prices(index, route).execution_native,
                )
        family: DecisionFamily = "buy_quantum" if route.side == "buy" else "sell_quantum"
        bounds[exact_decision_id(family, route.route_id)] = _floor_units(
            maximum,
            capability.order_step,
        )
    return bounds


def _decision_upper_bounds(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
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


def _expected_decision_rows(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[tuple[str, DecisionFamily, tuple[EntityRef, ...]], ...]:
    rows: list[tuple[str, DecisionFamily, tuple[EntityRef, ...]]] = []
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        rows.append(
            (
                exact_decision_id("funding_transfer", route.route_id),
                "funding_transfer",
                _entity_refs(
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
        for currency in _buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            rows.append(
                (
                    exact_decision_id("fx_debit", _fx_debit_key(route.route_id, currency)),
                    "fx_debit",
                    _entity_refs(
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
                _entity_refs(
                    ("asset", route.asset_id),
                    ("broker", route.broker_id),
                    ("order_route", route.route_id),
                ),
            )
        )
    return tuple(sorted(rows, key=lambda item: item[0]))


def _candidate_quanta(
    candidate: CandidateActionVector,
) -> dict[str, int]:
    return {item.decision_id: item.quanta for item in candidate.decisions}


def _validated_baseline_quanta(
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
    values = _candidate_quanta(baseline)
    for decision_id, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > upper_bounds[decision_id]:
            raise ExactPolicyContractError(f"baseline decision {decision_id} lies outside its finite domain")
    return values


def _ledger_keys(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
) -> tuple[tuple[str, str], ...]:
    keys = {(cash.broker_id, cash.selected.currency) for cash in scenario.existing_cash}
    keys.update((route.broker_id, route.currency) for route in scenario.funding_routes)
    keys.update((route.broker_id, index.assets[route.asset_id].quote.price.currency) for route in scenario.order_routes)
    return tuple(sorted(keys))


def _constraint_ref(
    *,
    code: ExactConstraintCode,
    key: str,
    scope: str,
    entity_refs: tuple[EntityRef, ...],
    unit: ExactUnit,
    bound_source: str,
    public_issue_code: str | None = None,
) -> ConstraintRef:
    return ConstraintRef(
        ref_id=f"constraint:{code.lower()}:{key}",
        code=code,
        phase="exact",
        scope=scope,
        entity_refs=entity_refs,
        units=(unit,),
        enforcement="solver_and_exact",
        bound_source=bound_source,
        public_issue_code=public_issue_code,
        explanation_key=f"tools.allocation.constraints.{code.lower()}",
    )


def _funding_constraint_refs(
    scenario: ExactPlannerScenario,
    boolean_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        native = ExactUnit(
            kind="native_money",
            currency_code=cash.selected.currency,
        )
        source_ref = _entity_refs(("funding_source", f"existing_cash:{cash.cash_id}"))
        refs.append(
            _constraint_ref(
                code="SELECTED_WITHIN_AVAILABLE",
                key=f"existing_cash:{cash.cash_id}",
                scope="funding_source",
                entity_refs=source_ref,
                unit=native,
                bound_source="existing_cash.available",
                public_issue_code="allocation.cash_selection_invalid",
            )
        )
    source_rows = [
        (
            "existing_cash",
            cash.cash_id,
            cash.selected.currency,
        )
        for cash in scenario.existing_cash
    ]
    source_rows.extend(
        (
            "contribution",
            contribution.contribution_id,
            contribution.amount.currency,
        )
        for contribution in scenario.contributions
    )
    for source_kind, source_id, currency in source_rows:
        check_budget(checkpoint)
        source_ref = _entity_refs(("funding_source", f"{source_kind}:{source_id}"))
        native = ExactUnit(kind="native_money", currency_code=currency)
        refs.extend(
            (
                _constraint_ref(
                    code="FUNDING_WITHIN_SELECTED",
                    key=f"{source_kind}:{source_id}",
                    scope="funding_source",
                    entity_refs=source_ref,
                    unit=native,
                    bound_source="selected source amount",
                ),
                _constraint_ref(
                    code="FUNDING_SOURCE_CONSERVATION",
                    key=f"{source_kind}:{source_id}",
                    scope="funding_source",
                    entity_refs=source_ref,
                    unit=native,
                    bound_source="selected = transferred + remaining",
                ),
            )
        )
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        refs.append(
            _constraint_ref(
                code="NO_SELF_TRANSFER",
                key=route.route_id,
                scope="funding_route",
                entity_refs=_entity_refs(
                    ("funding_route", route.route_id),
                ),
                unit=ExactUnit(
                    kind="native_money",
                    currency_code=route.currency,
                ),
                bound_source="source Broker identity",
            )
        )
    refs.append(
        _constraint_ref(
            code="NO_DOUBLE_COUNT",
            key="global",
            scope="scenario",
            entity_refs=(),
            unit=boolean_unit,
            bound_source="funding source conservation",
        )
    )
    return refs


def _fx_constraint_refs(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    boolean_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in _buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            key = _fx_debit_key(route.route_id, currency)
            route_refs = _entity_refs(
                ("order_route", route.route_id),
                ("currency", currency),
            )
            refs.extend(
                (
                    _constraint_ref(
                        code="FX_DEBIT_CREDIT_COUPLED",
                        key=key,
                        scope="order_route",
                        entity_refs=route_refs,
                        unit=ExactUnit(
                            kind="native_money",
                            currency_code=quote_currency,
                        ),
                        bound_source="approved rate and global spread",
                    ),
                    _constraint_ref(
                        code="FX_CREDIT_POSITIVE",
                        key=key,
                        scope="order_route",
                        entity_refs=route_refs,
                        unit=ExactUnit(
                            kind="native_money",
                            currency_code=quote_currency,
                        ),
                        bound_source="posted destination credit",
                    ),
                    _constraint_ref(
                        code="FX_NATIVE_QUANTUM",
                        key=key,
                        scope="order_route",
                        entity_refs=route_refs,
                        unit=ExactUnit(
                            kind="native_money",
                            currency_code=currency,
                        ),
                        bound_source="source currency minor unit",
                    ),
                    _constraint_ref(
                        code="FX_SOURCE_CASH",
                        key=key,
                        scope="order_route",
                        entity_refs=route_refs,
                        unit=ExactUnit(
                            kind="native_money",
                            currency_code=currency,
                        ),
                        bound_source="Broker source-currency ledger",
                    ),
                )
            )
    return refs


def _order_constraint_refs(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    purpose: ExactPolicyPurpose,
    boolean_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for route in scenario.order_routes:
        check_budget(checkpoint)
        capability = index.capabilities[(route.broker_id, route.capability_id)]
        quote_currency = index.assets[route.asset_id].quote.price.currency
        native_or_quantity = (
            ExactUnit(kind="asset_quantity", asset_id=route.asset_id)
            if capability.kind == "whole_quantity"
            else ExactUnit(
                kind="native_money",
                currency_code=quote_currency,
            )
        )
        route_refs = _entity_refs(
            ("asset", route.asset_id),
            ("broker", route.broker_id),
            ("order_route", route.route_id),
        )
        for code, bound_source, public_issue_code in (
            (
                "ORDER_QUANTIZED",
                "capability order step",
                "allocation.nonpositive_order_amount_step",
            ),
            (
                "ORDER_MIN_IF_ACTIVE",
                "route minimum_if_active",
                "allocation.order_minimum_exceeds_cap",
            ),
            (
                "ORDER_REQUIRED_MIN",
                "route required_minimum",
                "allocation.required_min_notional_unfunded",
            ),
            ("ORDER_CAP", "route cap", "allocation.order_cap_nonpositive"),
            ("ORDER_SIDE_ALLOWED", "declared route side", None),
            ("NO_IMPLICIT_ROUTE", "normalized order route", None),
        ):
            unit = boolean_unit if code in {"ORDER_SIDE_ALLOWED", "NO_IMPLICIT_ROUTE"} else native_or_quantity
            refs.append(
                _constraint_ref(
                    code=code,
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=unit,
                    bound_source=bound_source,
                    public_issue_code=public_issue_code,
                )
            )
        refs.append(
            _constraint_ref(
                code="FX_RATE_ORDER_SAFE",
                key=route.route_id,
                scope="order_route",
                entity_refs=route_refs,
                unit=boolean_unit,
                bound_source="mid and execution prices",
                public_issue_code="allocation.price_order_invalid",
            )
        )
        if route.side == "sell":
            refs.append(
                _constraint_ref(
                    code="SELL_NET_POSITIVE",
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=quote_currency,
                    ),
                    bound_source="posted gross less posted fee and tax reserve",
                )
            )
        else:
            refs.append(
                _constraint_ref(
                    code="BUY_DEBIT_POSITIVE",
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=quote_currency,
                    ),
                    bound_source="posted BUY cash debit",
                )
            )
        if purpose == "sell_extension" and route.side == "sell":
            refs.append(
                _constraint_ref(
                    code="SELL_ELIGIBLE",
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=boolean_unit,
                    bound_source="frozen invest-only baseline",
                )
            )
    return refs


def _position_constraint_refs(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    boolean_unit: ExactUnit,
    valuation_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for broker_id, currency in _ledger_keys(scenario, index):
        check_budget(checkpoint)
        ledger_refs = _entity_refs(
            ("broker", broker_id),
            ("currency", currency),
        )
        native = ExactUnit(kind="native_money", currency_code=currency)
        key = f"{broker_id}:{currency}"
        refs.extend(
            (
                _constraint_ref(
                    code="SPENDABLE_CASH_NONNEGATIVE",
                    key=key,
                    scope="broker_currency",
                    entity_refs=ledger_refs,
                    unit=native,
                    bound_source="native ledger",
                ),
                _constraint_ref(
                    code="PHYSICAL_CASH_RECONCILED",
                    key=key,
                    scope="broker_currency",
                    entity_refs=ledger_refs,
                    unit=native,
                    bound_source="spendable plus physical reserves",
                ),
            )
        )
    holding_keys = {(holding.asset_id, holding.broker_id) for holding in scenario.holdings}
    holding_keys.update((route.asset_id, route.broker_id) for route in scenario.order_routes)
    for asset_id, broker_id in sorted(holding_keys):
        check_budget(checkpoint)
        pair_refs = _entity_refs(
            ("asset", asset_id),
            ("broker", broker_id),
        )
        unit = ExactUnit(kind="asset_quantity", asset_id=asset_id)
        key = _asset_broker_key(asset_id, broker_id)
        refs.extend(
            (
                _constraint_ref(
                    code="FINAL_QUANTITY_NONNEGATIVE",
                    key=key,
                    scope="asset_broker",
                    entity_refs=pair_refs,
                    unit=unit,
                    bound_source="holding conservation",
                ),
                _constraint_ref(
                    code="SELL_WITHIN_INVENTORY",
                    key=key,
                    scope="asset_broker",
                    entity_refs=pair_refs,
                    unit=unit,
                    bound_source="exact planning quantity",
                    public_issue_code=("portfolio_rebalancer.sell_inventory_exceeded"),
                ),
            )
        )
    for asset in scenario.assets:
        check_budget(checkpoint)
        asset_refs = _entity_refs(("asset", asset.asset_id))
        refs.extend(
            (
                _constraint_ref(
                    code="FINAL_VALUE_NONNEGATIVE",
                    key=asset.asset_id,
                    scope="asset",
                    entity_refs=asset_refs,
                    unit=valuation_unit,
                    bound_source="final exact holding value",
                ),
                _constraint_ref(
                    code="NO_ASSET_BUY_AND_SELL",
                    key=asset.asset_id,
                    scope="asset",
                    entity_refs=asset_refs,
                    unit=boolean_unit,
                    bound_source="active order sides",
                    public_issue_code="allocation.required_buy_sell_conflict",
                ),
            )
        )
    return refs


def _global_constraint_refs(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    boolean_unit: ExactUnit,
    valuation_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    check_budget(checkpoint)
    refs: list[ConstraintRef] = []
    global_specs = (
        ("ROUTE_DECLARED", boolean_unit, "candidate decision domain"),
        ("COST_NOT_INVESTMENT", boolean_unit, "mid-value accounting"),
        ("SELL_POSTED_ONCE", boolean_unit, "closed posting families"),
        ("ROUNDING_BOUND", valuation_unit, "active monetary postings"),
        ("ACCOUNTING_IDENTITY", valuation_unit, "fixed-reference identity"),
        ("NO_SHORT_OR_LEVERAGE", boolean_unit, "native ledgers and holdings"),
    )
    for code, unit, bound_source in global_specs:
        refs.append(
            _constraint_ref(
                code=code,
                key="global",
                scope="scenario",
                entity_refs=(),
                unit=unit,
                bound_source=bound_source,
            )
        )
    if scenario.product == "rebalancer":
        refs.append(
            _constraint_ref(
                code="REBALANCER_NONEMPTY",
                key="global",
                scope="scenario",
                entity_refs=(),
                unit=valuation_unit,
                bound_source="current and final invested value",
                public_issue_code=("portfolio_rebalancer.nonpositive_current_portfolio"),
            )
        )
    if purpose == "sell_extension":
        refs.append(
            _constraint_ref(
                code="SELL_FUNDS_INCREMENTAL_BUY",
                key="global",
                scope="scenario",
                entity_refs=(),
                unit=boolean_unit,
                bound_source="frozen baseline and incremental BUY",
                public_issue_code="portfolio_rebalancer.sell_to_idle_forbidden",
            )
        )
    return refs


def _build_constraint_refs(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    purpose: ExactPolicyPurpose,
    checkpoint: Checkpoint | None,
) -> tuple[ConstraintRef, ...]:
    boolean_unit = ExactUnit(kind="boolean")
    valuation_unit = ExactUnit(
        kind="valuation_money",
        currency_code=scenario.valuation_currency,
    )
    refs = _funding_constraint_refs(
        scenario,
        boolean_unit,
        checkpoint,
    )
    refs.extend(
        _fx_constraint_refs(
            scenario,
            index,
            boolean_unit,
            checkpoint,
        )
    )
    refs.extend(
        _order_constraint_refs(
            scenario,
            index,
            purpose,
            boolean_unit,
            checkpoint,
        )
    )
    refs.extend(
        _position_constraint_refs(
            scenario,
            index,
            boolean_unit,
            valuation_unit,
            checkpoint,
        )
    )
    refs.extend(
        _global_constraint_refs(
            scenario,
            purpose,
            boolean_unit,
            valuation_unit,
            checkpoint,
        )
    )
    return tuple(sorted(refs, key=lambda item: item.ref_id))


def _objective_codes(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
) -> tuple[ExactObjectiveCode, ...]:
    if purpose == "deployment":
        return (
            "shortfall",
            "fixed_l2",
            "incremental_cost",
            "incremental_order_rows",
        )
    if scenario.policy == "proportional":
        return (
            "fixed_l2",
            "shortfall",
            "route_priority",
            "explicit_cost",
            "active_order_rows",
        )
    if scenario.policy == "min_fragmentation":
        return (
            "fixed_l2",
            "shortfall",
            "split_asset_count",
            "active_order_rows",
            "route_priority",
            "explicit_cost",
        )
    return (
        "fixed_l2",
        "shortfall",
        "turnover",
        "explicit_cost",
        "active_order_rows",
    )


def _objective_unit(
    scenario: ExactPlannerScenario,
    code: ExactObjectiveCode,
) -> ExactUnit:
    if code == "fixed_l2":
        return ExactUnit(
            kind="valuation_money_squared",
            currency_code=scenario.valuation_currency,
        )
    if code in {
        "shortfall",
        "turnover",
        "explicit_cost",
        "incremental_cost",
    }:
        return ExactUnit(
            kind="valuation_money",
            currency_code=scenario.valuation_currency,
        )
    if code in {
        "split_asset_count",
        "active_order_rows",
        "incremental_order_rows",
    }:
        return ExactUnit(kind="count")
    return ExactUnit(kind="ordinal_penalty")


def _build_objective_refs(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
) -> tuple[ObjectiveRef, ...]:
    result = []
    for ordinal, code in enumerate(
        _objective_codes(scenario, purpose),
        start=1,
    ):
        result.append(
            ObjectiveRef(
                ref_id=f"objective:{ordinal:02d}:{code}",
                code=code,
                ordinal=ordinal,
                sense="min",
                unit=_objective_unit(scenario, code),
                freeze_rule="exact_nonworsening_bound",
                report_field=code,
                closure_rule="exact_ratio_equality",
            )
        )
    return tuple(result)


def _append_exact_flow(
    postings: list[ExactLedgerPosting],
    *,
    posting_id: str,
    family: LedgerPostingFamily,
    broker_id: str,
    currency: str,
    amount: ExactRatio,
    entity_refs: tuple[EntityRef, ...],
) -> None:
    if amount == _EXACT_ZERO:
        return
    postings.append(
        exact_flow_posting(
            posting_id=posting_id,
            family=family,
            broker_id=broker_id,
            currency=currency,
            amount=amount,
            entity_refs=entity_refs,
        )
    )


def _append_rounded_posting(
    postings: list[ExactLedgerPosting],
    *,
    posting_id: str,
    family: LedgerPostingFamily,
    broker_id: str,
    currency: str,
    exact_amount: ExactRatio,
    quantum: ExactRatio,
    entity_refs: tuple[EntityRef, ...],
) -> ExactRatio:
    if exact_amount == _EXACT_ZERO:
        return _EXACT_ZERO
    posting = rounded_money_posting(
        posting_id=posting_id,
        family=family,
        broker_id=broker_id,
        currency=currency,
        exact_amount=exact_amount,
        quantum=quantum,
        entity_refs=entity_refs,
    )
    postings.append(posting)
    return posting.posted_amount


def _evaluate_funding(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    quanta: Mapping[str, int],
    postings: list[ExactLedgerPosting],
    checkpoint: Checkpoint | None,
) -> tuple[
    tuple[ExactFundingTransferEvaluation, ...],
    tuple[ExactFundingSourceEvaluation, ...],
]:
    transferred_by_source: dict[tuple[str, str], ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    transferred_by_route: dict[str, ExactRatio] = {}
    transfers = []

    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        _append_exact_flow(
            postings,
            posting_id=f"initial:{cash.cash_id}",
            family="initial_selected",
            broker_id=cash.broker_id,
            currency=cash.selected.currency,
            amount=cash.selected.amount,
            entity_refs=_entity_refs(("existing_cash", cash.cash_id)),
        )

    for route in scenario.funding_routes:
        check_budget(checkpoint)
        decision_id = exact_decision_id(
            "funding_transfer",
            route.route_id,
        )
        decision_quanta = quanta[decision_id]
        amount = index.currency_quantum[route.currency] * decision_quanta
        transferred_by_source[_source_key(route.source_kind, route.source_id)] += amount
        transferred_by_route[route.route_id] = amount
        if amount == _EXACT_ZERO:
            continue
        route_refs = _entity_refs(("funding_route", route.route_id))
        _append_exact_flow(
            postings,
            posting_id=f"funding-in:{route.route_id}",
            family="funding_in",
            broker_id=route.broker_id,
            currency=route.currency,
            amount=amount,
            entity_refs=route_refs,
        )
        if route.source_kind == "existing_cash":
            source_broker_id = index.existing_cash[route.source_id].broker_id
            _append_exact_flow(
                postings,
                posting_id=f"funding-out:{route.route_id}",
                family="funding_out",
                broker_id=source_broker_id,
                currency=route.currency,
                amount=amount,
                entity_refs=route_refs,
            )
        transfers.append(
            ExactFundingTransferEvaluation(
                decision_id=decision_id,
                route_id=route.route_id,
                source_kind=route.source_kind,
                source_id=route.source_id,
                destination_broker_id=route.broker_id,
                currency=route.currency,
                quanta=decision_quanta,
                amount=amount,
            )
        )

    sources = []
    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        key = _source_key("existing_cash", cash.cash_id)
        transferred = transferred_by_source[key]
        remaining = cash.selected.amount - transferred
        reachable_amount, trapped_amount = _source_reachability(
            scenario,
            index,
            transferred_by_route,
            source_kind="existing_cash",
            source_id=cash.cash_id,
            source_broker_id=cash.broker_id,
            source_currency=cash.selected.currency,
            remaining=remaining,
            checkpoint=checkpoint,
        )
        sources.append(
            ExactFundingSourceEvaluation(
                source_kind="existing_cash",
                source_id=cash.cash_id,
                source_broker_id=cash.broker_id,
                currency=cash.selected.currency,
                selected=cash.selected.amount,
                transferred=transferred,
                remaining=remaining,
                structurally_reachable_amount=reachable_amount,
                structurally_trapped_amount=trapped_amount,
            )
        )
    for contribution in scenario.contributions:
        check_budget(checkpoint)
        key = _source_key(
            "contribution",
            contribution.contribution_id,
        )
        transferred = transferred_by_source[key]
        remaining = contribution.amount.amount - transferred
        reachable_amount, trapped_amount = _source_reachability(
            scenario,
            index,
            transferred_by_route,
            source_kind="contribution",
            source_id=contribution.contribution_id,
            source_broker_id=None,
            source_currency=contribution.amount.currency,
            remaining=remaining,
            checkpoint=checkpoint,
        )
        sources.append(
            ExactFundingSourceEvaluation(
                source_kind="contribution",
                source_id=contribution.contribution_id,
                source_broker_id=None,
                currency=contribution.amount.currency,
                selected=contribution.amount.amount,
                transferred=transferred,
                remaining=remaining,
                structurally_reachable_amount=reachable_amount,
                structurally_trapped_amount=trapped_amount,
            )
        )
    return (
        tuple(sorted(transfers, key=lambda item: item.route_id)),
        tuple(
            sorted(
                sources,
                key=lambda item: (item.source_kind, item.source_id),
            )
        ),
    )


def _evaluate_fx(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    quanta: Mapping[str, int],
    postings: list[ExactLedgerPosting],
    checkpoint: Checkpoint | None,
) -> tuple[ExactFxEvaluation, ...]:
    result = []
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in _buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            decision_id = exact_decision_id(
                "fx_debit",
                _fx_debit_key(route.route_id, currency),
            )
            decision_quanta = quanta[decision_id]
            if decision_quanta == 0:
                continue
            source_debit = index.currency_quantum[currency] * decision_quanta
            approved_rate = _fx_rate(index.fx_rate_by_pair, currency, quote_currency)
            effective_rate = calculate_effective_fx_rate(
                approved_rate=approved_rate,
                spread=scenario.fx_spread_rate,
            )
            exact_credit = calculate_fx_credit(
                source_debit=source_debit,
                approved_rate=approved_rate,
                spread=scenario.fx_spread_rate,
            )
            posting_refs = _entity_refs(
                ("order_route", route.route_id),
                ("currency", currency),
            )
            _append_exact_flow(
                postings,
                posting_id=f"fx-debit:{route.route_id}:{currency}",
                family="fx_debit",
                broker_id=route.broker_id,
                currency=currency,
                amount=source_debit,
                entity_refs=posting_refs,
            )
            posted_credit = _append_rounded_posting(
                postings,
                posting_id=f"fx-credit:{route.route_id}:{currency}",
                family="fx_credit",
                broker_id=route.broker_id,
                currency=quote_currency,
                exact_amount=exact_credit,
                quantum=index.currency_quantum[quote_currency],
                entity_refs=posting_refs,
            )
            spread_loss = _to_valuation(index, source_debit, currency) - _to_valuation(
                index,
                exact_credit,
                quote_currency,
            )
            result.append(
                ExactFxEvaluation(
                    decision_id=decision_id,
                    order_route_id=route.route_id,
                    broker_id=route.broker_id,
                    source_currency=currency,
                    destination_currency=quote_currency,
                    quanta=decision_quanta,
                    source_debit=source_debit,
                    approved_rate=approved_rate,
                    effective_rate=effective_rate,
                    exact_destination_credit=exact_credit,
                    posted_destination_credit=posted_credit,
                    spread_loss=spread_loss,
                )
            )
    return tuple(sorted(result, key=lambda item: (item.order_route_id, item.source_currency)))


def _sell_tax_facts(
    *,
    index: _ScenarioIndex,
    route: ExactOrderRoute,
    quote_currency: str,
    economic_quantity: ExactRatio,
    exact_gross: ExactRatio,
    exact_fee: ExactRatio,
) -> tuple[
    ExactRatio,
    ExactRatio,
    ExactRatio,
    ExactRatio,
    str,
]:
    holding = index.holdings.get((route.asset_id, route.broker_id))
    if holding is None:
        raise ExactScenarioContractError(f"SELL route {route.route_id} has no Asset×Broker holding")
    cost_basis = index.cost_basis.get(holding.holding_id)
    asset_tax = index.asset_tax.get(route.asset_id)
    withholding = index.withholding.get(route.broker_id)
    if cost_basis is None or asset_tax is None or withholding is None:
        raise ExactScenarioContractError(f"SELL route {route.route_id} lacks WAC, tax, or withholding facts")
    unit_cost = _convert_currency(
        index,
        cost_basis.average_unit_cost.amount,
        cost_basis.average_unit_cost.currency,
        quote_currency,
    )
    sold_cost_basis = economic_quantity * unit_cost
    taxable_gain = calculate_taxable_gain(
        gross_sell_proceeds=exact_gross,
        sell_fee=exact_fee,
        sold_quantity=economic_quantity,
        unit_cost=unit_cost,
    )
    exact_tax = calculate_tax_reserve(
        gross_sell_proceeds=exact_gross,
        sell_fee=exact_fee,
        sold_quantity=economic_quantity,
        unit_cost=unit_cost,
        tax_rate=asset_tax.gain_tax_rate,
    )
    return (
        unit_cost,
        sold_cost_basis,
        taxable_gain,
        exact_tax,
        withholding.withholding_kind,
    )


def _evaluate_orders(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    quanta: Mapping[str, int],
    postings: list[ExactLedgerPosting],
    checkpoint: Checkpoint | None,
) -> tuple[ExactOrderEvaluation, ...]:
    result = []
    for route in scenario.order_routes:
        check_budget(checkpoint)
        family: DecisionFamily = "buy_quantum" if route.side == "buy" else "sell_quantum"
        decision_id = exact_decision_id(family, route.route_id)
        decision_quanta = quanta[decision_id]
        if decision_quanta == 0:
            continue
        asset = index.assets[route.asset_id]
        quote_currency = asset.quote.price.currency
        capability = index.capabilities[(route.broker_id, route.capability_id)]
        fee_schedule = index.fees[(route.broker_id, route.fee_schedule_id)]
        prices = _order_prices(index, route)
        order_measure = capability.order_step * decision_quanta
        if capability.kind == "whole_quantity":
            economic_quantity = order_measure
            exact_cash = economic_quantity * prices.execution_native
        else:
            exact_cash = order_measure
            economic_quantity = order_measure / prices.execution_native
        native_mid_value = economic_quantity * prices.mid_native
        mid_value = _to_valuation(
            index,
            native_mid_value,
            quote_currency,
        )
        execution_margin_loss = (
            _to_valuation(
                index,
                exact_cash - native_mid_value,
                quote_currency,
            )
            if route.side == "buy"
            else _to_valuation(
                index,
                native_mid_value - exact_cash,
                quote_currency,
            )
        )
        exact_fee = calculate_fee(
            notional=exact_cash,
            fixed=fee_schedule.fixed_fee.amount,
            rate=fee_schedule.proportional_rate,
            floor=fee_schedule.minimum_fee.amount,
            cap=(fee_schedule.maximum_fee.amount if fee_schedule.maximum_fee is not None else None),
        )
        route_refs = _entity_refs(
            ("asset", route.asset_id),
            ("broker", route.broker_id),
            ("order_route", route.route_id),
        )
        cash_family = "buy_debit" if route.side == "buy" else "gross_sell_credit"
        posted_cash = _append_rounded_posting(
            postings,
            posting_id=f"{cash_family.replace('_', '-')}:{route.route_id}",
            family=cash_family,
            broker_id=route.broker_id,
            currency=quote_currency,
            exact_amount=exact_cash,
            quantum=index.currency_quantum[quote_currency],
            entity_refs=route_refs,
        )
        fee_family = "buy_fee" if route.side == "buy" else "sell_fee"
        posted_fee = _append_rounded_posting(
            postings,
            posting_id=f"{fee_family.replace('_', '-')}:{route.route_id}",
            family=fee_family,
            broker_id=route.broker_id,
            currency=quote_currency,
            exact_amount=exact_fee,
            quantum=index.currency_quantum[quote_currency],
            entity_refs=route_refs,
        )
        cost_basis = _EXACT_ZERO
        taxable_gain = _EXACT_ZERO
        exact_tax = _EXACT_ZERO
        posted_tax = _EXACT_ZERO
        withholding_kind = None
        if route.side == "sell":
            (
                _unit_cost,
                cost_basis,
                taxable_gain,
                exact_tax,
                withholding_kind,
            ) = _sell_tax_facts(
                index=index,
                route=route,
                quote_currency=quote_currency,
                economic_quantity=economic_quantity,
                exact_gross=exact_cash,
                exact_fee=exact_fee,
            )
            tax_family = "broker_withheld_tax" if withholding_kind == "broker_withheld" else "self_reserved_tax"
            posted_tax = _append_rounded_posting(
                postings,
                posting_id=f"{tax_family.replace('_', '-')}:{route.route_id}",
                family=tax_family,
                broker_id=route.broker_id,
                currency=quote_currency,
                exact_amount=exact_tax,
                quantum=index.currency_quantum[quote_currency],
                entity_refs=route_refs,
            )
        result.append(
            ExactOrderEvaluation(
                decision_id=decision_id,
                route_id=route.route_id,
                side=route.side,
                broker_id=route.broker_id,
                asset_id=route.asset_id,
                capability_kind=capability.kind,
                native_currency=quote_currency,
                source_currency=quote_currency,
                source_quote_base_quantity=(asset.quote.quote_base_quantity),
                quanta=decision_quanta,
                order_measure=order_measure,
                economic_quantity=economic_quantity,
                source_unit_price=prices.source_unit,
                mid_unit_price=prices.mid_native,
                execution_unit_price=prices.execution_native,
                exact_cash_amount=exact_cash,
                posted_cash_amount=posted_cash,
                exact_fee=exact_fee,
                posted_fee=posted_fee,
                mid_value=mid_value,
                execution_margin_loss=execution_margin_loss,
                cost_basis=cost_basis,
                taxable_gain=taxable_gain,
                exact_tax_reserve=exact_tax,
                posted_tax_reserve=posted_tax,
                withholding_kind=withholding_kind,
            )
        )
    return tuple(sorted(result, key=lambda item: item.route_id))


def _evaluate_holdings(
    scenario: ExactPlannerScenario,
    orders: tuple[ExactOrderEvaluation, ...],
    checkpoint: Checkpoint | None,
) -> tuple[ExactHoldingEvaluation, ...]:
    initial = {(item.asset_id, item.broker_id): item.planning_quantity for item in scenario.holdings}
    buy: dict[tuple[str, str], ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    sell: dict[tuple[str, str], ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    for order in orders:
        check_budget(checkpoint)
        key = (order.asset_id, order.broker_id)
        if order.side == "buy":
            buy[key] += order.economic_quantity
        else:
            sell[key] += order.economic_quantity
    keys = set(initial) | set(buy) | set(sell) | {(route.asset_id, route.broker_id) for route in scenario.order_routes}
    result = []
    for asset_id, broker_id in sorted(keys):
        check_budget(checkpoint)
        initial_quantity = initial.get((asset_id, broker_id), _EXACT_ZERO)
        buy_quantity = buy[(asset_id, broker_id)]
        sell_quantity = sell[(asset_id, broker_id)]
        result.append(
            ExactHoldingEvaluation(
                asset_id=asset_id,
                broker_id=broker_id,
                initial_quantity=initial_quantity,
                buy_quantity=buy_quantity,
                sell_quantity=sell_quantity,
                final_quantity=(initial_quantity + buy_quantity - sell_quantity),
            )
        )
    return tuple(result)


def _evaluate_assets(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    holdings: tuple[ExactHoldingEvaluation, ...],
    orders: tuple[ExactOrderEvaluation, ...],
    fixed_reference: ExactRatio,
    checkpoint: Checkpoint | None,
) -> tuple[ExactAssetEvaluation, ...]:
    current_by_asset: dict[str, ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    final_by_asset: dict[str, ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    buy_by_asset: dict[str, ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    sell_by_asset: dict[str, ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    for holding in holdings:
        check_budget(checkpoint)
        asset = index.assets[holding.asset_id]
        source_unit = asset.quote.price.amount / asset.quote.quote_base_quantity
        current_by_asset[holding.asset_id] += _to_valuation(
            index,
            holding.initial_quantity * source_unit,
            asset.quote.price.currency,
        )
        final_by_asset[holding.asset_id] += _to_valuation(
            index,
            holding.final_quantity * source_unit,
            asset.quote.price.currency,
        )
    for order in orders:
        check_budget(checkpoint)
        if order.side == "buy":
            buy_by_asset[order.asset_id] += order.mid_value
        else:
            sell_by_asset[order.asset_id] += order.mid_value
    result = []
    for asset in scenario.assets:
        check_budget(checkpoint)
        target_weight = index.target_weights[asset.asset_id]
        target_value = target_weight * fixed_reference
        current_value = current_by_asset[asset.asset_id]
        final_value = final_by_asset[asset.asset_id]
        result.append(
            ExactAssetEvaluation(
                asset_id=asset.asset_id,
                target_weight=target_weight,
                current_value=current_value,
                target_value=target_value,
                buy_mid_value=buy_by_asset[asset.asset_id],
                sell_mid_value=sell_by_asset[asset.asset_id],
                final_value=final_value,
                residual=final_value - target_value,
            )
        )
    return tuple(result)


def _evaluate_costs(
    index: _ScenarioIndex,
    fx: tuple[ExactFxEvaluation, ...],
    orders: tuple[ExactOrderEvaluation, ...],
    checkpoint: Checkpoint | None,
) -> ExactCostEvaluation:
    buy_fees = _EXACT_ZERO
    sell_fees = _EXACT_ZERO
    fx_spread_loss = _EXACT_ZERO
    execution_margin_loss = _EXACT_ZERO
    broker_withheld_tax = _EXACT_ZERO
    self_reserved_tax = _EXACT_ZERO
    for action in fx:
        check_budget(checkpoint)
        fx_spread_loss += action.spread_loss
    for order in orders:
        check_budget(checkpoint)
        fee_value = _to_valuation(
            index,
            order.exact_fee,
            order.native_currency,
        )
        if order.side == "buy":
            buy_fees += fee_value
        else:
            sell_fees += fee_value
            tax_value = _to_valuation(
                index,
                order.exact_tax_reserve,
                order.native_currency,
            )
            if order.withholding_kind == "broker_withheld":
                broker_withheld_tax += tax_value
            else:
                self_reserved_tax += tax_value
        execution_margin_loss += order.execution_margin_loss
    explicit_cost = buy_fees + sell_fees + fx_spread_loss + execution_margin_loss + broker_withheld_tax + self_reserved_tax
    return ExactCostEvaluation(
        buy_fees=buy_fees,
        sell_fees=sell_fees,
        fx_spread_loss=fx_spread_loss,
        execution_margin_loss=execution_margin_loss,
        broker_withheld_tax=broker_withheld_tax,
        self_reserved_tax=self_reserved_tax,
        explicit_cost=explicit_cost,
    )


def _evaluate_economic_state(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    quanta: Mapping[str, int],
    checkpoint: Checkpoint | None,
) -> _EconomicState:
    check_budget(checkpoint)
    postings: list[ExactLedgerPosting] = []
    funding_transfers, funding_sources = _evaluate_funding(
        scenario,
        index,
        quanta,
        postings,
        checkpoint,
    )
    fx = _evaluate_fx(
        scenario,
        index,
        quanta,
        postings,
        checkpoint,
    )
    orders = _evaluate_orders(
        scenario,
        index,
        quanta,
        postings,
        checkpoint,
    )
    postings_tuple = tuple(sorted(postings, key=lambda item: item.posting_id))
    ledgers = reconcile_broker_ledgers(
        ledger_keys=_ledger_keys(scenario, index),
        postings=postings_tuple,
        checkpoint=checkpoint,
    )
    holdings = _evaluate_holdings(scenario, orders, checkpoint)
    current_invested = _current_invested(
        scenario,
        index,
        checkpoint,
    )
    selected_funding = _selected_funding(
        scenario,
        index,
        checkpoint,
    )
    reachable_funding = _EXACT_ZERO
    for source in funding_sources:
        check_budget(checkpoint)
        reachable_funding += _to_valuation(
            index,
            _source_reachability(
                scenario,
                index,
                {},
                source_kind=source.source_kind,
                source_id=source.source_id,
                source_broker_id=source.source_broker_id,
                source_currency=source.currency,
                remaining=source.selected,
                checkpoint=checkpoint,
            )[0],
            source.currency,
        )
    trapped_funding = selected_funding - reachable_funding
    fixed_reference = current_invested + reachable_funding
    assets = _evaluate_assets(
        scenario,
        index,
        holdings,
        orders,
        fixed_reference,
        checkpoint,
    )
    final_invested = sum(
        (item.final_value for item in assets),
        _EXACT_ZERO,
    )
    costs = _evaluate_costs(index, fx, orders, checkpoint)
    external_contribution_cash = sum(
        (
            _to_valuation(
                index,
                source.remaining,
                source.currency,
            )
            for source in funding_sources
            if source.source_kind == "contribution"
        ),
        _EXACT_ZERO,
    )
    broker_spendable_cash = sum(
        (
            _to_valuation(
                index,
                row.final_spendable,
                row.currency,
            )
            for row in ledgers
        ),
        _EXACT_ZERO,
    )
    free_cash = broker_spendable_cash + external_contribution_cash - trapped_funding
    physical_reserves = costs.self_reserved_tax
    economic_losses = costs.buy_fees + costs.sell_fees + costs.fx_spread_loss + costs.execution_margin_loss + costs.broker_withheld_tax
    rounding_adjustment = sum(
        (
            _to_valuation(
                index,
                posting.accounting_rounding_adjustment,
                posting.currency,
            )
            for posting in postings_tuple
        ),
        _EXACT_ZERO,
    )
    rounding_bound = sum(
        (
            _to_valuation(
                index,
                posting.quantum / _EXACT_TWO,
                posting.currency,
            )
            for posting in postings_tuple
            if posting.quantum is not None
        ),
        _EXACT_ZERO,
    )
    shortfall = fixed_reference - final_invested
    identity_delta = shortfall - (free_cash + physical_reserves + economic_losses + rounding_adjustment)
    accounting = ExactAccountingEvaluation(
        current_invested=current_invested,
        selected_funding=selected_funding,
        reachable_funding=reachable_funding,
        trapped_funding=trapped_funding,
        fixed_reference=fixed_reference,
        final_invested=final_invested,
        shortfall=shortfall,
        free_cash=free_cash,
        physical_reserves=physical_reserves,
        economic_losses=economic_losses,
        rounding_adjustment=rounding_adjustment,
        rounding_bound=rounding_bound,
        identity_delta=identity_delta,
    )
    check_budget(checkpoint)
    return _EconomicState(
        postings=postings_tuple,
        funding_transfers=funding_transfers,
        funding_sources=funding_sources,
        fx=fx,
        orders=orders,
        ledgers=ledgers,
        holdings=holdings,
        assets=assets,
        accounting=accounting,
        costs=costs,
    )


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
    index: _ScenarioIndex,
    quanta: Mapping[str, int],
    state: _EconomicState,
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
        source_broker_id = _source_broker(
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
    index: _ScenarioIndex,
    state: _EconomicState,
    ledger_rows: Mapping[
        tuple[str, str],
        ExactBrokerLedgerEvaluation,
    ],
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts: dict[str, _ConstraintFact] = {}
    fx_actions = {(item.order_route_id, item.source_currency): item for item in state.fx}
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in _buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            key = _fx_debit_key(route.route_id, currency)
            action = fx_actions.get((route.route_id, currency))
            source_debit = action.source_debit if action is not None else _EXACT_ZERO
            exact_credit = action.exact_destination_credit if action is not None else _EXACT_ZERO
            posted_credit = action.posted_destination_credit if action is not None else _EXACT_ZERO
            approved_rate = _fx_rate(index.fx_rate_by_pair, currency, quote_currency)
            expected_exact = calculate_fx_credit(
                source_debit=source_debit,
                approved_rate=approved_rate,
                spread=scenario.fx_spread_rate,
            )
            expected_posted = (
                rounded_money_posting(
                    posting_id="constraint-only",
                    family="fx_credit",
                    broker_id=route.broker_id,
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
            native_quantized = _is_quantum_multiple(
                source_debit,
                index.currency_quantum[currency],
            )
            facts[_constraint_id("FX_NATIVE_QUANTUM", key)] = _ConstraintFact(
                value=source_debit,
                lower_bound=_EXACT_ZERO,
                upper_bound=None,
                satisfied=native_quantized,
            )
            source_ledger = ledger_rows[(route.broker_id, currency)]
            facts[_constraint_id("FX_SOURCE_CASH", key)] = _ConstraintFact(
                value=source_ledger.final_spendable,
                lower_bound=_EXACT_ZERO,
                upper_bound=None,
                satisfied=source_ledger.final_spendable >= _EXACT_ZERO,
            )
    return facts


def _order_route_constraint_facts(
    *,
    route: ExactOrderRoute,
    index: _ScenarioIndex,
    quanta: Mapping[str, int],
    purpose: ExactPolicyPurpose,
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
    required_minimum = _minimum_value(route, "required_minimum")
    if purpose in {"primary", "invest_only_baseline"} and route.side == "sell":
        required_minimum = _EXACT_ZERO
    prices = _order_prices(index, route)
    price_order_safe = prices.mid_native <= prices.execution_native if route.side == "buy" else prices.execution_native <= prices.mid_native
    return {
        _constraint_id(
            "ORDER_QUANTIZED",
            route.route_id,
        ): _ConstraintFact(
            value=measure,
            lower_bound=_EXACT_ZERO,
            upper_bound=None,
            satisfied=_is_quantum_multiple(
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
        _constraint_id(
            "ORDER_REQUIRED_MIN",
            route.route_id,
        ): _ConstraintFact(
            value=measure,
            lower_bound=required_minimum,
            upper_bound=None,
            satisfied=measure >= required_minimum,
        ),
        _constraint_id("ORDER_CAP", route.route_id): _ConstraintFact(
            value=measure,
            lower_bound=_EXACT_ZERO,
            upper_bound=route.cap.value,
            satisfied=measure <= route.cap.value,
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
    index: _ScenarioIndex,
    quanta: Mapping[str, int],
    state: _EconomicState,
    purpose: ExactPolicyPurpose,
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
                purpose=purpose,
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
    index: _ScenarioIndex,
    state: _EconomicState,
    checkpoint: Checkpoint | None,
) -> dict[str, _ConstraintFact]:
    facts = {}
    ledger_rows = {(item.broker_id, item.currency): item for item in state.ledgers}
    for broker_id, currency in _ledger_keys(scenario, index):
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
        constraint_key = _asset_broker_key(holding.asset_id, holding.broker_id)
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
    state: _EconomicState,
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
    index: _ScenarioIndex,
    view: ExactPolicyView,
    quanta: Mapping[str, int],
    state: _EconomicState,
    baseline_state: _EconomicState | None,
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
        no_sell_state = _evaluate_economic_state(
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


def _constraint_facts(
    *,
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    view: ExactPolicyView,
    quanta: Mapping[str, int],
    state: _EconomicState,
    baseline_state: _EconomicState | None,
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
    facts.update(
        _order_constraint_facts(
            scenario,
            index,
            quanta,
            state,
            view.purpose,
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


def _validate_policy_purpose(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    baseline: CandidateActionVector | None,
) -> None:
    if purpose not in {
        "primary",
        "invest_only_baseline",
        "sell_extension",
        "deployment",
    }:
        raise ExactPolicyContractError(f"unknown exact policy purpose: {purpose}")
    if purpose == "primary" and scenario.policy == "invest_and_sell":
        raise ExactPolicyContractError("invest_and_sell requires invest_only_baseline then sell_extension")
    if purpose in {"invest_only_baseline", "sell_extension"} and scenario.policy != "invest_and_sell":
        raise ExactPolicyContractError(f"{purpose} requires an invest_and_sell scenario")
    if purpose in {"primary", "invest_only_baseline"} and baseline is not None:
        raise ExactPolicyContractError(f"{purpose} cannot receive a baseline candidate")


def _validate_invest_only_baseline(
    *,
    purpose: ExactPolicyPurpose,
    rows: tuple[
        tuple[str, DecisionFamily, tuple[EntityRef, ...]],
        ...,
    ],
    baseline_quanta: Mapping[str, int],
) -> None:
    if purpose in {"primary", "invest_only_baseline"}:
        if any(baseline_quanta.values()):
            raise ExactPolicyContractError(f"{purpose} must start from the zero action vector")
        return
    if purpose != "sell_extension":
        return
    sell_baseline_ids = {decision_id for decision_id, family, _refs in rows if family == "sell_quantum"}
    if any(baseline_quanta[decision_id] != 0 for decision_id in sell_baseline_ids):
        raise ExactPolicyContractError("invest-only baseline cannot contain SELL decisions")


def _baseline_state_for_purpose(
    *,
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    purpose: ExactPolicyPurpose,
    baseline_quanta: Mapping[str, int],
    checkpoint: Checkpoint | None,
) -> _EconomicState | None:
    if purpose not in {"sell_extension", "deployment"}:
        return None
    return _evaluate_economic_state(
        scenario,
        index,
        baseline_quanta,
        checkpoint,
    )


def _sell_eligible_route_ids(
    *,
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    baseline_state: _EconomicState | None,
) -> set[str]:
    if purpose != "sell_extension" or baseline_state is None:
        return set()
    baseline_assets = {item.asset_id: item for item in baseline_state.assets}
    baseline_buy_assets = {order.asset_id for order in baseline_state.orders if order.side == "buy"}
    return {route.route_id for route in scenario.order_routes if route.side == "sell" and baseline_assets[route.asset_id].residual > _EXACT_ZERO and route.asset_id not in baseline_buy_assets}


def _decision_mode_for_purpose(
    *,
    purpose: ExactPolicyPurpose,
    family: DecisionFamily,
    route_id: str,
    sell_eligible: set[str],
) -> DecisionMode:
    if purpose in {"primary", "invest_only_baseline"}:
        return "disabled" if family == "sell_quantum" else "mutable"
    if purpose == "sell_extension":
        if family in {"funding_transfer", "fx_debit"}:
            return "frozen_exact"
        if family == "buy_quantum":
            return "additive_only"
        return "mutable" if route_id in sell_eligible else "disabled"
    return "additive_only" if family == "buy_quantum" else "frozen_exact"


def _decision_access(
    *,
    decision_id: str,
    family: DecisionFamily,
    entity_refs: tuple[EntityRef, ...],
    mode: DecisionMode,
    upper_bound: int,
    baseline_value: int,
) -> DecisionAccess:
    if mode == "disabled":
        return DecisionAccess(
            decision_id=decision_id,
            family=family,
            mode=mode,
            entity_refs=entity_refs,
            lower_quanta=0,
            upper_quanta=0,
            baseline_quanta=0,
            frozen_quanta=None,
        )
    lower = baseline_value if mode == "additive_only" else 0
    frozen = baseline_value if mode == "frozen_exact" else None
    return DecisionAccess(
        decision_id=decision_id,
        family=family,
        mode=mode,
        entity_refs=entity_refs,
        lower_quanta=lower,
        upper_quanta=upper_bound,
        baseline_quanta=baseline_value,
        frozen_quanta=frozen,
    )


def _build_decision_accesses(
    *,
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    rows: tuple[
        tuple[str, DecisionFamily, tuple[EntityRef, ...]],
        ...,
    ],
    upper_bounds: Mapping[str, int],
    baseline_quanta: Mapping[str, int],
    baseline_state: _EconomicState | None,
    checkpoint: Checkpoint | None,
) -> tuple[DecisionAccess, ...]:
    sell_eligible = _sell_eligible_route_ids(
        scenario=scenario,
        purpose=purpose,
        baseline_state=baseline_state,
    )
    decisions = []
    for decision_id, family, entity_refs in rows:
        check_budget(checkpoint)
        route_id = decision_id.split(":", 1)[1]
        decisions.append(
            _decision_access(
                decision_id=decision_id,
                family=family,
                entity_refs=entity_refs,
                mode=_decision_mode_for_purpose(
                    purpose=purpose,
                    family=family,
                    route_id=route_id,
                    sell_eligible=sell_eligible,
                ),
                upper_bound=upper_bounds[decision_id],
                baseline_value=baseline_quanta[decision_id],
            )
        )
    return tuple(sorted(decisions, key=lambda item: item.decision_id))


def _canonical_tie_decision_ids(
    *,
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[str, ...]:
    rows: list[tuple[tuple[str, ...], str]] = []
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        decision_id = exact_decision_id("funding_transfer", route.route_id)
        rows.append(
            (
                (
                    "",
                    route.broker_id,
                    route.currency,
                    "funding",
                    "",
                    route.route_id,
                    decision_id,
                ),
                decision_id,
            )
        )
    for route in scenario.order_routes:
        check_budget(checkpoint)
        if route.side != "buy":
            continue
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in _buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            decision_id = exact_decision_id("fx_debit", _fx_debit_key(route.route_id, currency))
            rows.append(
                (
                    (
                        "",
                        route.broker_id,
                        currency,
                        "fx",
                        quote_currency,
                        route.route_id,
                        decision_id,
                    ),
                    decision_id,
                )
            )
    for route in scenario.order_routes:
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        family: DecisionFamily = "buy_quantum" if route.side == "buy" else "sell_quantum"
        decision_id = exact_decision_id(family, route.route_id)
        rows.append(
            (
                (
                    route.asset_id,
                    route.broker_id,
                    quote_currency,
                    route.side,
                    "",
                    route.route_id,
                    decision_id,
                ),
                decision_id,
            )
        )
    return tuple(decision_id for _, decision_id in sorted(rows))


def _canonical_tie_breaks(
    *,
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[TieBreakRef, ...]:
    return (
        TieBreakRef(
            ref_id="tie:canonical-decision-vector",
            code="canonical_key",
            ordinal=1,
            unit=ExactUnit(kind="canonical_key"),
            decision_ids=_canonical_tie_decision_ids(
                scenario=scenario,
                index=index,
                checkpoint=checkpoint,
            ),
        ),
    )


def _sell_gate_refs(
    *,
    purpose: ExactPolicyPurpose,
    decisions: tuple[DecisionAccess, ...],
) -> tuple[
    tuple[SellIrreducibilityGateRef, ...],
    tuple[ProofRequirement, ...],
]:
    if purpose != "sell_extension":
        return (), ()
    additive_buys = tuple(item.decision_id for item in decisions if item.family == "buy_quantum" and item.mode == "additive_only")
    reopened = tuple(item.decision_id for item in decisions if item.family in {"funding_transfer", "fx_debit"})
    gates = tuple(
        SellIrreducibilityGateRef(
            gate_id=f"sell-irreducibility:{item.decision_id}",
            sell_decision_id=item.decision_id,
            fixed_incremental_buy_decision_ids=additive_buys,
            reopened_decision_ids=reopened,
        )
        for item in decisions
        if (item.family == "sell_quantum" and item.mode != "disabled" and item.upper_quanta > 0)
    )
    requirements = (
        (
            ProofRequirement(
                requirement_id="proof:sell-irreducibility",
                code="portfolio_rebalancer.sell_irreducibility",
                allowed_sources=(
                    "deterministic_conflict",
                    "exhaustive_oracle",
                ),
            ),
        )
        if gates
        else ()
    )
    return gates, requirements


def _require_feasible_invest_only_baseline(
    scenario: ExactPlannerScenario,
    *,
    purpose: ExactPolicyPurpose,
    baseline: CandidateActionVector | None,
    checkpoint: Checkpoint | None,
) -> None:
    if purpose != "sell_extension":
        return
    if baseline is None:
        raise ExactPolicyContractError("SELL extension requires an invest-only baseline candidate")
    baseline_view = build_exact_policy_view(
        scenario,
        purpose="invest_only_baseline",
        view_id=baseline.view_id,
        checkpoint=checkpoint,
    )
    evaluation = evaluate_exact_candidate(
        scenario,
        baseline_view,
        baseline,
        checkpoint=checkpoint,
    )
    if not evaluation.feasible:
        codes = ", ".join(evaluation.conflict_codes)
        raise ExactPolicyContractError("SELL extension baseline is not exact-feasible" + (f": {codes}" if codes else ""))


def _default_exact_view_id(
    *,
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    baseline_quanta: Mapping[str, int],
) -> str:
    prefix = f"exact:{scenario.snapshot.snapshot_id}:" f"{scenario.snapshot.draft_revision}:{purpose}"
    if purpose not in {"sell_extension", "deployment"}:
        return prefix
    baseline_fingerprint = sha256(repr(tuple(sorted(baseline_quanta.items()))).encode("utf-8")).hexdigest()
    return f"{prefix}:{baseline_fingerprint}"


def build_exact_policy_view(
    scenario: ExactPlannerScenario,
    *,
    purpose: ExactPolicyPurpose = "primary",
    baseline: CandidateActionVector | None = None,
    view_id: str | None = None,
    checkpoint: Checkpoint | None = None,
) -> ExactPolicyView:
    """Build the canonical solver-neutral exact view for one policy phase.

    ``invest_and_sell`` is deliberately two-stage: callers first request
    ``invest_only_baseline`` and then pass that complete candidate to
    ``sell_extension``. ``deployment`` freezes all primary funding, FX and
    SELL decisions and exposes BUY decisions as additive-only; its caller
    supplies the already exact-verified primary candidate.
    """
    check_budget(checkpoint)
    index = _build_scenario_index(scenario)
    _validate_policy_purpose(scenario, purpose, baseline)
    rows = _expected_decision_rows(scenario, index, checkpoint)
    expected_ids = tuple(item[0] for item in rows)
    upper_bounds = _decision_upper_bounds(
        scenario,
        index,
        checkpoint,
    )
    baseline_quanta = _validated_baseline_quanta(
        baseline=baseline,
        expected_ids=expected_ids,
        upper_bounds=upper_bounds,
        required=purpose in {"sell_extension", "deployment"},
    )
    _require_feasible_invest_only_baseline(
        scenario,
        purpose=purpose,
        baseline=baseline,
        checkpoint=checkpoint,
    )
    _validate_invest_only_baseline(
        purpose=purpose,
        rows=rows,
        baseline_quanta=baseline_quanta,
    )
    baseline_state = _baseline_state_for_purpose(
        scenario=scenario,
        index=index,
        purpose=purpose,
        baseline_quanta=baseline_quanta,
        checkpoint=checkpoint,
    )
    decision_tuple = _build_decision_accesses(
        scenario=scenario,
        purpose=purpose,
        rows=rows,
        upper_bounds=upper_bounds,
        baseline_quanta=baseline_quanta,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    objectives = _build_objective_refs(scenario, purpose)
    sell_gates, proof_requirements = _sell_gate_refs(
        purpose=purpose,
        decisions=decision_tuple,
    )
    fingerprint = exact_scenario_fingerprint(scenario)
    result = ExactPolicyView(
        view_id=(
            view_id
            if view_id is not None
            else _default_exact_view_id(
                scenario=scenario,
                purpose=purpose,
                baseline_quanta=baseline_quanta,
            )
        ),
        scenario_fingerprint=fingerprint,
        product=scenario.product,
        policy=scenario.policy,
        purpose=purpose,
        phase="exact",
        decisions=decision_tuple,
        constraints=_build_constraint_refs(
            scenario,
            index,
            purpose,
            checkpoint,
        ),
        objectives=objectives,
        tie_breaks=_canonical_tie_breaks(
            scenario=scenario,
            index=index,
            checkpoint=checkpoint,
        ),
        sell_gates=sell_gates,
        proof_requirements=proof_requirements,
    )
    check_budget(checkpoint)
    return result


def _validated_policy_decisions(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    view: ExactPolicyView,
    checkpoint: Checkpoint | None,
) -> tuple[tuple[DecisionAccess, ...], _EconomicState | None]:
    expected_rows = _expected_decision_rows(scenario, index, checkpoint)
    expected_ids = tuple(item[0] for item in expected_rows)
    if tuple(item.decision_id for item in view.decisions) != expected_ids:
        raise ExactPolicyContractError("policy view must expose every scenario decision exactly once")
    upper_bounds = _decision_upper_bounds(
        scenario,
        index,
        checkpoint,
    )
    baseline_quanta = {item.decision_id: item.baseline_quanta for item in view.decisions}
    if any(value < 0 or value > upper_bounds[decision_id] for decision_id, value in baseline_quanta.items()):
        raise ExactPolicyContractError("policy view baseline lies outside the canonical finite domain")
    _validate_invest_only_baseline(
        purpose=view.purpose,
        rows=expected_rows,
        baseline_quanta=baseline_quanta,
    )
    if view.purpose == "sell_extension":
        embedded_baseline = CandidateActionVector(
            view_id=f"{view.view_id}:embedded-invest-only",
            candidate_id=f"{view.view_id}:embedded-invest-only",
            decisions=tuple(
                CandidateDecision(
                    decision_id=decision_id,
                    quanta=baseline_quanta[decision_id],
                )
                for decision_id in expected_ids
            ),
        )
        _require_feasible_invest_only_baseline(
            scenario,
            purpose=view.purpose,
            baseline=embedded_baseline,
            checkpoint=checkpoint,
        )
    baseline_state = _baseline_state_for_purpose(
        scenario=scenario,
        index=index,
        purpose=view.purpose,
        baseline_quanta=baseline_quanta,
        checkpoint=checkpoint,
    )
    expected_decisions = _build_decision_accesses(
        scenario=scenario,
        purpose=view.purpose,
        rows=expected_rows,
        upper_bounds=upper_bounds,
        baseline_quanta=baseline_quanta,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    if view.decisions != expected_decisions:
        raise ExactPolicyContractError("policy view decision access differs from the canonical phase")
    return expected_decisions, baseline_state


def _validate_policy_view(
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    view: ExactPolicyView,
    checkpoint: Checkpoint | None,
) -> tuple[ExactPolicyPurpose, _EconomicState | None]:
    if view.product != scenario.product or view.policy != scenario.policy:
        raise ExactPolicyContractError("policy view product/policy does not match the scenario")
    if view.phase != "exact":
        raise ExactPolicyContractError("exact evaluator requires an exact-phase policy view")
    _validate_policy_purpose(scenario, view.purpose, None)
    if view.scenario_fingerprint != exact_scenario_fingerprint(scenario):
        raise ExactPolicyContractError("policy view scenario fingerprint does not match")
    expected_decisions, baseline_state = _validated_policy_decisions(
        scenario,
        index,
        view,
        checkpoint,
    )
    expected_constraints = _build_constraint_refs(
        scenario,
        index,
        view.purpose,
        checkpoint,
    )
    if view.constraints != expected_constraints:
        raise ExactPolicyContractError("policy view constraint refs do not match the exact catalogue")
    expected_objectives = _build_objective_refs(
        scenario,
        view.purpose,
    )
    if view.objectives != expected_objectives:
        raise ExactPolicyContractError("policy view objective refs do not match its policy phase")
    if view.tie_breaks != _canonical_tie_breaks(
        scenario=scenario,
        index=index,
        checkpoint=checkpoint,
    ):
        raise ExactPolicyContractError("policy view tie break differs from the canonical vector")
    expected_gates, expected_requirements = _sell_gate_refs(
        purpose=view.purpose,
        decisions=expected_decisions,
    )
    if view.sell_gates != expected_gates or view.proof_requirements != expected_requirements:
        raise ExactPolicyContractError("policy view SELL proof metadata differs from the canonical phase")
    return view.purpose, baseline_state


def _conflict(
    code: str,
    *refs: tuple[str, str],
) -> ExactConflict:
    return ExactConflict(code=code, entity_refs=_entity_refs(*refs))


def _decision_access_conflicts(
    access: DecisionAccess,
    value: int,
) -> tuple[ExactConflict, ...]:
    ref = ("decision", access.decision_id)
    conflicts = []
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return (_conflict("CANDIDATE_DECISION_OFF_GRID", ref),)
    if not access.lower_quanta <= value <= access.upper_quanta:
        conflicts.append(_conflict("CANDIDATE_DECISION_OUT_OF_BOUNDS", ref))
    if access.mode == "disabled" and value != 0:
        conflicts.append(_conflict("CANDIDATE_DECISION_DISABLED", ref))
    if access.mode == "frozen_exact" and value != access.frozen_quanta:
        conflicts.append(_conflict("CANDIDATE_DECISION_NOT_FROZEN", ref))
    if access.mode == "additive_only" and value < access.baseline_quanta:
        conflicts.append(_conflict("CANDIDATE_DECISION_NOT_ADDITIVE", ref))
    return tuple(conflicts)


def _candidate_contract_conflicts(
    *,
    view: ExactPolicyView,
    candidate: CandidateActionVector,
    checkpoint: Checkpoint | None,
) -> tuple[ExactConflict, ...]:
    conflicts = []
    if candidate.view_id != view.view_id:
        conflicts.append(
            _conflict(
                "CANDIDATE_VIEW_MISMATCH",
                ("policy_view", view.view_id),
                ("candidate", candidate.candidate_id),
            )
        )
    candidate_ids = tuple(item.decision_id for item in candidate.decisions)
    if len(candidate_ids) != len(set(candidate_ids)):
        conflicts.append(
            _conflict(
                "CANDIDATE_DECISION_DUPLICATE",
                ("candidate", candidate.candidate_id),
            )
        )
    candidate_values = _candidate_quanta(candidate)
    expected_ids = {item.decision_id for item in view.decisions}
    actual_ids = set(candidate_values)
    for decision_id in sorted(expected_ids - actual_ids):
        conflicts.append(
            _conflict(
                "CANDIDATE_DECISION_MISSING",
                ("decision", decision_id),
            )
        )
    for decision_id in sorted(actual_ids - expected_ids):
        conflicts.append(
            _conflict(
                "CANDIDATE_DECISION_EXTRA",
                ("decision", decision_id),
            )
        )
    for access in view.decisions:
        check_budget(checkpoint)
        value = candidate_values.get(access.decision_id)
        if value is None:
            continue
        conflicts.extend(_decision_access_conflicts(access, value))
    return tuple(
        sorted(
            set(conflicts),
            key=lambda item: (
                item.code,
                tuple((ref.kind, ref.entity_id) for ref in item.entity_refs),
            ),
        )
    )


def _objective_value_map(
    *,
    scenario: ExactPlannerScenario,
    index: _ScenarioIndex,
    view: ExactPolicyView,
    quanta: Mapping[str, int],
    state: _EconomicState,
    baseline_state: _EconomicState | None,
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


def evaluate_exact_candidate(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    candidate: CandidateActionVector,
    *,
    checkpoint: Checkpoint | None = None,
) -> ExactEvaluation:
    """Replay one complete discrete candidate with exact native accounting."""
    check_budget(checkpoint)
    index = _build_scenario_index(scenario)
    _purpose, baseline_state = _validate_policy_view(
        scenario,
        index,
        view,
        checkpoint,
    )
    contract_conflicts = _candidate_contract_conflicts(
        view=view,
        candidate=candidate,
        checkpoint=checkpoint,
    )
    if contract_conflicts:
        conflict_codes = tuple(sorted({item.code for item in contract_conflicts}))
        return ExactEvaluation(
            view_id=view.view_id,
            candidate_id=candidate.candidate_id,
            feasible=False,
            constraints=(),
            objectives=(),
            conflict_codes=conflict_codes,
            candidate_valid=False,
            conflicts=contract_conflicts,
        )

    quanta = _candidate_quanta(candidate)
    state = _evaluate_economic_state(
        scenario,
        index,
        quanta,
        checkpoint,
    )
    facts = _constraint_facts(
        scenario=scenario,
        index=index,
        view=view,
        quanta=quanta,
        state=state,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    constraints = []
    conflicts = []
    for ref in view.constraints:
        check_budget(checkpoint)
        fact = facts.get(ref.ref_id)
        if fact is None:
            raise ExactPolicyContractError(f"exact evaluator has no predicate for {ref.ref_id}")
        constraints.append(
            ExactConstraintEvaluation(
                ref_id=ref.ref_id,
                satisfied=fact.satisfied,
                value=fact.value,
                lower_bound=fact.lower_bound,
                upper_bound=fact.upper_bound,
            )
        )
        if not fact.satisfied:
            conflicts.append(
                ExactConflict(
                    code=ref.code,
                    entity_refs=ref.entity_refs,
                )
            )

    objective_values = _objective_value_map(
        scenario=scenario,
        index=index,
        view=view,
        quanta=quanta,
        state=state,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    objectives = tuple(
        ExactObjectiveEvaluation(
            ref_id=ref.ref_id,
            value=objective_values[ref.code],
        )
        for ref in view.objectives
    )
    conflicts_tuple = tuple(
        sorted(
            set(conflicts),
            key=lambda item: (
                item.code,
                tuple((entity.kind, entity.entity_id) for entity in item.entity_refs),
            ),
        )
    )
    conflict_codes = tuple(sorted({item.code for item in conflicts_tuple}))
    canonical_tie_decision_ids = view.tie_breaks[0].decision_ids
    result = ExactEvaluation(
        view_id=view.view_id,
        candidate_id=candidate.candidate_id,
        feasible=not conflicts_tuple,
        constraints=tuple(sorted(constraints, key=lambda item: item.ref_id)),
        objectives=objectives,
        conflict_codes=conflict_codes,
        candidate_valid=True,
        conflicts=conflicts_tuple,
        postings=state.postings,
        funding_transfers=state.funding_transfers,
        funding_sources=state.funding_sources,
        fx=state.fx,
        orders=state.orders,
        ledgers=state.ledgers,
        holdings=state.holdings,
        assets=state.assets,
        accounting=state.accounting,
        costs=state.costs,
        canonical_tie_decision_ids=canonical_tie_decision_ids,
        canonical_tie_quanta=tuple(quanta[decision_id] for decision_id in canonical_tie_decision_ids),
    )
    check_budget(checkpoint)
    return result
