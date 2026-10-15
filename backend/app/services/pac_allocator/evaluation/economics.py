"""Exact economic replay of a candidate: funding, FX, orders, holdings, assets and costs, posted to the broker ledgers in native currency."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from backend.app.services.pac_allocator.evaluation.bounds import current_invested, selected_funding
from backend.app.services.pac_allocator.evaluation.errors import ExactScenarioContractError
from backend.app.services.pac_allocator.evaluation.keys import entity_refs, exact_decision_id, fx_debit_key, source_key
from backend.app.services.pac_allocator.evaluation.reachability import buy_pool_currencies, source_reachability
from backend.app.services.pac_allocator.evaluation.references import ledger_keys
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex, convert_currency, fx_rate, order_prices, to_valuation, valuation_rate_of
from backend.app.services.pac_allocator.ledger import (
    exact_flow_posting,
    reconcile_broker_ledgers,
    rounded_money_posting,
)
from backend.app.services.pac_allocator.models import (
    Checkpoint,
    DecisionFamily,
    EntityRef,
    ExactAccountingEvaluation,
    ExactAssetEvaluation,
    ExactBrokerLedgerEvaluation,
    ExactCostEvaluation,
    ExactFundingSourceEvaluation,
    ExactFundingTransferEvaluation,
    ExactFxEvaluation,
    ExactHoldingEvaluation,
    ExactLedgerPosting,
    ExactOrderEvaluation,
    ExactOrderRoute,
    ExactPlannerScenario,
    LedgerPostingFamily,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
    calculate_fee,
    calculate_fx_credit,
    calculate_planning_fx_rate,
    calculate_tax_reserve,
    calculate_taxable_gain,
)

_EXACT_ZERO = ExactRatio(0)


@dataclass(frozen=True, slots=True)
class EconomicState:
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
    index: ScenarioIndex,
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
            entity_refs=entity_refs(("existing_cash", cash.cash_id)),
        )

    for route in scenario.funding_routes:
        check_budget(checkpoint)
        decision_id = exact_decision_id(
            "funding_transfer",
            route.route_id,
        )
        decision_quanta = quanta[decision_id]
        amount = index.currency_quantum[route.currency] * decision_quanta
        transferred_by_source[source_key(route.source_kind, route.source_id)] += amount
        transferred_by_route[route.route_id] = amount
        if amount == _EXACT_ZERO:
            continue
        route_refs = entity_refs(("funding_route", route.route_id))
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
        key = source_key("existing_cash", cash.cash_id)
        transferred = transferred_by_source[key]
        remaining = cash.selected.amount - transferred
        reachable_amount, trapped_amount = source_reachability(
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
        key = source_key(
            "contribution",
            contribution.contribution_id,
        )
        transferred = transferred_by_source[key]
        remaining = contribution.amount.amount - transferred
        reachable_amount, trapped_amount = source_reachability(
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
    index: ScenarioIndex,
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
        for currency in buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            decision_id = exact_decision_id(
                "fx_debit",
                fx_debit_key(route.route_id, currency),
            )
            decision_quanta = quanta[decision_id]
            if decision_quanta == 0:
                continue
            source_debit = index.currency_quantum[currency] * decision_quanta
            approved_rate = fx_rate(index.fx_rate_by_pair, currency, quote_currency)
            # The planning rate: the spread rate, capped at the triangle through
            # the valuation currency, so no conversion creates value.
            source_valuation_rate = valuation_rate_of(index, currency)
            destination_valuation_rate = valuation_rate_of(index, quote_currency)
            effective_rate = calculate_planning_fx_rate(
                approved_rate=approved_rate,
                spread=scenario.fx_spread_rate,
                source_valuation_rate=source_valuation_rate,
                destination_valuation_rate=destination_valuation_rate,
            )
            exact_credit = calculate_fx_credit(
                source_debit=source_debit,
                approved_rate=approved_rate,
                spread=scenario.fx_spread_rate,
                source_valuation_rate=source_valuation_rate,
                destination_valuation_rate=destination_valuation_rate,
            )
            posting_refs = entity_refs(
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
            spread_loss = to_valuation(index, source_debit, currency) - to_valuation(
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
    index: ScenarioIndex,
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
    unit_cost = convert_currency(
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
    index: ScenarioIndex,
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
        prices = order_prices(index, route)
        order_measure = capability.order_step * decision_quanta
        if capability.kind == "whole_quantity":
            economic_quantity = order_measure
            exact_cash = economic_quantity * prices.execution_native
        else:
            exact_cash = order_measure
            economic_quantity = order_measure / prices.execution_native
        native_mid_value = economic_quantity * prices.mid_native
        mid_value = to_valuation(
            index,
            native_mid_value,
            quote_currency,
        )
        execution_margin_loss = (
            to_valuation(
                index,
                exact_cash - native_mid_value,
                quote_currency,
            )
            if route.side == "buy"
            else to_valuation(
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
        route_refs = entity_refs(
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
    index: ScenarioIndex,
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
        current_by_asset[holding.asset_id] += to_valuation(
            index,
            holding.initial_quantity * source_unit,
            asset.quote.price.currency,
        )
        final_by_asset[holding.asset_id] += to_valuation(
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
    index: ScenarioIndex,
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
        fee_value = to_valuation(
            index,
            order.exact_fee,
            order.native_currency,
        )
        if order.side == "buy":
            buy_fees += fee_value
        else:
            sell_fees += fee_value
            tax_value = to_valuation(
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


def evaluate_economic_state(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    quanta: Mapping[str, int],
    checkpoint: Checkpoint | None,
) -> EconomicState:
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
        ledger_keys=ledger_keys(scenario, index),
        postings=postings_tuple,
        checkpoint=checkpoint,
    )
    holdings = _evaluate_holdings(scenario, orders, checkpoint)
    invested_value = current_invested(
        scenario,
        index,
        checkpoint,
    )
    selected_value = selected_funding(
        scenario,
        index,
        checkpoint,
    )
    reachable_funding = _EXACT_ZERO
    for source in funding_sources:
        check_budget(checkpoint)
        reachable_funding += to_valuation(
            index,
            source_reachability(
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
    trapped_funding = selected_value - reachable_funding
    fixed_reference = invested_value + reachable_funding
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
            to_valuation(
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
            to_valuation(
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
            to_valuation(
                index,
                posting.accounting_rounding_adjustment,
                posting.currency,
            )
            for posting in postings_tuple
        ),
        _EXACT_ZERO,
    )
    # The band: one minor unit per rounded posting, valued in the scenario
    # currency. Every posting rounds against the plan, so the aggregate
    # adjustment lies in [0, sum of quanta) however many movements a plan
    # has; the strict rule stays per posting (``ledger._validate_posting``).
    rounding_bound = sum(
        (
            to_valuation(
                index,
                posting.quantum,
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
        current_invested=invested_value,
        selected_funding=selected_value,
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
    return EconomicState(
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
