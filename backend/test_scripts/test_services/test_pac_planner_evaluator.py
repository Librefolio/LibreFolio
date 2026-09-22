"""Focused exact-policy, evaluator, and native-ledger contract tests.

All scenarios are small, pure, in-memory witnesses built directly from the
frozen exact records.  They intentionally do not reuse the medium public
fixture, call a solver/oracle, use presentation-number projections, or touch
the database, server, clock, or network.

The public contracts below are asserted without a compatibility workaround.
Checkpointed constraint construction and Broker-scoped funding/order tie
lookups execute through the real frozen entry points.  No suppression or
runtime patch masks a production failure, and no fabricated replay can make
these tests green for the wrong reason.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, date, datetime
from hashlib import sha256
from inspect import currentframe
from typing import Any

import pytest

from backend.app.schemas.pac_allocator import PacPlannerRequest
from backend.app.services.pac_allocator.evaluator import (
    ExactEvaluatorError,
    ExactPolicyContractError,
    ExactScenarioContractError,
    _asset_broker_key,
    _fx_debit_key,
    build_exact_policy_view,
    evaluate_exact_candidate,
    exact_decision_id,
    exact_scenario_fingerprint,
)
from backend.app.services.pac_allocator.ledger import (
    DuplicatePostingError,
    ExactLedgerError,
    PostingFamilyError,
    exact_flow_posting,
    reconcile_broker_ledgers,
    rounded_money_posting,
)
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    DecisionAccess,
    EntityRef,
    ExactAsset,
    ExactAssetQuote,
    ExactAssetTax,
    ExactBroker,
    ExactContribution,
    ExactCostBasis,
    ExactCurrencySpec,
    ExactExistingCash,
    ExactFeeSchedule,
    ExactFreshness,
    ExactFundingRoute,
    ExactFxRate,
    ExactHolding,
    ExactLedgerPosting,
    ExactMoney,
    ExactOrderCap,
    ExactOrderCapability,
    ExactOrderMinimum,
    ExactOrderRoute,
    ExactPlannerScenario,
    ExactPolicyView,
    ExactProvenance,
    ExactSellContext,
    ExactSnapshot,
    ExactTargetWeight,
    ExactUnit,
    ExactWithholding,
    LedgerPostingFamily,
)
from backend.app.services.pac_allocator.normalize import normalize_planner_request
from backend.app.services.pac_allocator.numeric import ExactRatio

R = ExactRatio
ZERO = R(0)
ONE = R(1)
CENT = R(1, 100)
AS_OF = date(2026, 9, 16)
CAPTURED_AT = datetime(2026, 9, 16, 20, 0, tzinfo=UTC)
PROVENANCE_ID = "provenance:test"


def _fresh() -> ExactFreshness:
    return ExactFreshness(kind="fresh", age_days=None, accepted=False)


def _money(amount: ExactRatio, currency: str = "EUR") -> ExactMoney:
    return ExactMoney(amount=amount, currency=currency)


def _asset(
    asset_id: str,
    *,
    price: ExactRatio = R(10),
    currency: str = "EUR",
    quote_base: ExactRatio = ONE,
) -> ExactAsset:
    return ExactAsset(
        asset_id=asset_id,
        identity_kind="manual",
        source_asset_id=None,
        name=asset_id,
        ticker=None,
        asset_class="fund",
        quote=ExactAssetQuote(
            price=_money(price, currency),
            quote_base_quantity=quote_base,
            reference_date=AS_OF,
            freshness=_fresh(),
            provenance_id=PROVENANCE_ID,
        ),
        exposures=(),
    )


def _capability(
    capability_id: str,
    *,
    kind: str = "whole_quantity",
    step: ExactRatio = ONE,
) -> ExactOrderCapability:
    return ExactOrderCapability(
        capability_id=capability_id,
        kind=kind,
        order_step=step,
    )


def _fee(
    fee_id: str,
    capability_id: str,
    side: str,
    *,
    currency: str = "EUR",
    fixed: ExactRatio = ZERO,
    rate: ExactRatio = ZERO,
    floor: ExactRatio = ZERO,
    cap: ExactRatio | None = None,
) -> ExactFeeSchedule:
    return ExactFeeSchedule(
        fee_schedule_id=fee_id,
        capability_id=capability_id,
        side=side,
        fixed_fee=_money(fixed, currency),
        proportional_rate=rate,
        minimum_fee=_money(floor, currency),
        maximum_fee=None if cap is None else _money(cap, currency),
    )


def _broker(
    broker_id: str,
    capabilities: Iterable[ExactOrderCapability] = (),
    fees: Iterable[ExactFeeSchedule] = (),
    *,
    active: bool | None = True,
    domain: bool = False,
) -> ExactBroker:
    return ExactBroker(
        broker_id=broker_id,
        identity_kind="domain" if domain else "manual",
        source_broker_id=f"source:{broker_id}" if domain else None,
        name=broker_id,
        active=active,
        provenance_id=PROVENANCE_ID,
        capabilities=tuple(sorted(capabilities, key=lambda item: item.capability_id)),
        fee_schedules=tuple(
            sorted(
                fees,
                key=lambda item: (
                    item.capability_id,
                    item.side,
                    item.fee_schedule_id,
                ),
            )
        ),
    )


def _minimum(
    capability: ExactOrderCapability,
    value: ExactRatio = ZERO,
    currency: str = "EUR",
) -> ExactOrderMinimum:
    if value == ZERO:
        return ExactOrderMinimum(kind="none", value=ZERO, currency=None)
    if capability.kind == "whole_quantity":
        return ExactOrderMinimum(
            kind="whole_quantity",
            value=value,
            currency=None,
        )
    return ExactOrderMinimum(
        kind="monetary_amount",
        value=value,
        currency=currency,
    )


def _order_route(
    route_id: str,
    *,
    broker_id: str,
    asset_id: str,
    capability: ExactOrderCapability,
    fee_id: str,
    side: str,
    minimum: ExactRatio = ZERO,
    required: ExactRatio = ZERO,
    cap: ExactRatio = R(100),
    margin: ExactRatio = ZERO,
    priority: int = 0,
    currency: str = "EUR",
) -> ExactOrderRoute:
    cap_kind = "quantity" if capability.kind == "whole_quantity" else "notional"
    cap_currency = None if capability.kind == "whole_quantity" else currency
    return ExactOrderRoute(
        route_id=route_id,
        broker_id=broker_id,
        asset_id=asset_id,
        capability_id=capability.capability_id,
        fee_schedule_id=fee_id,
        side=side,
        minimum_if_active=_minimum(capability, minimum, currency),
        required_minimum=_minimum(capability, required, currency),
        cap=ExactOrderCap(
            kind=cap_kind,
            value=cap,
            currency=cap_currency,
        ),
        execution_margin_rate=margin,
        priority=priority,
        provenance_id=PROVENANCE_ID,
    )


def _holding(
    holding_id: str,
    asset_id: str,
    broker_id: str,
    quantity: ExactRatio,
) -> ExactHolding:
    return ExactHolding(
        holding_id=holding_id,
        asset_id=asset_id,
        broker_id=broker_id,
        custody_quantity=quantity,
        economic_share=ONE,
        economic_quantity=quantity,
        planning_quantity=quantity,
        provenance_id=PROVENANCE_ID,
    )


def _sell_context(
    *,
    holdings: Iterable[ExactHolding],
    asset_ids: Iterable[str],
    broker_ids: Iterable[str],
    currency: str = "EUR",
    unit_costs: dict[str, ExactRatio] | None = None,
    tax_rate: ExactRatio = ZERO,
    withholding_kind: str = "broker_withheld",
    carried_loss: ExactRatio = ZERO,
) -> ExactSellContext:
    costs = unit_costs or {}
    holding_rows = tuple(holdings)
    return ExactSellContext(
        cost_basis=tuple(
            sorted(
                (
                    ExactCostBasis(
                        holding_id=holding.holding_id,
                        average_unit_cost=_money(
                            costs.get(holding.asset_id, R(5)),
                            currency,
                        ),
                        reference_date=AS_OF,
                        provenance_id=PROVENANCE_ID,
                    )
                    for holding in holding_rows
                ),
                key=lambda item: item.holding_id,
            )
        ),
        asset_tax=tuple(
            ExactAssetTax(
                asset_id=asset_id,
                fiscal_currency=currency,
                gain_tax_rate=tax_rate,
                provenance_id=PROVENANCE_ID,
            )
            for asset_id in sorted(asset_ids)
        ),
        withholding=tuple(
            ExactWithholding(
                broker_id=broker_id,
                fiscal_currency=currency,
                carried_loss_available=_money(carried_loss, currency),
                withholding_kind=withholding_kind,
                reference_date=AS_OF,
                provenance_id=PROVENANCE_ID,
            )
            for broker_id in sorted(broker_ids)
        ),
    )


def _scenario(
    scenario_id: str,
    *,
    product: str,
    policy: str,
    assets: Iterable[ExactAsset],
    brokers: Iterable[ExactBroker],
    holdings: Iterable[ExactHolding] = (),
    existing_cash: Iterable[ExactExistingCash] = (),
    contributions: Iterable[ExactContribution] = (),
    funding_routes: Iterable[ExactFundingRoute] = (),
    order_routes: Iterable[ExactOrderRoute] = (),
    fx_rates: Iterable[ExactFxRate] = (),
    fx_spread_rate: ExactRatio = ZERO,
    currency_quantums: Iterable[tuple[str, ExactRatio]] = (("EUR", CENT),),
    target_weights: Iterable[ExactTargetWeight] | None = None,
    sell_context: ExactSellContext | None = None,
) -> ExactPlannerScenario:
    asset_rows = tuple(sorted(assets, key=lambda item: item.asset_id))
    targets = (
        tuple(
            ExactTargetWeight(
                asset_id=asset.asset_id,
                weight=R(1, len(asset_rows)),
            )
            for asset in asset_rows
        )
        if target_weights is None
        else tuple(sorted(target_weights, key=lambda item: item.asset_id))
    )
    return ExactPlannerScenario(
        snapshot=ExactSnapshot(
            snapshot_id=scenario_id,
            draft_revision=7,
            captured_at=CAPTURED_AT,
        ),
        product=product,
        policy=policy,
        as_of_date=AS_OF,
        valuation_currency="EUR",
        currency_specs=tuple(ExactCurrencySpec(currency=currency, minor_unit=quantum) for currency, quantum in sorted(currency_quantums)),
        provenance=(
            ExactProvenance(
                provenance_id=PROVENANCE_ID,
                kind="manual",
                label="test",
                entered_at=CAPTURED_AT,
                domain=None,
                source_ref=None,
                source_label=None,
                captured_at=CAPTURED_AT,
            ),
        ),
        fx_rates=tuple(sorted(fx_rates, key=lambda item: (item.pair_first, item.pair_second))),
        fx_spread_rate=fx_spread_rate,
        assets=asset_rows,
        brokers=tuple(sorted(brokers, key=lambda item: item.broker_id)),
        holdings=tuple(sorted(holdings, key=lambda item: item.holding_id)),
        existing_cash=tuple(sorted(existing_cash, key=lambda item: item.cash_id)),
        contributions=tuple(sorted(contributions, key=lambda item: item.contribution_id)),
        funding_routes=tuple(sorted(funding_routes, key=lambda item: item.route_id)),
        order_routes=tuple(sorted(order_routes, key=lambda item: item.route_id)),
        target_weights=targets,
        sell_context=sell_context,
    )


def _cash(
    cash_id: str,
    broker_id: str,
    amount: ExactRatio,
    *,
    currency: str = "EUR",
    available: ExactRatio | None = None,
) -> ExactExistingCash:
    return ExactExistingCash(
        source_kind="local_broker_cash",
        cash_id=cash_id,
        broker_id=broker_id,
        available=_money(amount if available is None else available, currency),
        selected=_money(amount, currency),
        provenance_id=PROVENANCE_ID,
    )


def _contribution(
    contribution_id: str,
    amount: ExactRatio,
    *,
    currency: str = "EUR",
) -> ExactContribution:
    return ExactContribution(
        contribution_id=contribution_id,
        label=contribution_id,
        amount=_money(amount, currency),
        provenance_id=PROVENANCE_ID,
    )


def _fx_rate(
    pair_first: str,
    pair_second: str,
    rate: ExactRatio,
) -> ExactFxRate:
    return ExactFxRate(
        pair_first=pair_first,
        pair_second=pair_second,
        rate=rate,
    )


def _funding_route(
    route_id: str,
    *,
    broker_id: str,
    source_kind: str,
    source_id: str,
    amount: ExactRatio,
    currency: str = "EUR",
    priority: int = 0,
) -> ExactFundingRoute:
    return ExactFundingRoute(
        route_id=route_id,
        broker_id=broker_id,
        source_kind=source_kind,
        source_id=source_id,
        currency=currency,
        transfer_cap=_money(amount, currency),
        priority=priority,
        provenance_id=PROVENANCE_ID,
    )


def _planner_request_with_whole_step(
    quantity_step: str,
) -> PacPlannerRequest:
    return PacPlannerRequest.model_validate(
        {
            "operation": "plan",
            "snapshot": {
                "snapshot_id": "snapshot:whole-step",
                "draft_revision": 7,
                "captured_at": "2026-09-16T20:00:00Z",
            },
            "as_of": "2026-09-16",
            "valuation_currency": "EUR",
            "currency_specs": [
                {
                    "currency": "EUR",
                    "minor_unit": "0.01",
                }
            ],
            "provenance": [
                {
                    "kind": "manual",
                    "provenance_id": PROVENANCE_ID,
                    "label": "test",
                    "entered_at": "2026-09-16T20:00:00Z",
                }
            ],
            "fx_rates": {},
            "fx_spread_rate": "0",
            "assets": [
                {
                    "asset_id": "asset:a",
                    "identity": {
                        "kind": "manual_asset",
                        "name": "Asset A",
                        "ticker": None,
                        "asset_class": "fund",
                    },
                    "quote": {
                        "amount": "10",
                        "currency": "EUR",
                        "quote_base_quantity": "1",
                        "reference_date": "2026-09-16",
                        "freshness": {"kind": "fresh"},
                        "provenance_id": PROVENANCE_ID,
                    },
                    "exposures": [],
                }
            ],
            "brokers": [
                {
                    "broker_id": "broker:a",
                    "identity": {
                        "kind": "manual_broker",
                        "name": "Broker A",
                    },
                    "provenance_id": PROVENANCE_ID,
                    "capabilities": [
                        {
                            "kind": "whole_quantity",
                            "capability_id": "capability:whole",
                            "quantity_unit": "asset_unit",
                            "quantity_step": quantity_step,
                        }
                    ],
                    "fee_schedules": [
                        {
                            "fee_schedule_id": "fee:buy",
                            "capability_id": "capability:whole",
                            "side": "buy",
                            "fixed_fee": {
                                "amount": "0",
                                "currency": "EUR",
                            },
                            "rate": "0",
                            "variable_floor": {
                                "amount": "0",
                                "currency": "EUR",
                            },
                            "variable_cap": {"kind": "none"},
                        }
                    ],
                }
            ],
            "existing_cash": [
                {
                    "source_kind": "local_broker_cash",
                    "cash_id": "cash:a",
                    "broker_id": "broker:a",
                    "available": {
                        "amount": "100",
                        "currency": "EUR",
                    },
                    "selected": {
                        "amount": "100",
                        "currency": "EUR",
                    },
                    "provenance_id": PROVENANCE_ID,
                }
            ],
            "contributions": [],
            "funding_routes": [],
            "target_weights": [
                {
                    "asset_id": "asset:a",
                    "weight": "1",
                }
            ],
            "order_routes": [
                {
                    "route_id": "route:buy:a",
                    "asset_id": "asset:a",
                    "broker_id": "broker:a",
                    "capability_id": "capability:whole",
                    "side": "buy",
                    "priority": 0,
                    "minimum_if_active": {"kind": "none"},
                    "required_minimum": {"kind": "none"},
                    "cap": {
                        "kind": "quantity",
                        "quantity": "100",
                        "unit": "asset_unit",
                    },
                    "execution_margin_rate": "0",
                    "fee_schedule_id": "fee:buy",
                    "provenance_id": PROVENANCE_ID,
                }
            ],
            "policy": "proportional",
        }
    )


def _pac_scenario(
    *,
    policy: str = "proportional",
    price: ExactRatio = R(10),
    quote_base: ExactRatio = ONE,
    quote_currency: str = "EUR",
    capability_kind: str = "whole_quantity",
    step: ExactRatio = ONE,
    cash: ExactRatio = R(100),
    fixed_fee: ExactRatio = ZERO,
    fee_rate: ExactRatio = ZERO,
    fee_floor: ExactRatio = ZERO,
    fee_cap: ExactRatio | None = None,
    minimum: ExactRatio = ZERO,
    required: ExactRatio = ZERO,
    route_cap: ExactRatio = R(100),
    margin: ExactRatio = ZERO,
    priority: int = 7,
    scenario_id: str = "scenario:pac",
) -> ExactPlannerScenario:
    capability = _capability(
        "capability:a",
        kind=capability_kind,
        step=step,
    )
    fee = _fee(
        "fee:buy:a",
        capability.capability_id,
        "buy",
        currency=quote_currency,
        fixed=fixed_fee,
        rate=fee_rate,
        floor=fee_floor,
        cap=fee_cap,
    )
    return _scenario(
        scenario_id,
        product="pac",
        policy=policy,
        assets=(
            _asset(
                "asset:a",
                price=price,
                currency=quote_currency,
                quote_base=quote_base,
            ),
        ),
        brokers=(_broker("broker:a", (capability,), (fee,)),),
        existing_cash=(
            _cash(
                "cash:a",
                "broker:a",
                cash,
                currency=quote_currency,
            ),
        ),
        order_routes=(
            _order_route(
                "route:buy:a",
                broker_id="broker:a",
                asset_id="asset:a",
                capability=capability,
                fee_id=fee.fee_schedule_id,
                side="buy",
                minimum=minimum,
                required=required,
                cap=route_cap,
                margin=margin,
                priority=priority,
                currency=quote_currency,
            ),
        ),
        currency_quantums=((quote_currency, CENT),),
    )


def _min_fragmentation_scenario(
    *,
    permuted_inputs: bool = False,
) -> ExactPlannerScenario:
    capability_a = _capability("capability:a")
    capability_b = _capability("capability:b")
    fee_a = _fee("fee:buy:a", capability_a.capability_id, "buy")
    fee_b = _fee("fee:buy:b", capability_b.capability_id, "buy")
    broker_a = _broker("broker:a", (capability_a,), (fee_a,))
    broker_b = _broker("broker:b", (capability_b,), (fee_b,))
    route_a = _order_route(
        "route:buy:a",
        broker_id=broker_a.broker_id,
        asset_id="asset:a",
        capability=capability_a,
        fee_id=fee_a.fee_schedule_id,
        side="buy",
        cap=R(5),
        priority=1,
    )
    route_b = _order_route(
        "route:buy:b",
        broker_id=broker_b.broker_id,
        asset_id="asset:a",
        capability=capability_b,
        fee_id=fee_b.fee_schedule_id,
        side="buy",
        cap=R(5),
        priority=3,
    )
    brokers = (broker_b, broker_a) if permuted_inputs else (broker_a, broker_b)
    routes = (route_b, route_a) if permuted_inputs else (route_a, route_b)
    cash = (
        _cash("cash:b", "broker:b", R(50)),
        _cash("cash:a", "broker:a", R(50)),
    )
    if not permuted_inputs:
        cash = tuple(reversed(cash))
    return _scenario(
        "scenario:min-fragmentation",
        product="pac",
        policy="min_fragmentation",
        assets=(_asset("asset:a"),),
        brokers=brokers,
        existing_cash=cash,
        order_routes=routes,
    )


def _funding_fx_scenario() -> ExactPlannerScenario:
    capability = _capability("capability:usd")
    buy_fee = _fee(
        "fee:buy:usd",
        capability.capability_id,
        "buy",
        currency="USD",
    )
    destination = _broker(
        "broker:destination",
        (capability,),
        (buy_fee,),
    )
    source = _broker("broker:source")
    return _scenario(
        "scenario:funding-fx",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(100), currency="USD"),),
        brokers=(destination, source),
        existing_cash=(_cash("cash:source", source.broker_id, R(200)),),
        funding_routes=(
            _funding_route(
                "route:funding:eur",
                broker_id=destination.broker_id,
                source_kind="existing_cash",
                source_id="cash:source",
                amount=R(200),
                priority=2,
            ),
        ),
        order_routes=(
            _order_route(
                "route:buy:usd",
                broker_id=destination.broker_id,
                asset_id="asset:a",
                capability=capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(2),
                priority=5,
            ),
        ),
        fx_rates=(_fx_rate("EUR", "USD", R(6, 5)),),
        fx_spread_rate=R(1, 100),
        currency_quantums=(("EUR", CENT), ("USD", CENT)),
    )


def _invest_only_scenario() -> ExactPlannerScenario:
    capability = _capability("capability:whole")
    buy_fee = _fee("fee:buy", capability.capability_id, "buy")
    broker = _broker("broker:a", (capability,), (buy_fee,))
    holdings = (
        _holding("holding:a", "asset:a", broker.broker_id, R(8)),
        _holding("holding:b", "asset:b", broker.broker_id, R(2)),
    )
    contribution = _contribution("contribution:a", R(20))
    return _scenario(
        "scenario:invest-only",
        product="rebalancer",
        policy="invest_only",
        assets=(_asset("asset:a"), _asset("asset:b")),
        brokers=(broker,),
        holdings=holdings,
        contributions=(contribution,),
        funding_routes=(
            _funding_route(
                "route:funding",
                broker_id=broker.broker_id,
                source_kind="contribution",
                source_id=contribution.contribution_id,
                amount=R(20),
            ),
        ),
        order_routes=(
            _order_route(
                "route:buy:a",
                broker_id=broker.broker_id,
                asset_id="asset:a",
                capability=capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(10),
            ),
            _order_route(
                "route:buy:b",
                broker_id=broker.broker_id,
                asset_id="asset:b",
                capability=capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(10),
            ),
        ),
    )


def _invest_and_sell_scenario(
    *,
    contribution_amount: ExactRatio = R(20),
    sell_fixed: ExactRatio = ZERO,
    sell_rate: ExactRatio = ZERO,
    sell_floor: ExactRatio = ZERO,
    sell_cap: ExactRatio | None = None,
    tax_rate: ExactRatio = ZERO,
    withholding_kind: str = "broker_withheld",
    carried_loss: ExactRatio = ZERO,
    monetary_sell: bool = False,
    sell_step: ExactRatio = ONE,
    sell_minimum: ExactRatio = ZERO,
    sell_required: ExactRatio = ZERO,
    zero_domain_sell: bool = False,
) -> ExactPlannerScenario:
    buy_capability = _capability("capability:buy")
    sell_capability = _capability(
        "capability:sell",
        kind="monetary_amount" if monetary_sell else "whole_quantity",
        step=sell_step,
    )
    buy_fee = _fee("fee:buy", buy_capability.capability_id, "buy")
    sell_fee = _fee(
        "fee:sell",
        sell_capability.capability_id,
        "sell",
        fixed=sell_fixed,
        rate=sell_rate,
        floor=sell_floor,
        cap=sell_cap,
    )
    broker = _broker(
        "broker:a",
        (buy_capability, sell_capability),
        (buy_fee, sell_fee),
    )
    holdings = (
        _holding("holding:a", "asset:a", broker.broker_id, R(8)),
        _holding("holding:b", "asset:b", broker.broker_id, R(2)),
    )
    contribution = _contribution(
        "contribution:a",
        contribution_amount,
    )
    sell_a_cap = R(80) if monetary_sell else R(8)
    sell_b_cap = R(20) if monetary_sell else R(2)
    sell_routes = [
        _order_route(
            "route:sell:a",
            broker_id=broker.broker_id,
            asset_id="asset:a",
            capability=sell_capability,
            fee_id=sell_fee.fee_schedule_id,
            side="sell",
            minimum=sell_minimum,
            required=sell_required,
            cap=sell_a_cap,
            priority=4,
        ),
        _order_route(
            "route:sell:b",
            broker_id=broker.broker_id,
            asset_id="asset:b",
            capability=sell_capability,
            fee_id=sell_fee.fee_schedule_id,
            side="sell",
            cap=sell_b_cap,
            priority=5,
        ),
    ]
    if zero_domain_sell:
        sell_routes.append(
            _order_route(
                "route:sell:a:zero-domain",
                broker_id=broker.broker_id,
                asset_id="asset:a",
                capability=sell_capability,
                fee_id=sell_fee.fee_schedule_id,
                side="sell",
                cap=R(1, 2),
                priority=6,
            )
        )
    context = _sell_context(
        holdings=holdings,
        asset_ids=("asset:a", "asset:b"),
        broker_ids=(broker.broker_id,),
        unit_costs={"asset:a": R(5), "asset:b": R(8)},
        tax_rate=tax_rate,
        withholding_kind=withholding_kind,
        carried_loss=carried_loss,
    )
    return _scenario(
        "scenario:invest-and-sell",
        product="rebalancer",
        policy="invest_and_sell",
        assets=(_asset("asset:a"), _asset("asset:b")),
        brokers=(broker,),
        holdings=holdings,
        contributions=(contribution,),
        funding_routes=(
            _funding_route(
                "route:funding",
                broker_id=broker.broker_id,
                source_kind="contribution",
                source_id=contribution.contribution_id,
                amount=contribution_amount,
                priority=1,
            ),
        ),
        order_routes=(
            _order_route(
                "route:buy:a",
                broker_id=broker.broker_id,
                asset_id="asset:a",
                capability=buy_capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(10),
                priority=2,
            ),
            _order_route(
                "route:buy:b",
                broker_id=broker.broker_id,
                asset_id="asset:b",
                capability=buy_capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(10),
                priority=3,
            ),
            *sell_routes,
        ),
        sell_context=context,
    )


def _by_id(rows: Iterable[Any], field: str, value: str) -> Any:
    matches = tuple(row for row in rows if getattr(row, field) == value)
    assert len(matches) == 1, f"Expected one {field}={value!r}, found " f"{tuple(getattr(row, field) for row in matches)!r}"
    (match,) = matches
    return match


def _decision(view: ExactPolicyView, decision_id: str) -> DecisionAccess:
    return _by_id(view.decisions, "decision_id", decision_id)


def _candidate(
    view: ExactPolicyView,
    values: dict[str, int] | None = None,
    *,
    candidate_id: str = "candidate:test",
    view_id: str | None = None,
) -> CandidateActionVector:
    supplied = values or {}
    return CandidateActionVector(
        view_id=view.view_id if view_id is None else view_id,
        candidate_id=candidate_id,
        decisions=tuple(
            CandidateDecision(
                decision_id=access.decision_id,
                quanta=supplied.get(
                    access.decision_id,
                    access.baseline_quanta,
                ),
            )
            for access in view.decisions
        ),
    )


def _unsafe_candidate_decision(
    decision_id: str,
    quanta: object,
) -> CandidateDecision:
    decision = object.__new__(CandidateDecision)
    object.__setattr__(decision, "decision_id", decision_id)
    object.__setattr__(decision, "quanta", quanta)
    return decision


def _unsafe_candidate_vector(
    *,
    view_id: str,
    candidate_id: str,
    decisions: tuple[CandidateDecision, ...],
) -> CandidateActionVector:
    candidate = object.__new__(CandidateActionVector)
    object.__setattr__(candidate, "view_id", view_id)
    object.__setattr__(candidate, "candidate_id", candidate_id)
    object.__setattr__(candidate, "decisions", decisions)
    return candidate


def _candidate_with_unsafe_quanta(
    candidate: CandidateActionVector,
    decision_id: str,
    quanta: object,
) -> CandidateActionVector:
    return _unsafe_candidate_vector(
        view_id=candidate.view_id,
        candidate_id=candidate.candidate_id,
        decisions=tuple(_unsafe_candidate_decision(item.decision_id, quanta) if item.decision_id == decision_id else item for item in candidate.decisions),
    )


def _integer_quanta(value: ExactRatio, quantum: ExactRatio = CENT) -> int:
    scaled = value / quantum
    assert scaled.denominator == 1
    return scaled.numerator


def _invest_only_baseline(
    scenario: ExactPlannerScenario,
    *,
    buy_b_quanta: int = 2,
) -> tuple[ExactPolicyView, CandidateActionVector]:
    view = build_exact_policy_view(
        scenario,
        purpose="invest_only_baseline",
        view_id="view:invest-only",
    )
    contribution = _by_id(
        scenario.contributions,
        "contribution_id",
        "contribution:a",
    )
    candidate = _candidate(
        view,
        {
            exact_decision_id("funding_transfer", "route:funding"): (_integer_quanta(contribution.amount.amount)),
            exact_decision_id("buy_quantum", "route:buy:b"): buy_b_quanta,
        },
        candidate_id="candidate:invest-only",
    )
    return view, candidate


def _sell_extension(
    scenario: ExactPlannerScenario,
    baseline: CandidateActionVector,
) -> ExactPolicyView:
    return build_exact_policy_view(
        scenario,
        purpose="sell_extension",
        baseline=baseline,
        view_id="view:sell-extension",
    )


def _assert_invalid_candidate_has_no_replay(
    evaluation: Any,
    expected_codes: tuple[str, ...],
) -> None:
    assert evaluation.candidate_valid is False
    assert evaluation.feasible is False
    assert evaluation.conflict_codes == tuple(sorted(expected_codes))
    assert evaluation.constraints == ()
    assert evaluation.objectives == ()
    assert evaluation.postings == ()
    assert evaluation.funding_transfers == ()
    assert evaluation.funding_sources == ()
    assert evaluation.fx == ()
    assert evaluation.orders == ()
    assert evaluation.ledgers == ()
    assert evaluation.holdings == ()
    assert evaluation.assets == ()
    assert evaluation.accounting is None
    assert evaluation.costs is None
    assert evaluation.canonical_tie_decision_ids == ()
    assert evaluation.canonical_tie_quanta == ()


class _Cancelled(RuntimeError):
    """Test-only cooperative cancellation sentinel."""


class _CancelIn:
    def __init__(self, function_name: str) -> None:
        self.function_name = function_name
        self.observed = False

    def __call__(self) -> None:
        frame = currentframe()
        try:
            while frame is not None:
                if frame.f_code.co_name == self.function_name:
                    self.observed = True
                    raise _Cancelled(self.function_name)
                frame = frame.f_back
        finally:
            del frame


class _ObserveIn:
    def __init__(self, function_name: str) -> None:
        self.function_name = function_name
        self.observed = False

    def __call__(self) -> None:
        frame = currentframe()
        try:
            while frame is not None:
                if frame.f_code.co_name == self.function_name:
                    self.observed = True
                    return
                frame = frame.f_back
        finally:
            del frame


def test_exact_error_taxonomies_and_public_entry_points_are_stable() -> None:
    # The P1 prototype entry points (evaluate_pac_budget, evaluate_rebalancing)
    # were dropped in b82e59ffa; the surviving set below is planner v2 only.
    assert issubclass(ExactScenarioContractError, ExactEvaluatorError)
    assert issubclass(ExactPolicyContractError, ExactEvaluatorError)
    assert issubclass(DuplicatePostingError, ExactLedgerError)
    assert issubclass(PostingFamilyError, ExactLedgerError)
    assert callable(exact_decision_id)
    assert callable(exact_scenario_fingerprint)
    assert callable(build_exact_policy_view)
    assert callable(evaluate_exact_candidate)
    assert callable(exact_flow_posting)
    assert callable(rounded_money_posting)
    assert callable(reconcile_broker_ledgers)


@pytest.mark.parametrize(
    ("family", "entity_id", "expected"),
    [
        pytest.param(
            "funding_transfer",
            "route:a",
            "funding:route:a",
            id="funding",
        ),
        pytest.param("fx_debit", "route:a", "fx:route:a", id="fx"),
        pytest.param("buy_quantum", "route:a", "buy:route:a", id="buy"),
        pytest.param("sell_quantum", "route:a", "sell:route:a", id="sell"),
    ],
)
def test_exact_decision_ids_are_stable(
    family: str,
    entity_id: str,
    expected: str,
) -> None:
    assert exact_decision_id(family, entity_id) == expected


def test_scenario_fingerprint_is_full_sha256_of_exact_canonical_state() -> None:
    scenario = _pac_scenario()
    expected = sha256(repr(scenario).encode("utf-8")).hexdigest()

    fingerprint = exact_scenario_fingerprint(scenario)

    assert fingerprint == expected
    assert len(fingerprint) == 64
    assert fingerprint != exact_scenario_fingerprint(
        replace(
            scenario,
            snapshot=replace(scenario.snapshot, draft_revision=8),
        )
    )


def test_policy_view_exposes_complete_exact_vector_with_stable_ids() -> None:
    scenario = _funding_fx_scenario()

    view = build_exact_policy_view(scenario)

    fx_debit_id = exact_decision_id("fx_debit", _fx_debit_key("route:buy:usd", "EUR"))
    expected = {
        exact_decision_id("funding_transfer", "route:funding:eur"),
        fx_debit_id,
        exact_decision_id("buy_quantum", "route:buy:usd"),
    }
    assert {item.decision_id for item in view.decisions} == expected
    assert tuple(item.decision_id for item in view.decisions) == tuple(sorted(expected))
    assert all(item.lower_quanta == 0 for item in view.decisions)
    assert all(item.baseline_quanta == 0 for item in view.decisions)
    assert all(item.upper_quanta >= 0 for item in view.decisions)

    candidate = _candidate(
        view,
        {
            exact_decision_id(
                "funding_transfer",
                "route:funding:eur",
            ): 15_000,
            fx_debit_id: 100,
            exact_decision_id("buy_quantum", "route:buy:usd"): 1,
        },
    )
    assert tuple(item.decision_id for item in candidate.decisions) == tuple(sorted(expected))
    assert all(isinstance(item.quanta, int) for item in candidate.decisions)


def test_policy_view_build_reaches_checkpointed_constraint_refs() -> None:
    checkpoint = _ObserveIn("_build_constraint_refs")

    view = build_exact_policy_view(
        _pac_scenario(),
        checkpoint=checkpoint,
    )

    assert checkpoint.observed is True
    assert view.constraints


@pytest.mark.parametrize(
    ("case", "expected_codes"),
    [
        pytest.param(
            "view-mismatch",
            ("CANDIDATE_VIEW_MISMATCH",),
            id="view-mismatch",
        ),
        pytest.param(
            "missing",
            ("CANDIDATE_DECISION_MISSING",),
            id="missing",
        ),
        pytest.param(
            "extra",
            ("CANDIDATE_DECISION_EXTRA",),
            id="extra",
        ),
        pytest.param(
            "duplicate",
            ("CANDIDATE_DECISION_DUPLICATE",),
            id="duplicate",
        ),
        pytest.param(
            "noninteger",
            ("CANDIDATE_DECISION_OFF_GRID",),
            id="noninteger",
        ),
        pytest.param(
            "negative",
            ("CANDIDATE_DECISION_OFF_GRID",),
            id="negative",
        ),
        pytest.param(
            "out-of-bound",
            ("CANDIDATE_DECISION_OUT_OF_BOUNDS",),
            id="out-of-bound",
        ),
        pytest.param(
            "disabled",
            (
                "CANDIDATE_DECISION_DISABLED",
                "CANDIDATE_DECISION_OUT_OF_BOUNDS",
            ),
            id="disabled",
        ),
        pytest.param(
            "not-frozen",
            ("CANDIDATE_DECISION_NOT_FROZEN",),
            id="not-frozen",
        ),
        pytest.param(
            "not-additive",
            (
                "CANDIDATE_DECISION_NOT_ADDITIVE",
                "CANDIDATE_DECISION_OUT_OF_BOUNDS",
            ),
            id="not-additive",
        ),
    ],
)
def test_candidate_contract_conflicts_are_deterministic_and_skip_replay(
    case: str,
    expected_codes: tuple[str, ...],
) -> None:
    scenario = _invest_and_sell_scenario()
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    valid = _candidate(view, candidate_id=f"candidate:{case}")
    funding_id = exact_decision_id("funding_transfer", "route:funding")
    buy_b_id = exact_decision_id("buy_quantum", "route:buy:b")
    sell_b_id = exact_decision_id("sell_quantum", "route:sell:b")
    duplicate = _by_id(valid.decisions, "decision_id", buy_b_id)
    buy_access = _decision(view, buy_b_id)
    funding_access = _decision(view, funding_id)
    assert buy_access.baseline_quanta > 0
    assert funding_access.frozen_quanta is not None
    candidates = {
        "view-mismatch": replace(valid, view_id="view:other"),
        "missing": replace(
            valid,
            decisions=tuple(item for item in valid.decisions if item.decision_id != buy_b_id),
        ),
        "extra": replace(
            valid,
            decisions=tuple(
                sorted(
                    (
                        *valid.decisions,
                        CandidateDecision(
                            decision_id="zz-extra:decision",
                            quanta=0,
                        ),
                    ),
                    key=lambda item: item.decision_id,
                )
            ),
        ),
        "duplicate": _unsafe_candidate_vector(
            view_id=view.view_id,
            candidate_id=valid.candidate_id,
            decisions=tuple(
                sorted(
                    (*valid.decisions, duplicate),
                    key=lambda item: item.decision_id,
                )
            ),
        ),
        "noninteger": _candidate_with_unsafe_quanta(
            valid,
            buy_b_id,
            R(1, 2),
        ),
        "negative": _candidate_with_unsafe_quanta(
            valid,
            buy_b_id,
            -1,
        ),
        "out-of-bound": _candidate(
            view,
            {buy_b_id: buy_access.upper_quanta + 1},
            candidate_id=valid.candidate_id,
        ),
        "disabled": _candidate(
            view,
            {sell_b_id: 1},
            candidate_id=valid.candidate_id,
        ),
        "not-frozen": _candidate(
            view,
            {funding_id: funding_access.frozen_quanta - 1},
            candidate_id=valid.candidate_id,
        ),
        "not-additive": _candidate(
            view,
            {buy_b_id: buy_access.baseline_quanta - 1},
            candidate_id=valid.candidate_id,
        ),
    }
    candidate = candidates[case]

    evaluation = evaluate_exact_candidate(scenario, view, candidate)

    _assert_invalid_candidate_has_no_replay(
        evaluation,
        expected_codes,
    )
    assert tuple(
        (
            conflict.code,
            tuple((ref.kind, ref.entity_id) for ref in conflict.entity_refs),
        )
        for conflict in evaluation.conflicts
    ) == tuple(
        sorted(
            (
                conflict.code,
                tuple((ref.kind, ref.entity_id) for ref in conflict.entity_refs),
            )
            for conflict in evaluation.conflicts
        )
    )


@pytest.mark.parametrize(
    "quanta",
    [
        pytest.param(-1, id="negative"),
        pytest.param(True, id="boolean"),
        pytest.param(R(1), id="exact-ratio"),
    ],
)
def test_candidate_decision_constructor_rejects_noninteger_or_negative_quanta(
    quanta: object,
) -> None:
    with pytest.raises(ValueError, match="nonnegative|integer"):
        CandidateDecision(decision_id="buy:route:a", quanta=quanta)


def test_candidate_vector_rejects_noncanonical_order_before_replay() -> None:
    with pytest.raises(
        ValueError,
        match="candidate decisions must use canonical sorted order",
    ):
        CandidateActionVector(
            view_id="view:a",
            candidate_id="candidate:a",
            decisions=(
                CandidateDecision("sell:route:z", 0),
                CandidateDecision("buy:route:a", 0),
            ),
        )


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("proportional-primary", id="proportional-primary"),
        pytest.param(
            "min-fragmentation-primary",
            id="min-fragmentation-primary",
        ),
        pytest.param("invest-only-primary", id="invest-only-primary"),
        pytest.param(
            "invest-and-sell-baseline",
            id="invest-and-sell-baseline",
        ),
    ],
)
def test_primary_and_invest_only_policy_views_start_from_zero(
    case: str,
) -> None:
    if case == "proportional-primary":
        scenario = _pac_scenario(policy="proportional")
        view = build_exact_policy_view(scenario)
    elif case == "min-fragmentation-primary":
        scenario = _min_fragmentation_scenario()
        view = build_exact_policy_view(scenario)
    elif case == "invest-only-primary":
        scenario = _invest_only_scenario()
        view = build_exact_policy_view(scenario)
    elif case == "invest-and-sell-baseline":
        scenario = _invest_and_sell_scenario()
        view = build_exact_policy_view(
            scenario,
            purpose="invest_only_baseline",
        )
    else:
        raise AssertionError(f"Unknown policy-view witness {case!r}")

    assert all(item.baseline_quanta == 0 for item in view.decisions)
    assert all(item.lower_quanta == 0 for item in view.decisions)
    if view.purpose == "invest_only_baseline":
        assert all(item.mode == "disabled" for item in view.decisions if item.family == "sell_quantum")


def test_invest_and_sell_requires_complete_exact_feasible_baseline() -> None:
    scenario = _invest_and_sell_scenario()

    with pytest.raises(
        ExactPolicyContractError,
        match="requires.*baseline",
    ):
        build_exact_policy_view(
            scenario,
            purpose="sell_extension",
        )

    baseline_view, _baseline = _invest_only_baseline(scenario)
    infeasible = _candidate(
        baseline_view,
        {
            exact_decision_id(
                "funding_transfer",
                "route:funding",
            ): 2_000,
            exact_decision_id("buy_quantum", "route:buy:b"): 3,
        },
        candidate_id="candidate:infeasible-baseline",
    )
    baseline_evaluation = evaluate_exact_candidate(
        scenario,
        baseline_view,
        infeasible,
    )
    assert baseline_evaluation.candidate_valid is True
    assert baseline_evaluation.feasible is False
    assert "SPENDABLE_CASH_NONNEGATIVE" in (baseline_evaluation.conflict_codes)

    with pytest.raises(
        ExactPolicyContractError,
        match="baseline is not exact-feasible",
    ):
        build_exact_policy_view(
            scenario,
            purpose="sell_extension",
            baseline=infeasible,
        )


def test_sell_extension_freezes_flows_adds_buys_and_opens_only_eligible_sells() -> None:
    scenario = _invest_and_sell_scenario()
    baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)

    funding = _decision(
        view,
        exact_decision_id("funding_transfer", "route:funding"),
    )
    # NOTE: _invest_and_sell_scenario is 100% EUR-only under the redesign (no
    # fx_rates declared), so it has no fx_debit decision to freeze/inspect
    # here anymore -- the old assertion on a fabricated fx route id is gone.
    buy_a = _decision(
        view,
        exact_decision_id("buy_quantum", "route:buy:a"),
    )
    buy_b = _decision(
        view,
        exact_decision_id("buy_quantum", "route:buy:b"),
    )
    sell_a = _decision(
        view,
        exact_decision_id("sell_quantum", "route:sell:a"),
    )
    sell_b = _decision(
        view,
        exact_decision_id("sell_quantum", "route:sell:b"),
    )

    assert (
        funding.mode,
        funding.frozen_quanta,
        funding.baseline_quanta,
    ) == ("frozen_exact", 2_000, 2_000)
    assert (buy_a.mode, buy_a.lower_quanta) == ("additive_only", 0)
    assert (buy_b.mode, buy_b.lower_quanta) == ("additive_only", 2)
    assert sell_a.mode == "mutable"
    assert sell_a.upper_quanta > 0
    assert (
        sell_b.mode,
        sell_b.lower_quanta,
        sell_b.upper_quanta,
    ) == ("disabled", 0, 0)

    frozen_buy_baseline = _candidate(
        baseline_view,
        {
            exact_decision_id(
                "funding_transfer",
                "route:funding",
            ): 2_000,
            exact_decision_id("buy_quantum", "route:buy:a"): 1,
        },
        candidate_id="candidate:frozen-buy-overweight",
    )
    frozen_buy_view = _sell_extension(
        scenario,
        frozen_buy_baseline,
    )
    assert (
        _decision(
            frozen_buy_view,
            exact_decision_id("sell_quantum", "route:sell:a"),
        ).mode
        == "disabled"
    )


def test_deployment_freezes_funding_fx_and_sell_but_keeps_buy_additive() -> None:
    scenario = _invest_and_sell_scenario()
    _baseline_view, invest_only = _invest_only_baseline(scenario)
    extension = _sell_extension(scenario, invest_only)
    primary = _candidate(
        extension,
        {
            exact_decision_id("buy_quantum", "route:buy:b"): 4,
            exact_decision_id("sell_quantum", "route:sell:a"): 2,
        },
        candidate_id="candidate:primary",
    )

    deployment = build_exact_policy_view(
        scenario,
        purpose="deployment",
        baseline=primary,
    )

    for access in deployment.decisions:
        baseline_value = _by_id(
            primary.decisions,
            "decision_id",
            access.decision_id,
        ).quanta
        assert access.baseline_quanta == baseline_value
        if access.family == "buy_quantum":
            assert access.mode == "additive_only"
            assert access.lower_quanta == baseline_value
            assert access.frozen_quanta is None
        else:
            assert access.mode == "frozen_exact"
            assert access.frozen_quanta == baseline_value


@pytest.mark.parametrize(
    "purpose",
    [
        pytest.param("sell_extension", id="sell-extension"),
        pytest.param("deployment", id="deployment"),
    ],
)
def test_baseline_dependent_default_view_ids_use_full_sha256(
    purpose: str,
) -> None:
    if purpose == "sell_extension":
        scenario = _invest_and_sell_scenario()
        baseline_view = build_exact_policy_view(
            scenario,
            purpose="invest_only_baseline",
            view_id="view:invest-only",
        )
        funding_id = exact_decision_id(
            "funding_transfer",
            "route:funding",
        )
        buy_id = exact_decision_id("buy_quantum", "route:buy:b")
        first = _candidate(
            baseline_view,
            {funding_id: 2_000, buy_id: 1},
            candidate_id="candidate:first",
        )
        second = _candidate(
            baseline_view,
            {funding_id: 2_000, buy_id: 2},
            candidate_id="candidate:second",
        )
    else:
        scenario = _pac_scenario()
        baseline_view = build_exact_policy_view(
            scenario,
            view_id="view:primary",
        )
        buy_id = exact_decision_id("buy_quantum", "route:buy:a")
        first = _candidate(
            baseline_view,
            {buy_id: 0},
            candidate_id="candidate:first",
        )
        second = _candidate(
            baseline_view,
            {buy_id: 1},
            candidate_id="candidate:second",
        )

    first_view = build_exact_policy_view(
        scenario,
        purpose=purpose,
        baseline=first,
    )
    second_view = build_exact_policy_view(
        scenario,
        purpose=purpose,
        baseline=second,
    )
    first_items = tuple(sorted((item.decision_id, item.quanta) for item in first.decisions))
    second_items = tuple(sorted((item.decision_id, item.quanta) for item in second.decisions))
    first_hash = sha256(repr(first_items).encode("utf-8")).hexdigest()
    second_hash = sha256(repr(second_items).encode("utf-8")).hexdigest()

    assert first_view.view_id.endswith(f":{first_hash}")
    assert second_view.view_id.endswith(f":{second_hash}")
    assert len(first_hash) == 64
    assert len(second_hash) == 64
    assert first_view.view_id != second_view.view_id


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("missing", id="missing"),
        pytest.param("extra", id="extra"),
        pytest.param("duplicate", id="duplicate"),
        pytest.param("noninteger", id="noninteger"),
        pytest.param("negative", id="negative"),
    ],
)
def test_baseline_candidate_contract_fails_closed_without_last_wins(
    case: str,
) -> None:
    scenario = _pac_scenario()
    primary = build_exact_policy_view(
        scenario,
        view_id="view:primary",
    )
    valid = _candidate(
        primary,
        candidate_id=f"candidate:baseline:{case}",
    )
    decision_id = exact_decision_id("buy_quantum", "route:buy:a")
    decision = _by_id(valid.decisions, "decision_id", decision_id)
    if case == "missing":
        malformed = replace(valid, decisions=())
    elif case == "extra":
        malformed = replace(
            valid,
            decisions=tuple(
                sorted(
                    (
                        *valid.decisions,
                        CandidateDecision("zz-extra:decision", 0),
                    ),
                    key=lambda item: item.decision_id,
                )
            ),
        )
    elif case == "duplicate":
        malformed = _unsafe_candidate_vector(
            view_id=valid.view_id,
            candidate_id=valid.candidate_id,
            decisions=(decision, decision),
        )
    elif case in {"noninteger", "negative"}:
        malformed = _unsafe_candidate_vector(
            view_id=valid.view_id,
            candidate_id=valid.candidate_id,
            decisions=(
                _unsafe_candidate_decision(
                    decision_id,
                    R(1, 2) if case == "noninteger" else -1,
                ),
            ),
        )
    else:
        raise AssertionError(f"Unknown malformed baseline {case!r}")

    with pytest.raises(
        ExactPolicyContractError,
        match="baseline candidate|baseline decision",
    ):
        build_exact_policy_view(
            scenario,
            purpose="deployment",
            baseline=malformed,
        )


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("fingerprint", id="fingerprint"),
        pytest.param("decision-refs", id="decision-refs"),
        pytest.param("decision-bound", id="decision-bound"),
        pytest.param("constraint", id="constraint"),
        pytest.param("objective", id="objective"),
        pytest.param("tie-order", id="tie-order"),
    ],
)
def test_tampered_policy_metadata_is_rejected_with_typed_error(
    case: str,
) -> None:
    scenario = _funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    candidate = _candidate(view)

    if case == "fingerprint":
        tampered = replace(view, scenario_fingerprint="0" * 64)
    elif case in {"decision-refs", "decision-bound"}:
        decision_id = exact_decision_id(
            "buy_quantum",
            "route:buy:usd",
        )
        access = _decision(view, decision_id)
        changed = replace(access, entity_refs=()) if case == "decision-refs" else replace(access, upper_quanta=access.upper_quanta + 1)
        tampered = replace(
            view,
            decisions=tuple(changed if item.decision_id == decision_id else item for item in view.decisions),
        )
    elif case == "constraint":
        ref_id = "constraint:route_declared:global"
        ref = _by_id(view.constraints, "ref_id", ref_id)
        changed = replace(ref, bound_source="tampered source")
        tampered = replace(
            view,
            constraints=tuple(changed if item.ref_id == ref_id else item for item in view.constraints),
        )
    elif case == "objective":
        ref_id = "objective:01:fixed_l2"
        ref = _by_id(view.objectives, "ref_id", ref_id)
        changed = replace(ref, report_field="tampered_field")
        tampered = replace(
            view,
            objectives=tuple(changed if item.ref_id == ref_id else item for item in view.objectives),
        )
    elif case == "tie-order":
        tie = _by_id(
            view.tie_breaks,
            "ref_id",
            "tie:canonical-decision-vector",
        )
        changed = replace(
            tie,
            decision_ids=tuple(reversed(tie.decision_ids)),
        )
        tampered = replace(view, tie_breaks=(changed,))
    else:
        raise AssertionError(f"Unknown policy tamper {case!r}")

    with pytest.raises(ExactPolicyContractError):
        evaluate_exact_candidate(scenario, tampered, candidate)


def test_tampered_sell_gate_metadata_is_rejected_with_typed_error() -> None:
    scenario = _invest_and_sell_scenario()
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    gate = _by_id(
        view.sell_gates,
        "gate_id",
        "sell-irreducibility:sell:route:sell:a",
    )
    tampered_gate = replace(gate, gate_id="sell-irreducibility:tampered")
    tampered_view = replace(view, sell_gates=(tampered_gate,))

    with pytest.raises(
        ExactPolicyContractError,
        match="SELL proof metadata",
    ):
        evaluate_exact_candidate(
            scenario,
            tampered_view,
            _candidate(view),
        )


def test_total_tie_covers_every_decision_once_in_semantic_order() -> None:
    scenario = _invest_and_sell_scenario()
    view = build_exact_policy_view(
        scenario,
        purpose="invest_only_baseline",
    )
    expected = (
        exact_decision_id("funding_transfer", "route:funding"),
        # NOTE: no fx_debit entry -- _invest_and_sell_scenario is 100%
        # EUR-only under the redesign (no fx_rates declared).
        exact_decision_id("buy_quantum", "route:buy:a"),
        exact_decision_id("sell_quantum", "route:sell:a"),
        exact_decision_id("buy_quantum", "route:buy:b"),
        exact_decision_id("sell_quantum", "route:sell:b"),
    )

    for tie in view.tie_breaks:
        assert tie.decision_ids == expected
        assert set(tie.decision_ids) == {item.decision_id for item in view.decisions}
        assert len(tie.decision_ids) == len(set(tie.decision_ids))


def test_funding_tie_uses_route_broker_id() -> None:
    contribution = _contribution("contribution:a", R(20))
    scenario = _scenario(
        "scenario:funding-tie",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a"),),
        brokers=(
            _broker("broker:a"),
            _broker("broker:z"),
        ),
        contributions=(contribution,),
        funding_routes=(
            _funding_route(
                "route:a",
                broker_id="broker:z",
                source_kind="contribution",
                source_id=contribution.contribution_id,
                amount=R(10),
            ),
            _funding_route(
                "route:z",
                broker_id="broker:a",
                source_kind="contribution",
                source_id=contribution.contribution_id,
                amount=R(10),
            ),
        ),
    )

    view = build_exact_policy_view(scenario)
    tie = _by_id(
        view.tie_breaks,
        "ref_id",
        "tie:canonical-decision-vector",
    )

    assert tie.decision_ids == (
        exact_decision_id("funding_transfer", "route:z"),
        exact_decision_id("funding_transfer", "route:a"),
    )


def test_same_local_capability_id_is_scoped_by_broker_for_tie_and_order() -> None:
    capability_id = "capability:shared"
    fee_id = "fee:shared"
    step_a_capability = _capability(capability_id, step=R(2))
    step_b_capability = _capability(capability_id, step=R(3))
    fee_a = _fee(fee_id, capability_id, "buy")
    fee_b = _fee(fee_id, capability_id, "buy")
    scenario = _scenario(
        "scenario:broker-scoped-capability",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a"),),
        brokers=(
            _broker("broker:a", (step_a_capability,), (fee_a,)),
            _broker("broker:b", (step_b_capability,), (fee_b,)),
        ),
        existing_cash=(
            _cash("cash:a", "broker:a", R(100)),
            _cash("cash:b", "broker:b", R(100)),
        ),
        order_routes=(
            _order_route(
                "route:a",
                broker_id="broker:a",
                asset_id="asset:a",
                capability=step_a_capability,
                fee_id=fee_id,
                side="buy",
                cap=R(10),
            ),
            _order_route(
                "route:b",
                broker_id="broker:b",
                asset_id="asset:a",
                capability=step_b_capability,
                fee_id=fee_id,
                side="buy",
                cap=R(12),
            ),
        ),
    )

    view = build_exact_policy_view(scenario)
    tie = _by_id(
        view.tie_breaks,
        "ref_id",
        "tie:canonical-decision-vector",
    )
    route_a_id = exact_decision_id("buy_quantum", "route:a")
    route_b_id = exact_decision_id("buy_quantum", "route:b")
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                route_a_id: 1,
                route_b_id: 1,
            },
        ),
    )
    order_a = _by_id(evaluation.orders, "route_id", "route:a")
    order_b = _by_id(evaluation.orders, "route_id", "route:b")

    assert tie.decision_ids == (route_a_id, route_b_id)
    assert _decision(view, route_a_id).upper_quanta == 5
    assert _decision(view, route_b_id).upper_quanta == 4
    assert (
        order_a.native_currency,
        order_a.order_measure,
        order_a.exact_cash_amount,
    ) == ("EUR", R(2), R(20))
    assert (
        order_b.native_currency,
        order_b.order_measure,
        order_b.exact_cash_amount,
    ) == ("EUR", R(3), R(30))


def test_asset_broker_key_is_collision_free_across_ambiguous_splits() -> None:
    """Mandated regression (b): _asset_broker_key is the composite key used
    at the position-constraint ref/fact sites (formerly an ambiguous plain
    f"{asset_id}:{broker_id}" join). A naive join would produce the
    identical string "a:b:c" for both pairs below (the ':' separator could
    be reassigned across the asset_id/broker_id boundary); the
    length-prefixed scheme must keep them distinct.
    """
    key_one = _asset_broker_key("a:b", "c")
    key_two = _asset_broker_key("a", "b:c")

    assert key_one != key_two
    assert key_one == "3:a:b1:c"
    assert key_two == "1:a3:b:c"


def test_constraint_refs_publish_canonical_entities_and_exact_units() -> None:
    view = build_exact_policy_view(_funding_fx_scenario())
    funding = _by_id(
        view.constraints,
        "ref_id",
        "constraint:no_self_transfer:route:funding:eur",
    )
    order = _by_id(
        view.constraints,
        "ref_id",
        "constraint:order_quantized:route:buy:usd",
    )
    ledger = _by_id(
        view.constraints,
        "ref_id",
        "constraint:spendable_cash_nonnegative:broker:destination:USD",
    )
    accounting = _by_id(
        view.constraints,
        "ref_id",
        "constraint:accounting_identity:global",
    )

    assert funding.entity_refs == (EntityRef("funding_route", "route:funding:eur"),)
    assert funding.units == (ExactUnit(kind="native_money", currency_code="EUR"),)
    assert order.entity_refs == (
        EntityRef("asset", "asset:a"),
        EntityRef("broker", "broker:destination"),
        EntityRef("order_route", "route:buy:usd"),
    )
    assert order.units == (ExactUnit(kind="asset_quantity", asset_id="asset:a"),)
    assert ledger.entity_refs == (
        EntityRef("broker", "broker:destination"),
        EntityRef("currency", "USD"),
    )
    assert ledger.units == (ExactUnit(kind="native_money", currency_code="USD"),)
    assert accounting.entity_refs == ()
    assert accounting.units == (ExactUnit(kind="valuation_money", currency_code="EUR"),)


def test_evaluation_tie_ids_and_quanta_align_with_policy_vector() -> None:
    scenario = _funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    values = {
        exact_decision_id(
            "funding_transfer",
            "route:funding:eur",
        ): 15_000,
        # Zero quanta: this test only checks that the canonical tie vector
        # (decision_ids + quanta) round-trips correctly, not real FX
        # conversion numerics (already covered by the dedicated FX tests),
        # so a zero fx_debit avoids the confirmed
        # ExactFxEvaluation.route_id models.py bug entirely (no row is
        # ever produced for a zero-quanta pool currency).
        exact_decision_id("fx_debit", _fx_debit_key("route:buy:usd", "EUR")): 0,
        exact_decision_id("buy_quantum", "route:buy:usd"): 1,
    }
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view, values),
    )
    tie = _by_id(
        view.tie_breaks,
        "ref_id",
        "tie:canonical-decision-vector",
    )

    assert evaluation.canonical_tie_decision_ids == tie.decision_ids
    assert evaluation.canonical_tie_quanta == tuple(values[decision_id] for decision_id in tie.decision_ids)
    assert all(isinstance(value, int) for value in evaluation.canonical_tie_quanta)


def test_permuted_source_rows_canonicalize_to_identical_exact_results() -> None:
    canonical = _min_fragmentation_scenario()
    permuted = _min_fragmentation_scenario(permuted_inputs=True)
    assert canonical == permuted
    assert exact_scenario_fingerprint(canonical) == (exact_scenario_fingerprint(permuted))

    canonical_view = build_exact_policy_view(canonical)
    permuted_view = build_exact_policy_view(permuted)
    values = {
        exact_decision_id("buy_quantum", "route:buy:a"): 1,
        exact_decision_id("buy_quantum", "route:buy:b"): 1,
    }
    canonical_result = evaluate_exact_candidate(
        canonical,
        canonical_view,
        _candidate(
            canonical_view,
            values,
            candidate_id="candidate:permutation",
        ),
    )
    permuted_result = evaluate_exact_candidate(
        permuted,
        permuted_view,
        _candidate(
            permuted_view,
            values,
            candidate_id="candidate:permutation",
        ),
    )

    assert canonical_view == permuted_view
    assert canonical_result == permuted_result


@pytest.mark.parametrize(
    ("family", "direction"),
    [
        pytest.param("initial_selected", "credit", id="initial"),
        pytest.param("funding_in", "credit", id="funding-in"),
        pytest.param("funding_out", "debit", id="funding-out"),
        pytest.param("fx_debit", "debit", id="fx-debit"),
    ],
)
def test_exact_flow_posting_families_have_zero_raw_delta(
    family: LedgerPostingFamily,
    direction: str,
) -> None:
    posting = exact_flow_posting(
        posting_id=f"posting:{family}",
        family=family,
        broker_id="broker:a",
        currency="EUR",
        amount=R(1001, 100),
        entity_refs=(
            EntityRef("route", "z"),
            EntityRef("asset", "a"),
        ),
    )

    assert posting.direction == direction
    assert posting.exact_amount == R(1001, 100)
    assert posting.posted_amount == R(1001, 100)
    assert posting.quantum is None
    assert posting.rounding_delta == ZERO
    assert posting.accounting_rounding_adjustment == ZERO
    assert posting.entity_refs == (
        EntityRef("asset", "a"),
        EntityRef("route", "z"),
    )


@pytest.mark.parametrize(
    ("family", "direction", "accounting_delta"),
    [
        pytest.param("fx_credit", "credit", R(-1, 200), id="fx-credit"),
        pytest.param("buy_debit", "debit", R(1, 200), id="buy-debit"),
        pytest.param(
            "gross_sell_credit",
            "credit",
            R(-1, 200),
            id="sell-gross",
        ),
        pytest.param("buy_fee", "debit", R(1, 200), id="buy-fee"),
        pytest.param("sell_fee", "debit", R(1, 200), id="sell-fee"),
        pytest.param(
            "broker_withheld_tax",
            "debit",
            R(1, 200),
            id="broker-tax",
        ),
        pytest.param(
            "self_reserved_tax",
            "debit",
            R(1, 200),
            id="self-tax",
        ),
    ],
)
def test_monetary_posting_families_use_signed_half_up_once(
    family: LedgerPostingFamily,
    direction: str,
    accounting_delta: ExactRatio,
) -> None:
    posting = rounded_money_posting(
        posting_id=f"posting:{family}",
        family=family,
        broker_id="broker:a",
        currency="EUR",
        exact_amount=R(201, 200),
        quantum=CENT,
    )

    assert posting.direction == direction
    assert posting.exact_amount == R(201, 200)
    assert posting.posted_amount == R(101, 100)
    assert posting.quantum == CENT
    assert posting.rounding_delta == R(1, 200)
    assert posting.accounting_rounding_adjustment == accounting_delta
    assert posting.rounding_delta == posting.posted_amount - posting.exact_amount


@pytest.mark.parametrize(
    ("builder", "family"),
    [
        pytest.param("exact", "buy_debit", id="rounded-through-exact"),
        pytest.param("rounded", "initial_selected", id="exact-through-rounded"),
    ],
)
def test_posting_builders_reject_the_other_family(
    builder: str,
    family: LedgerPostingFamily,
) -> None:
    with pytest.raises(PostingFamilyError):
        if builder == "exact":
            exact_flow_posting(
                posting_id="posting:wrong",
                family=family,
                broker_id="broker:a",
                currency="EUR",
                amount=ONE,
            )
        else:
            rounded_money_posting(
                posting_id="posting:wrong",
                family=family,
                broker_id="broker:a",
                currency="EUR",
                exact_amount=ONE,
                quantum=CENT,
            )


def test_native_ledger_aggregates_all_columns_without_double_counting() -> None:
    exact_specs = (
        ("initial", "initial_selected", R(10)),
        ("funding-in", "funding_in", R(5)),
        ("funding-out", "funding_out", R(2)),
        ("fx-debit", "fx_debit", ONE),
    )
    rounded_specs = (
        ("fx-credit", "fx_credit", R(3)),
        ("buy-debit", "buy_debit", R(4)),
        ("sell-credit", "gross_sell_credit", R(2)),
        ("buy-fee", "buy_fee", ONE),
        ("sell-fee", "sell_fee", ONE),
        ("broker-tax", "broker_withheld_tax", ONE),
        ("self-tax", "self_reserved_tax", ONE),
    )
    postings = tuple(
        exact_flow_posting(
            posting_id=posting_id,
            family=family,
            broker_id="broker:a",
            currency="EUR",
            amount=amount,
        )
        for posting_id, family, amount in exact_specs
    ) + tuple(
        rounded_money_posting(
            posting_id=posting_id,
            family=family,
            broker_id="broker:a",
            currency="EUR",
            exact_amount=amount,
            quantum=CENT,
        )
        for posting_id, family, amount in rounded_specs
    )

    rows = reconcile_broker_ledgers(
        ledger_keys=(("broker:a", "EUR"),),
        postings=postings,
    )
    matches = tuple(row for row in rows if (row.broker_id, row.currency) == ("broker:a", "EUR"))
    assert len(matches) == 1
    (row,) = matches
    assert row.initial_selected == R(10)
    assert row.funding_in == R(5)
    assert row.funding_out == R(2)
    assert row.fx_debit == ONE
    assert row.fx_credit == R(3)
    assert row.buy_debit == R(4)
    assert row.gross_sell_credit == R(2)
    assert row.buy_fees == ONE
    assert row.sell_fees == ONE
    assert row.broker_withheld_tax == ONE
    assert row.self_reserved_tax == ONE
    assert row.raw_rounding_delta == ZERO
    assert row.accounting_rounding_adjustment == ZERO
    assert row.final_spendable == R(9)
    assert row.final_physical == R(10)
    assert row.final_physical == (row.final_spendable + row.self_reserved_tax)


def test_native_ledger_rows_include_empty_domain_keys_in_canonical_order() -> None:
    rows = reconcile_broker_ledgers(
        ledger_keys=(
            ("broker:z", "USD"),
            ("broker:a", "EUR"),
            ("broker:a", "USD"),
        ),
        postings=(),
    )

    assert tuple((row.broker_id, row.currency) for row in rows) == (
        ("broker:a", "EUR"),
        ("broker:a", "USD"),
        ("broker:z", "USD"),
    )
    assert all(row.final_spendable == ZERO for row in rows)
    assert all(row.final_physical == ZERO for row in rows)


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("wrong-direction", id="wrong-direction"),
        pytest.param("undeclared-family", id="undeclared-family"),
        pytest.param("exact-extra-quantum", id="exact-extra-quantum"),
        pytest.param("rounded-missing-quantum", id="rounded-missing-quantum"),
        pytest.param("noncanonical-half-up", id="noncanonical-half-up"),
    ],
)
def test_reconciliation_rejects_malformed_posting_contracts(
    case: str,
) -> None:
    base = rounded_money_posting(
        posting_id="posting:a",
        family="buy_debit",
        broker_id="broker:a",
        currency="EUR",
        exact_amount=R(201, 200),
        quantum=CENT,
    )
    if case == "wrong-direction":
        malformed = replace(base, direction="credit")
    elif case == "undeclared-family":
        malformed = ExactLedgerPosting(
            posting_id="posting:a",
            family="undeclared",
            direction="debit",
            broker_id="broker:a",
            currency="EUR",
            entity_refs=(),
            exact_amount=ONE,
            posted_amount=ONE,
            quantum=CENT,
            rounding_delta=ZERO,
        )
    elif case == "exact-extra-quantum":
        malformed = ExactLedgerPosting(
            posting_id="posting:a",
            family="initial_selected",
            direction="credit",
            broker_id="broker:a",
            currency="EUR",
            entity_refs=(),
            exact_amount=ONE,
            posted_amount=ONE,
            quantum=CENT,
            rounding_delta=ZERO,
        )
    elif case == "rounded-missing-quantum":
        malformed = ExactLedgerPosting(
            posting_id="posting:a",
            family="buy_debit",
            direction="debit",
            broker_id="broker:a",
            currency="EUR",
            entity_refs=(),
            exact_amount=ONE,
            posted_amount=ONE,
            quantum=None,
            rounding_delta=ZERO,
        )
    elif case == "noncanonical-half-up":
        malformed = ExactLedgerPosting(
            posting_id="posting:a",
            family="buy_debit",
            direction="debit",
            broker_id="broker:a",
            currency="EUR",
            entity_refs=(),
            exact_amount=R(251, 250),
            posted_amount=R(101, 100),
            quantum=CENT,
            rounding_delta=R(3, 500),
        )
    else:
        raise AssertionError(f"Unknown malformed posting {case!r}")

    with pytest.raises(PostingFamilyError):
        reconcile_broker_ledgers(
            ledger_keys=(),
            postings=(malformed,),
        )


def test_reconciliation_rejects_duplicate_posting_ids_before_aggregation() -> None:
    first = exact_flow_posting(
        posting_id="posting:duplicate",
        family="initial_selected",
        broker_id="broker:a",
        currency="EUR",
        amount=R(10),
    )
    second = exact_flow_posting(
        posting_id="posting:duplicate",
        family="funding_in",
        broker_id="broker:b",
        currency="USD",
        amount=R(20),
    )

    with pytest.raises(
        DuplicatePostingError,
        match="posting IDs must be unique",
    ):
        reconcile_broker_ledgers(
            ledger_keys=(),
            postings=(first, second),
        )


def _inactive_surface_scenario(case: str) -> ExactPlannerScenario:
    asset = _asset("asset:a")
    inactive = _broker("broker:inactive", active=False, domain=True)
    if case == "selected-cash":
        return _scenario(
            "scenario:inactive:selected-cash",
            product="pac",
            policy="proportional",
            assets=(asset,),
            brokers=(inactive,),
            existing_cash=(_cash("cash:inactive", inactive.broker_id, ONE),),
        )
    if case == "funding-destination":
        contribution = _contribution("contribution:a", ONE)
        return _scenario(
            "scenario:inactive:funding-destination",
            product="pac",
            policy="proportional",
            assets=(asset,),
            brokers=(inactive,),
            contributions=(contribution,),
            funding_routes=(
                _funding_route(
                    "route:funding",
                    broker_id=inactive.broker_id,
                    source_kind="contribution",
                    source_id=contribution.contribution_id,
                    amount=ONE,
                ),
            ),
        )
    if case == "funding-source":
        active = _broker("broker:active")
        return _scenario(
            "scenario:inactive:funding-source",
            product="pac",
            policy="proportional",
            assets=(asset,),
            brokers=(active, inactive),
            existing_cash=(_cash("cash:inactive", inactive.broker_id, ZERO),),
            funding_routes=(
                _funding_route(
                    "route:funding",
                    broker_id=active.broker_id,
                    source_kind="existing_cash",
                    source_id="cash:inactive",
                    amount=ONE,
                ),
            ),
        )
    if case == "order":
        capability = _capability("capability:buy")
        fee = _fee("fee:buy", capability.capability_id, "buy")
        inactive = _broker(
            inactive.broker_id,
            (capability,),
            (fee,),
            active=False,
            domain=True,
        )
        return _scenario(
            "scenario:inactive:order",
            product="pac",
            policy="proportional",
            assets=(asset,),
            brokers=(inactive,),
            order_routes=(
                _order_route(
                    "route:buy",
                    broker_id=inactive.broker_id,
                    asset_id=asset.asset_id,
                    capability=capability,
                    fee_id=fee.fee_schedule_id,
                    side="buy",
                ),
            ),
        )
    raise AssertionError(f"Unknown inactive Broker witness {case!r}")


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("selected-cash", id="selected-cash"),
        pytest.param("funding-destination", id="funding-destination"),
        pytest.param("funding-source", id="funding-source"),
        pytest.param("order", id="order"),
    ],
)
def test_inactive_domain_broker_executable_surfaces_fail_closed(
    case: str,
) -> None:
    with pytest.raises(
        ExactScenarioContractError,
        match="inactive",
    ):
        build_exact_policy_view(_inactive_surface_scenario(case))


def test_inactive_broker_custody_only_holding_remains_evaluable() -> None:
    broker = _broker("broker:inactive", active=False, domain=True)
    scenario = _scenario(
        "scenario:inactive:custody-only",
        product="rebalancer",
        policy="invest_only",
        assets=(_asset("asset:a"),),
        brokers=(broker,),
        holdings=(
            _holding(
                "holding:a",
                "asset:a",
                broker.broker_id,
                ONE,
            ),
        ),
    )

    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view),
    )

    assert evaluation.candidate_valid is True
    assert evaluation.feasible is True
    holding = _by_id(evaluation.holdings, "asset_id", "asset:a")
    assert holding.initial_quantity == ONE
    assert holding.final_quantity == ONE
    assert evaluation.accounting is not None
    assert evaluation.accounting.current_invested == R(10)


def test_selected_cash_cannot_exceed_available_cash() -> None:
    with pytest.raises(
        ValueError,
        match="selected cash cannot exceed available cash",
    ):
        _cash(
            "cash:a",
            "broker:a",
            R(11),
            available=R(10),
        )


# NOTE: test_conversion_allowed_accepts_one_explicit_valuation_leg and
# test_order_currency_contract_rejects_implicit_conversion tested the removed
# ExactOrderCapability.currency / fx_mode ("native_currency_required" /
# "conversion_allowed") axis. Order fee/minimum/step now always live in the
# Asset's own quote currency, so this contract cannot be violated anymore and
# the tests were deleted rather than adapted.


@pytest.mark.parametrize(
    ("pair_first", "pair_second"),
    [
        pytest.param("USD", "EUR", id="reversed-order"),
        pytest.param("EUR", "EUR", id="identical-currency"),
    ],
)
def test_fx_rate_pair_must_be_ascending_and_distinct(
    pair_first: str,
    pair_second: str,
) -> None:
    with pytest.raises(ValueError, match="ascending alphabetical order"):
        ExactFxRate(pair_first=pair_first, pair_second=pair_second, rate=ONE)


@pytest.mark.parametrize(
    ("quantity_step", "expected_issue"),
    [
        pytest.param(
            "9007199254740993",
            None,
            id="canonical-lossless-integer",
        ),
        pytest.param(
            "0",
            "allocation.nonpositive_quantity_step",
            id="zero",
        ),
        pytest.param(
            "-1",
            "allocation.nonpositive_quantity_step",
            id="negative",
        ),
    ],
)
def test_whole_quantity_step_transport_normalizes_losslessly_or_rejects_nonpositive(
    quantity_step: str,
    expected_issue: str | None,
) -> None:
    request = _planner_request_with_whole_step(quantity_step)
    wire_broker = _by_id(
        request.brokers,
        "broker_id",
        "broker:a",
    )
    wire_capability = _by_id(
        wire_broker.capabilities,
        "capability_id",
        "capability:whole",
    )
    assert isinstance(wire_capability.quantity_step, str)
    assert wire_capability.quantity_step == quantity_step

    result = normalize_planner_request(request)

    if expected_issue is None:
        assert result.availability == "ready"
        assert result.normalized is not None
        exact_broker = _by_id(
            result.normalized.brokers,
            "broker_id",
            "broker:a",
        )
        exact_capability = _by_id(
            exact_broker.capabilities,
            "capability_id",
            "capability:whole",
        )
        assert exact_capability.order_step == R(9_007_199_254_740_993)
    else:
        assert result.normalized is None
        assert expected_issue in {issue.code for issue in result.issues}


def test_whole_quantity_capability_requires_integer_step() -> None:
    scenario = _pac_scenario(step=R(1, 2))

    with pytest.raises(
        ExactScenarioContractError,
        match="requires an integer step",
    ):
        build_exact_policy_view(scenario)


def _replace_with_noncanonical_order_routes() -> object:
    scenario = _min_fragmentation_scenario()
    return replace(
        scenario,
        order_routes=tuple(reversed(scenario.order_routes)),
    )


def _replace_with_duplicate_order_id() -> object:
    scenario = _pac_scenario()
    route = _by_id(
        scenario.order_routes,
        "route_id",
        "route:buy:a",
    )
    return replace(
        scenario,
        order_routes=(route, route),
    )


def _replace_with_duplicate_fee_id() -> object:
    scenario = _pac_scenario()
    broker = _by_id(scenario.brokers, "broker_id", "broker:a")
    fee = _by_id(
        broker.fee_schedules,
        "fee_schedule_id",
        "fee:buy:a",
    )
    return replace(
        broker,
        fee_schedules=(fee, fee),
    )


def _replace_with_duplicate_fx_pair() -> object:
    scenario = _funding_fx_scenario()
    rate = _by_id(scenario.fx_rates, "pair_key", "EUR/USD")
    duplicate = replace(rate, rate=rate.rate * 2)
    return replace(
        scenario,
        fx_rates=tuple(
            sorted(
                (rate, duplicate),
                key=lambda item: (item.pair_first, item.pair_second),
            )
        ),
    )


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(
            _replace_with_noncanonical_order_routes,
            id="order-ordering",
        ),
        pytest.param(
            _replace_with_duplicate_order_id,
            id="duplicate-order-id",
        ),
        pytest.param(
            _replace_with_duplicate_fee_id,
            id="duplicate-fee-id",
        ),
        pytest.param(
            _replace_with_duplicate_fx_pair,
            id="duplicate-fx-pair",
        ),
    ],
)
def test_exact_models_reject_duplicate_or_noncanonical_rows_before_indexing(
    mutation: Any,
) -> None:
    with pytest.raises(ValueError, match="canonical|duplicate|unique"):
        mutation()


def test_inactive_order_row_has_no_fee_or_monetary_posting() -> None:
    scenario = _pac_scenario(
        fixed_fee=R(9),
        fee_rate=R(1, 2),
        fee_floor=R(7),
    )
    view = build_exact_policy_view(scenario)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view),
    )

    assert evaluation.orders == ()
    assert not [posting for posting in evaluation.postings if posting.family in {"buy_debit", "buy_fee"}]
    assert evaluation.costs is not None
    assert evaluation.costs.buy_fees == ZERO


@pytest.mark.parametrize(
    ("rate", "floor", "cap", "expected"),
    [
        pytest.param(
            R(1, 100),
            R(2),
            R(5),
            R(3),
            id="floor",
        ),
        pytest.param(
            R(1, 5),
            ONE,
            R(5),
            R(3),
            id="variable",
        ),
        pytest.param(
            R(1, 2),
            ONE,
            R(3),
            R(4),
            id="cap",
        ),
    ],
)
def test_active_order_applies_fixed_and_bounded_variable_fee_once(
    rate: ExactRatio,
    floor: ExactRatio,
    cap: ExactRatio,
    expected: ExactRatio,
) -> None:
    scenario = _pac_scenario(
        fixed_fee=ONE,
        fee_rate=rate,
        fee_floor=floor,
        fee_cap=cap,
    )
    view = build_exact_policy_view(scenario)
    decision_id = exact_decision_id("buy_quantum", "route:buy:a")

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view, {decision_id: 1}),
    )
    order = _by_id(evaluation.orders, "route_id", "route:buy:a")
    fee_posting = _by_id(
        evaluation.postings,
        "posting_id",
        "buy-fee:route:buy:a",
    )

    assert order.exact_cash_amount == R(10)
    assert order.exact_fee == expected
    assert order.posted_fee == expected
    assert fee_posting.exact_amount == expected
    assert fee_posting.posted_amount == expected
    assert evaluation.costs is not None
    assert evaluation.costs.buy_fees == expected


def test_direct_fx_replay_preserves_direction_and_spread() -> None:
    scenario = _funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    fx_debit_id = exact_decision_id(
        "fx_debit",
        _fx_debit_key("route:buy:usd", "EUR"),
    )
    candidate = _candidate(
        view,
        {
            exact_decision_id(
                "funding_transfer",
                "route:funding:eur",
            ): 15_000,
            fx_debit_id: 10_000,
            exact_decision_id("buy_quantum", "route:buy:usd"): 1,
        },
    )

    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    action = _by_id(
        evaluation.fx,
        "order_route_id",
        "route:buy:usd",
    )
    debit = _by_id(
        evaluation.postings,
        "posting_id",
        "fx-debit:route:buy:usd:EUR",
    )
    credit = _by_id(
        evaluation.postings,
        "posting_id",
        "fx-credit:route:buy:usd:EUR",
    )

    assert action.source_currency == "EUR"
    assert action.destination_currency == "USD"
    assert action.quanta == 10_000
    assert action.source_debit == R(100)
    assert action.approved_rate == R(6, 5)
    assert action.effective_rate == R(297, 250)
    assert action.exact_destination_credit == R(594, 5)
    assert action.posted_destination_credit == R(594, 5)
    assert action.spread_loss == R(1)
    assert debit.family == "fx_debit"
    assert debit.quantum is None
    assert debit.posted_amount == R(100)
    assert credit.family == "fx_credit"
    assert credit.quantum == CENT
    assert credit.posted_amount == R(594, 5)
    assert (action.source_debit / CENT).denominator == 1


def test_multi_source_buy_shares_a_cash_pool_across_two_buys() -> None:
    """A single BUY (route:buy:1) draws from two currency pools (GBP and USD
    existing cash) at the same Broker, each converting to its own EUR quote
    currency via a distinct direct fx_rate. A second BUY (route:buy:2)
    shares the same GBP pool. Asserts one ExactFxEvaluation per (route,
    source currency) with spread applied once each, and that the shared GBP
    ledger row nets the combined draw from both BUYs correctly
    (SPENDABLE_CASH_NONNEGATIVE across combined postings -- already covered
    by the existing ledger-level check, no separate constraint code needed).
    A pure BUY-only (PAC) scenario is used deliberately: SELL requires the
    invest_and_sell two-phase baseline/extension flow, which is orthogonal to
    what this regression is about (multi-currency pool sharing).
    """
    buy_capability = _capability("capability:buy")
    buy_fee = _fee("fee:buy", buy_capability.capability_id, "buy")
    broker = _broker("broker:hub", (buy_capability,), (buy_fee,))
    scenario = _scenario(
        "scenario:multi-source-buy",
        product="pac",
        policy="proportional",
        assets=(
            _asset("asset:target1", price=R(99), currency="EUR"),
            _asset("asset:target2", price=R(99), currency="EUR"),
        ),
        brokers=(broker,),
        existing_cash=(
            _cash("cash:gbp", broker.broker_id, R(200), currency="GBP"),
            _cash("cash:usd", broker.broker_id, R(100), currency="USD"),
        ),
        order_routes=(
            _order_route(
                "route:buy:1",
                broker_id=broker.broker_id,
                asset_id="asset:target1",
                capability=buy_capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(10),
                priority=1,
            ),
            _order_route(
                "route:buy:2",
                broker_id=broker.broker_id,
                asset_id="asset:target2",
                capability=buy_capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(10),
                priority=2,
            ),
        ),
        fx_rates=(
            _fx_rate("EUR", "GBP", R(1, 2)),
            _fx_rate("EUR", "USD", R(1, 4)),
        ),
        fx_spread_rate=R(1, 100),
        currency_quantums=(("EUR", CENT), ("GBP", CENT), ("USD", CENT)),
    )
    view = build_exact_policy_view(scenario)
    candidate = _candidate(
        view,
        {
            # route:buy:1 (2 units @ EUR99 = EUR198): GBP50 -> EUR99 +
            # USD25 -> EUR99, exactly covering its EUR198 cost.
            exact_decision_id("fx_debit", _fx_debit_key("route:buy:1", "GBP")): 5_000,
            exact_decision_id("fx_debit", _fx_debit_key("route:buy:1", "USD")): 2_500,
            exact_decision_id("buy_quantum", "route:buy:1"): 2,
            # route:buy:2 (1 unit @ EUR99): GBP50 -> EUR99, sharing the same
            # GBP cash row already partly drawn by route:buy:1.
            exact_decision_id("fx_debit", _fx_debit_key("route:buy:2", "GBP")): 5_000,
            exact_decision_id("buy_quantum", "route:buy:2"): 1,
        },
    )

    evaluation = evaluate_exact_candidate(scenario, view, candidate)

    fx_by_key = {(item.order_route_id, item.source_currency): item for item in evaluation.fx}
    assert set(fx_by_key) == {
        ("route:buy:1", "GBP"),
        ("route:buy:1", "USD"),
        ("route:buy:2", "GBP"),
    }

    # GBP -> EUR: 1 GBP = 2 EUR official; effective = 2 * (1 - 1/100) = 99/50.
    buy1_gbp = fx_by_key[("route:buy:1", "GBP")]
    assert buy1_gbp.destination_currency == "EUR"
    assert buy1_gbp.source_debit == R(50)
    assert buy1_gbp.approved_rate == R(2)
    assert buy1_gbp.effective_rate == R(99, 50)
    assert buy1_gbp.exact_destination_credit == R(99)
    assert buy1_gbp.posted_destination_credit == R(99)
    assert buy1_gbp.spread_loss == R(1)

    # USD -> EUR: 1 USD = 4 EUR official; effective = 4 * (1 - 1/100) = 99/25.
    buy1_usd = fx_by_key[("route:buy:1", "USD")]
    assert buy1_usd.destination_currency == "EUR"
    assert buy1_usd.source_debit == R(25)
    assert buy1_usd.approved_rate == R(4)
    assert buy1_usd.effective_rate == R(99, 25)
    assert buy1_usd.exact_destination_credit == R(99)
    assert buy1_usd.posted_destination_credit == R(99)
    assert buy1_usd.spread_loss == R(1)

    buy2_gbp = fx_by_key[("route:buy:2", "GBP")]
    assert buy2_gbp.destination_currency == "EUR"
    assert buy2_gbp.source_debit == R(50)
    assert buy2_gbp.approved_rate == R(2)
    assert buy2_gbp.effective_rate == R(99, 50)
    assert buy2_gbp.exact_destination_credit == R(99)
    assert buy2_gbp.posted_destination_credit == R(99)
    assert buy2_gbp.spread_loss == R(1)

    ledger_rows = {(row.broker_id, row.currency): row for row in evaluation.ledgers}
    gbp_row = ledger_rows[("broker:hub", "GBP")]
    usd_row = ledger_rows[("broker:hub", "USD")]
    eur_row = ledger_rows[("broker:hub", "EUR")]

    # Shared pool: both BUYs draw GBP from the same cash row; the combined
    # debit (50 + 50 = 100) must be reflected as one nonnegative residual,
    # not evaluated per-BUY in isolation.
    assert gbp_row.fx_debit == R(100)
    assert gbp_row.final_spendable == R(100)
    assert usd_row.fx_debit == R(25)
    assert usd_row.final_spendable == R(75)
    assert eur_row.fx_credit == R(297)
    assert eur_row.buy_debit == R(297)
    assert eur_row.final_spendable == ZERO


def test_sell_never_converts_and_proceeds_stay_in_quote_currency() -> None:
    """SELL never converts: a SELL whose Asset quote currency (USD) differs
    from another currency that actually holds cash at the same Broker (EUR)
    must produce no ExactFxEvaluation/fx postings at all for its proceeds --
    only a BUY may draw on a currency pool. The proceeds ledger posting
    lands in the Asset's own quote currency, untouched. A same-currency (USD)
    incremental BUY is included so the SELL genuinely funds it (satisfying
    the invest_and_sell SELL_FUNDS_INCREMENTAL_BUY policy rule) while still
    involving zero FX -- keeping the "SELL never converts" claim isolated
    from any cross-currency mechanics.
    """
    sell_capability = _capability("capability:sell")
    buy_capability = _capability("capability:buy")
    sell_fee = _fee("fee:sell", sell_capability.capability_id, "sell", currency="USD")
    buy_fee = _fee("fee:buy", buy_capability.capability_id, "buy", currency="USD")
    broker = _broker(
        "broker:hub2",
        (sell_capability, buy_capability),
        (sell_fee, buy_fee),
    )
    holding = _holding("holding:sell-only", "asset:sell-only", broker.broker_id, R(3))
    scenario = _scenario(
        "scenario:sell-never-converts",
        product="rebalancer",
        policy="invest_and_sell",
        # A third, unheld "asset:other" is included purely so the target
        # weights are not evenly split only between the two active assets in
        # a way that would zero out the sell-source's residual; with
        # fixed_reference == current_invested (no funding_routes here),
        # splitting the target three ways keeps asset:sell-only genuinely
        # overweight (residual > 0), which is what unlocks it for the
        # sell_extension phase.
        assets=(
            _asset("asset:sell-only", price=R(20), currency="USD"),
            _asset("asset:usd-buy-target", price=R(30), currency="USD"),
            _asset("asset:other", price=R(10), currency="EUR"),
        ),
        brokers=(broker,),
        holdings=(holding,),
        existing_cash=(_cash("cash:eur", broker.broker_id, R(50), currency="EUR"),),
        order_routes=(
            _order_route(
                "route:sell-only",
                broker_id=broker.broker_id,
                asset_id="asset:sell-only",
                capability=sell_capability,
                fee_id=sell_fee.fee_schedule_id,
                side="sell",
                cap=R(10),
            ),
            _order_route(
                "route:buy-usd",
                broker_id=broker.broker_id,
                asset_id="asset:usd-buy-target",
                capability=buy_capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=R(10),
            ),
        ),
        fx_rates=(_fx_rate("EUR", "USD", R(1, 2)),),
        fx_spread_rate=R(1, 100),
        currency_quantums=(("EUR", CENT), ("USD", CENT)),
        sell_context=_sell_context(
            holdings=(holding,),
            asset_ids=("asset:sell-only",),
            broker_ids=(broker.broker_id,),
            currency="USD",
            unit_costs={"asset:sell-only": R(5)},
        ),
    )
    # invest_and_sell scenarios are strictly two-phase: an all-zero
    # invest_only_baseline (route:buy-usd stays at 0) followed by a
    # sell_extension that unlocks the pre-existing "asset:sell-only" holding
    # and additively increases the USD buy, funded entirely by the sell.
    baseline_view = build_exact_policy_view(scenario, purpose="invest_only_baseline")
    baseline_candidate = _candidate(baseline_view, {}, candidate_id="candidate:baseline")
    view = build_exact_policy_view(
        scenario,
        purpose="sell_extension",
        baseline=baseline_candidate,
    )
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id("sell_quantum", "route:sell-only"): 2,
                exact_decision_id("buy_quantum", "route:buy-usd"): 1,
            },
        ),
    )

    assert evaluation.feasible is True
    assert evaluation.fx == ()
    assert not any(posting.family in {"fx_debit", "fx_credit"} for posting in evaluation.postings)
    credit_posting = _by_id(
        evaluation.postings,
        "posting_id",
        "gross-sell-credit:route:sell-only",
    )
    assert credit_posting.currency == "USD"
    assert credit_posting.posted_amount == R(40)

    ledger_rows = {(row.broker_id, row.currency): row for row in evaluation.ledgers}
    usd_row = ledger_rows[("broker:hub2", "USD")]
    eur_row = ledger_rows[("broker:hub2", "EUR")]
    # SELL proceeds (40) fund the USD BUY (30) same-currency, no FX at all;
    # the EUR cash row is completely untouched by the SELL's own currency.
    assert usd_row.gross_sell_credit == R(40)
    assert usd_row.buy_debit == R(30)
    assert usd_row.fx_debit == ZERO
    assert usd_row.fx_credit == ZERO
    assert usd_row.final_spendable == R(10)
    assert eur_row.fx_debit == ZERO
    assert eur_row.fx_credit == ZERO
    assert eur_row.final_spendable == R(50)


# NOTE: test_active_fx_graph_conflicts_are_deterministic tested the removed
# FX route-graph cycle/multi-hop/arbitrage rejection codes (FX_NO_ACTIVE_ARBITRAGE,
# FX_NO_ACTIVE_CYCLE, FX_SINGLE_HOP). Anti-cascade is now structural (a BUY's FX
# credit lands directly in its own quote currency and can never become a pool
# source for another BUY), so there is no runtime graph-cycle check left to
# exercise; the test was deleted rather than adapted.


@pytest.mark.parametrize(
    ("kind", "step", "quanta", "expected_measure", "expected_quantity"),
    [
        pytest.param(
            "whole_quantity",
            R(2),
            2,
            R(4),
            R(4),
            id="whole",
        ),
        pytest.param(
            "monetary_amount",
            R(15),
            2,
            R(30),
            R(3),
            id="monetary",
        ),
    ],
)
def test_buy_capabilities_preserve_measure_quantity_and_quote_basis(
    kind: str,
    step: ExactRatio,
    quanta: int,
    expected_measure: ExactRatio,
    expected_quantity: ExactRatio,
) -> None:
    scenario = _pac_scenario(
        price=R(1_000),
        quote_base=R(100),
        capability_kind=kind,
        step=step,
        route_cap=R(100),
    )
    view = build_exact_policy_view(scenario)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id(
                    "buy_quantum",
                    "route:buy:a",
                ): quanta
            },
        ),
    )
    order = _by_id(evaluation.orders, "route_id", "route:buy:a")

    assert order.capability_kind == kind
    assert order.source_quote_base_quantity == R(100)
    assert order.source_unit_price == R(10)
    assert order.mid_unit_price == R(10)
    assert order.order_measure == expected_measure
    assert order.economic_quantity == expected_quantity
    expected_cash = R(40) if kind == "whole_quantity" else R(30)
    assert order.exact_cash_amount == expected_cash
    assert order.posted_cash_amount > ZERO


def test_positive_buy_quanta_with_zero_rounded_debit_is_infeasible() -> None:
    scenario = _pac_scenario(
        price=ONE,
        capability_kind="monetary_amount",
        step=R(1, 250),
        cash=ONE,
        route_cap=ONE,
    )
    view = build_exact_policy_view(scenario)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id(
                    "buy_quantum",
                    "route:buy:a",
                ): 1
            },
        ),
    )
    order = _by_id(evaluation.orders, "route_id", "route:buy:a")

    assert order.exact_cash_amount == R(1, 250)
    assert order.posted_cash_amount == ZERO
    assert "BUY_DEBIT_POSITIVE" in evaluation.conflict_codes
    assert evaluation.candidate_valid is True
    assert evaluation.feasible is False


@pytest.mark.parametrize(
    "withholding_kind",
    [
        pytest.param("broker_withheld", id="broker-withheld"),
        pytest.param("self_reserved", id="self-reserved"),
    ],
)
def test_sell_replay_uses_exact_wac_gain_tax_and_withholding_once(
    withholding_kind: str,
) -> None:
    scenario = _invest_and_sell_scenario(
        sell_fixed=ONE,
        sell_rate=R(1, 10),
        sell_floor=ONE,
        sell_cap=R(2),
        tax_rate=R(1, 4),
        withholding_kind=withholding_kind,
        carried_loss=R(999),
    )
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    candidate = _candidate(
        view,
        {
            exact_decision_id("buy_quantum", "route:buy:b"): 3,
            exact_decision_id("sell_quantum", "route:sell:a"): 2,
        },
    )

    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    order = _by_id(evaluation.orders, "route_id", "route:sell:a")
    tax_family = "broker_withheld_tax" if withholding_kind == "broker_withheld" else "self_reserved_tax"
    tax_posting = _by_id(
        evaluation.postings,
        "posting_id",
        f"{tax_family.replace('_', '-')}:route:sell:a",
    )
    ledger = tuple(row for row in evaluation.ledgers if (row.broker_id, row.currency) == ("broker:a", "EUR"))
    assert len(ledger) == 1
    (ledger_row,) = ledger

    assert evaluation.candidate_valid is True
    assert evaluation.feasible is True
    assert order.side == "sell"
    assert order.order_measure == R(2)
    assert order.economic_quantity == R(2)
    assert order.exact_cash_amount == R(20)
    assert order.posted_cash_amount == R(20)
    assert order.exact_fee == R(3)
    assert order.posted_fee == R(3)
    assert order.cost_basis == R(10)
    assert order.taxable_gain == R(7)
    assert order.exact_tax_reserve == R(7, 4)
    assert order.posted_tax_reserve == R(7, 4)
    assert order.withholding_kind == withholding_kind
    assert tax_posting.family == tax_family
    assert tax_posting.exact_amount == R(7, 4)
    assert tax_posting.posted_amount == R(7, 4)
    assert evaluation.costs is not None
    assert evaluation.costs.sell_fees == R(3)
    assert _objective_map(view, evaluation)["explicit_cost"] == R(19, 4)
    if withholding_kind == "broker_withheld":
        assert evaluation.costs.broker_withheld_tax == R(7, 4)
        assert evaluation.costs.self_reserved_tax == ZERO
        assert ledger_row.broker_withheld_tax == R(7, 4)
        assert ledger_row.self_reserved_tax == ZERO
        assert ledger_row.final_physical == ledger_row.final_spendable
    else:
        assert evaluation.costs.broker_withheld_tax == ZERO
        assert evaluation.costs.self_reserved_tax == R(7, 4)
        assert ledger_row.broker_withheld_tax == ZERO
        assert ledger_row.self_reserved_tax == R(7, 4)
        assert ledger_row.final_physical == (ledger_row.final_spendable + R(7, 4))


# NOTE: test_sell_wac_converts_through_one_direct_fiscal_valuation_leg tested a
# "fiscal" valuation rate independently adjustable from the FX conversion
# rate (scenario.valuation_rates). Valuation is now always derived from the
# same canonical fx_rates map used for real conversions, so an independently
# diverging valuation leg can no longer exist; the test was deleted rather
# than adapted.


def test_carried_loss_is_informational_and_does_not_offset_sell_tax() -> None:
    evaluations = []
    for carried_loss in (ZERO, R(10_000)):
        scenario = _invest_and_sell_scenario(
            sell_fixed=ONE,
            sell_rate=R(1, 10),
            sell_floor=ONE,
            sell_cap=R(2),
            tax_rate=R(1, 4),
            carried_loss=carried_loss,
        )
        _baseline_view, baseline = _invest_only_baseline(scenario)
        view = _sell_extension(scenario, baseline)
        evaluations.append(
            evaluate_exact_candidate(
                scenario,
                view,
                _candidate(
                    view,
                    {
                        exact_decision_id(
                            "buy_quantum",
                            "route:buy:b",
                        ): 3,
                        exact_decision_id(
                            "sell_quantum",
                            "route:sell:a",
                        ): 2,
                    },
                ),
            )
        )

    reserves = tuple(
        _by_id(
            evaluation.orders,
            "route_id",
            "route:sell:a",
        ).exact_tax_reserve
        for evaluation in evaluations
    )
    assert reserves == (R(7, 4), R(7, 4))


def test_monetary_sell_uses_integer_quanta_without_hidden_requested_ceiling() -> None:
    scenario = _invest_and_sell_scenario(
        monetary_sell=True,
        sell_step=R(2),
    )
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    sell_id = exact_decision_id("sell_quantum", "route:sell:a")
    access = _decision(view, sell_id)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id("buy_quantum", "route:buy:b"): 3,
                sell_id: 8,
            },
        ),
    )
    order = _by_id(evaluation.orders, "route_id", "route:sell:a")

    assert access.upper_quanta == 40
    assert order.capability_kind == "monetary_amount"
    assert order.quanta == 8
    assert order.order_measure == R(16)
    assert order.exact_cash_amount == R(16)
    assert order.economic_quantity == R(8, 5)
    assert order.source_quote_base_quantity == ONE
    assert order.posted_cash_amount == R(16)
    assert evaluation.feasible is True


@pytest.mark.parametrize(
    ("declared_cap", "expected_upper"),
    [
        pytest.param(R(25), 25, id="notional-cap"),
        pytest.param(R(100), 80, id="inventory"),
    ],
)
def test_monetary_sell_upper_bound_keeps_notional_cap_and_inventory_binding(
    declared_cap: ExactRatio,
    expected_upper: int,
) -> None:
    scenario = _invest_and_sell_scenario(monetary_sell=True)
    sell_route = _by_id(
        scenario.order_routes,
        "route_id",
        "route:sell:a",
    )
    scenario = replace(
        scenario,
        order_routes=tuple(
            (
                replace(
                    route,
                    cap=replace(route.cap, value=declared_cap),
                )
                if route == sell_route
                else route
            )
            for route in scenario.order_routes
        ),
    )
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    sell_id = exact_decision_id("sell_quantum", "route:sell:a")
    access = _decision(view, sell_id)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {sell_id: expected_upper + 1},
        ),
    )

    assert access.upper_quanta == expected_upper
    _assert_invalid_candidate_has_no_replay(
        evaluation,
        ("CANDIDATE_DECISION_OUT_OF_BOUNDS",),
    )


@pytest.mark.parametrize(
    ("first_quanta", "second_quanta", "expected_final", "expected_conflict"),
    [
        pytest.param(1, 1, R(6), False, id="within-inventory"),
        pytest.param(5, 5, R(-2), True, id="over-inventory"),
    ],
)
def test_multiple_sell_routes_reconcile_shared_inventory(
    first_quanta: int,
    second_quanta: int,
    expected_final: ExactRatio,
    expected_conflict: bool,
) -> None:
    scenario = _invest_and_sell_scenario()
    first = _by_id(
        scenario.order_routes,
        "route_id",
        "route:sell:a",
    )
    second = replace(first, route_id="route:sell:a:second")
    scenario = replace(
        scenario,
        order_routes=tuple(
            sorted(
                (*scenario.order_routes, second),
                key=lambda item: item.route_id,
            )
        ),
    )
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id("buy_quantum", "route:buy:b"): 4,
                exact_decision_id(
                    "sell_quantum",
                    "route:sell:a",
                ): first_quanta,
                exact_decision_id(
                    "sell_quantum",
                    "route:sell:a:second",
                ): second_quanta,
            },
        ),
    )
    holding_rows = tuple(
        item
        for item in evaluation.holdings
        if (item.asset_id, item.broker_id)
        == (
            "asset:a",
            "broker:a",
        )
    )
    assert len(holding_rows) == 1
    (holding,) = holding_rows

    assert holding.initial_quantity == R(8)
    assert holding.sell_quantity == R(first_quanta + second_quanta)
    assert holding.final_quantity == expected_final
    assert ("SELL_WITHIN_INVENTORY" in evaluation.conflict_codes) is expected_conflict
    assert ("FINAL_QUANTITY_NONNEGATIVE" in evaluation.conflict_codes) is expected_conflict


def test_buy_and_sell_same_asset_is_forbidden_even_when_cash_reconciles() -> None:
    scenario = _invest_and_sell_scenario()
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id("buy_quantum", "route:buy:a"): 1,
                exact_decision_id("sell_quantum", "route:sell:a"): 1,
            },
        ),
    )

    assert evaluation.candidate_valid is True
    assert "NO_ASSET_BUY_AND_SELL" in evaluation.conflict_codes
    assert evaluation.feasible is False


@pytest.mark.parametrize(
    ("minimum", "required", "cap", "quanta", "expected_code"),
    [
        pytest.param(
            R(2),
            ZERO,
            R(10),
            1,
            "ORDER_MIN_IF_ACTIVE",
            id="minimum-if-active",
        ),
        pytest.param(
            ZERO,
            R(3),
            R(10),
            2,
            "ORDER_REQUIRED_MIN",
            id="required-minimum",
        ),
        pytest.param(
            ZERO,
            ZERO,
            R(3),
            3,
            None,
            id="cap-boundary",
        ),
    ],
)
def test_order_minimum_required_and_cap_contracts(
    minimum: ExactRatio,
    required: ExactRatio,
    cap: ExactRatio,
    quanta: int,
    expected_code: str | None,
) -> None:
    scenario = _pac_scenario(
        minimum=minimum,
        required=required,
        route_cap=cap,
    )
    view = build_exact_policy_view(scenario)
    decision_id = exact_decision_id("buy_quantum", "route:buy:a")
    access = _decision(view, decision_id)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view, {decision_id: quanta}),
    )

    assert access.upper_quanta == cap.numerator // cap.denominator
    if expected_code is None:
        assert "ORDER_MIN_IF_ACTIVE" not in evaluation.conflict_codes
        assert "ORDER_REQUIRED_MIN" not in evaluation.conflict_codes
        assert "ORDER_CAP" not in evaluation.conflict_codes
    else:
        assert expected_code in evaluation.conflict_codes


@pytest.mark.parametrize(
    ("minimum", "required", "constraint_code"),
    [
        pytest.param(
            R(2),
            ZERO,
            "ORDER_MIN_IF_ACTIVE",
            id="minimum-if-active",
        ),
        pytest.param(
            ZERO,
            R(3),
            "ORDER_REQUIRED_MIN",
            id="required-minimum",
        ),
    ],
)
def test_monetary_sell_enforces_native_minimums(
    minimum: ExactRatio,
    required: ExactRatio,
    constraint_code: str,
) -> None:
    scenario = _invest_and_sell_scenario(
        monetary_sell=True,
        sell_minimum=minimum,
        sell_required=required,
    )
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id("buy_quantum", "route:buy:b"): 3,
                exact_decision_id("sell_quantum", "route:sell:a"): 1,
            },
        ),
    )
    constraint = _by_id(
        evaluation.constraints,
        "ref_id",
        f"constraint:{constraint_code.lower()}:route:sell:a",
    )

    assert constraint.value == ONE
    assert constraint.lower_bound == max(minimum, required)
    assert constraint.satisfied is False
    assert constraint_code in evaluation.conflict_codes


def test_sell_required_minimum_is_neutral_in_baseline_and_hard_in_extension() -> None:
    scenario = _invest_and_sell_scenario(sell_required=ONE)
    baseline_view, baseline = _invest_only_baseline(scenario)
    baseline_evaluation = evaluate_exact_candidate(
        scenario,
        baseline_view,
        baseline,
    )
    assert baseline_evaluation.feasible is True
    assert "ORDER_REQUIRED_MIN" not in baseline_evaluation.conflict_codes

    extension = _sell_extension(scenario, baseline)
    zero_sell = evaluate_exact_candidate(
        scenario,
        extension,
        _candidate(extension),
    )

    assert "ORDER_REQUIRED_MIN" in zero_sell.conflict_codes
    constraint = _by_id(
        zero_sell.constraints,
        "ref_id",
        "constraint:order_required_min:route:sell:a",
    )
    assert constraint.value == ZERO
    assert constraint.lower_bound == ONE
    assert constraint.satisfied is False


def test_active_sell_requires_strictly_positive_posted_net() -> None:
    scenario = _invest_and_sell_scenario(
        sell_fixed=R(10),
    )
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id("buy_quantum", "route:buy:b"): 3,
                exact_decision_id("sell_quantum", "route:sell:a"): 1,
            },
        ),
    )
    order = _by_id(evaluation.orders, "route_id", "route:sell:a")

    assert order.posted_cash_amount == R(10)
    assert order.posted_fee == R(10)
    assert order.posted_tax_reserve == ZERO
    assert "SELL_NET_POSITIVE" in evaluation.conflict_codes
    assert evaluation.feasible is False


def _multiroute_funding_scenario() -> ExactPlannerScenario:
    capability_a = _capability("capability:a")
    capability_b = _capability("capability:b")
    fee_a = _fee("fee:buy:a", capability_a.capability_id, "buy")
    fee_b = _fee("fee:buy:b", capability_b.capability_id, "buy")
    broker_a = _broker("broker:a", (capability_a,), (fee_a,))
    broker_b = _broker("broker:b", (capability_b,), (fee_b,))
    contribution = _contribution("contribution:a", R(10))
    return _scenario(
        "scenario:funding:multiroute",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a"),),
        brokers=(broker_a, broker_b),
        contributions=(contribution,),
        funding_routes=(
            _funding_route(
                "route:funding:a",
                broker_id=broker_a.broker_id,
                source_kind="contribution",
                source_id=contribution.contribution_id,
                amount=R(10),
            ),
            _funding_route(
                "route:funding:b",
                broker_id=broker_b.broker_id,
                source_kind="contribution",
                source_id=contribution.contribution_id,
                amount=R(10),
            ),
        ),
        order_routes=(
            _order_route(
                "route:buy:a",
                broker_id=broker_a.broker_id,
                asset_id="asset:a",
                capability=capability_a,
                fee_id=fee_a.fee_schedule_id,
                side="buy",
            ),
            _order_route(
                "route:buy:b",
                broker_id=broker_b.broker_id,
                asset_id="asset:a",
                capability=capability_b,
                fee_id=fee_b.fee_schedule_id,
                side="buy",
            ),
        ),
    )


def test_multiroute_funding_sums_by_source_and_detects_overcommitment() -> None:
    scenario = _multiroute_funding_scenario()
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id(
                    "funding_transfer",
                    "route:funding:a",
                ): 600,
                exact_decision_id(
                    "funding_transfer",
                    "route:funding:b",
                ): 500,
            },
        ),
    )
    source = _by_id(
        evaluation.funding_sources,
        "source_id",
        "contribution:a",
    )

    assert source.selected == R(10)
    assert source.transferred == R(11)
    assert source.remaining == R(-1)
    assert source.selected == source.transferred + source.remaining
    # _source_reachability now floors an overcommitted (negative) remaining
    # to effective_remaining = max(remaining, 0) = max(-1, 0) = 0 before
    # splitting it into reachable/trapped, so both are exactly zero here
    # (0 + 0 == max(-1, 0), matching ExactFundingSourceEvaluation's
    # reconciliation invariant) rather than crashing.
    assert source.structurally_reachable_amount == R(0)
    assert source.structurally_trapped_amount == R(0)
    assert "FUNDING_WITHIN_SELECTED" in evaluation.conflict_codes
    assert "FUNDING_SOURCE_CONSERVATION" not in evaluation.conflict_codes
    assert "NO_DOUBLE_COUNT" not in evaluation.conflict_codes


def test_self_transfer_has_zero_domain_and_never_posts_both_sides() -> None:
    scenario = _pac_scenario()
    route = _funding_route(
        "route:funding:self",
        broker_id="broker:a",
        source_kind="existing_cash",
        source_id="cash:a",
        amount=R(100),
    )
    scenario = replace(scenario, funding_routes=(route,))
    view = build_exact_policy_view(scenario)
    decision_id = exact_decision_id(
        "funding_transfer",
        "route:funding:self",
    )
    access = _decision(view, decision_id)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view),
    )

    assert access.lower_quanta == 0
    assert access.upper_quanta == 0
    assert evaluation.funding_transfers == ()
    assert not [
        posting
        for posting in evaluation.postings
        if posting.posting_id
        in {
            "funding-in:route:funding:self",
            "funding-out:route:funding:self",
        }
    ]
    constraint = _by_id(
        evaluation.constraints,
        "ref_id",
        "constraint:no_self_transfer:route:funding:self",
    )
    assert constraint.value == ZERO
    assert constraint.satisfied is True


def test_fixed_reference_excludes_structurally_trapped_cash_and_contribution() -> None:
    capability = _capability("capability:buy")
    fee = _fee("fee:buy", capability.capability_id, "buy")
    broker_a = _broker("broker:a", (capability,), (fee,))
    broker_b = _broker("broker:b")
    scenario = _scenario(
        "scenario:trapped",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a"),),
        brokers=(broker_a, broker_b),
        existing_cash=(
            _cash("cash:reachable", broker_a.broker_id, R(10)),
            _cash("cash:trapped", broker_b.broker_id, R(7)),
        ),
        contributions=(_contribution("contribution:trapped", R(5)),),
        order_routes=(
            _order_route(
                "route:buy",
                broker_id=broker_a.broker_id,
                asset_id="asset:a",
                capability=capability,
                fee_id=fee.fee_schedule_id,
                side="buy",
            ),
        ),
    )
    view = build_exact_policy_view(scenario)

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view),
    )

    assert evaluation.accounting is not None
    accounting = evaluation.accounting
    assert accounting.current_invested == ZERO
    assert accounting.selected_funding == R(22)
    assert accounting.reachable_funding == R(10)
    assert accounting.trapped_funding == R(12)
    assert accounting.fixed_reference == R(10)
    assert accounting.final_invested == ZERO
    assert accounting.shortfall == R(10)
    assert accounting.free_cash == R(10)
    assert accounting.identity_delta == ZERO
    source_states = {
        (item.source_kind, item.source_id): (
            item.selected,
            item.transferred,
            item.remaining,
            item.structurally_reachable_amount,
            item.structurally_trapped_amount,
        )
        for item in evaluation.funding_sources
    }
    assert source_states == {
        ("contribution", "contribution:trapped"): (
            R(5),
            ZERO,
            R(5),
            ZERO,
            R(5),
        ),
        ("existing_cash", "cash:reachable"): (
            R(10),
            ZERO,
            R(10),
            R(10),
            ZERO,
        ),
        ("existing_cash", "cash:trapped"): (
            R(7),
            ZERO,
            R(7),
            ZERO,
            R(7),
        ),
    }


def test_funding_source_reachability_splits_partial_remaining_by_route_capacity() -> None:
    """Mandated regression (d): a partially-transferred funding source whose
    remaining cash is split across a reachable and a structurally-trapped
    funding route. The identity structurally_reachable_amount +
    structurally_trapped_amount == remaining is already enforced by the
    model's own __post_init__ (see ExactFundingSourceEvaluation), so this
    test independently computes the expected reachable/trapped split from
    the real route-capacity accounting (unused transfer_cap on a
    buy-reaching route vs. a dead-end route) and asserts the evaluator
    reproduces exactly that split, with no double-counting against
    selected/transferred.
    """
    capability = _capability("capability:buy")
    fee = _fee("fee:buy", capability.capability_id, "buy")
    broker_a = _broker("broker:a", (capability,), (fee,))  # can reach a buy
    broker_b = _broker("broker:b")  # dead end: no order routes at all
    broker_c = _broker("broker:c")  # source's own broker: cannot itself reach a buy
    scenario = _scenario(
        "scenario:partial-transfer-reachability",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a"),),
        brokers=(broker_a, broker_b, broker_c),
        existing_cash=(_cash("cash:partial", broker_c.broker_id, R(20)),),
        funding_routes=(
            _funding_route(
                "route:funding:reach",
                broker_id=broker_a.broker_id,
                source_kind="existing_cash",
                source_id="cash:partial",
                amount=R(6),
                priority=1,
            ),
            _funding_route(
                "route:funding:trap",
                broker_id=broker_b.broker_id,
                source_kind="existing_cash",
                source_id="cash:partial",
                amount=R(50),
                priority=2,
            ),
        ),
        order_routes=(
            _order_route(
                "route:buy",
                broker_id=broker_a.broker_id,
                asset_id="asset:a",
                capability=capability,
                fee_id=fee.fee_schedule_id,
                side="buy",
            ),
        ),
    )
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {exact_decision_id("funding_transfer", "route:funding:reach"): 400},
        ),
    )

    source = _by_id(evaluation.funding_sources, "source_id", "cash:partial")
    assert source.selected == R(20)
    assert source.transferred == R(4)
    assert source.remaining == R(16)
    # route:funding:reach has R(6) - R(4) = R(2) unused capacity toward
    # broker:a, which can reach a buy; route:funding:trap's full R(50) is
    # entirely toward broker:b, a dead end, so it contributes nothing.
    assert source.structurally_reachable_amount == R(2)
    assert source.structurally_trapped_amount == R(14)
    assert source.structurally_reachable_amount + source.structurally_trapped_amount == source.remaining
    assert source.transferred + source.structurally_reachable_amount + source.structurally_trapped_amount == source.selected


def test_posted_fee_can_make_native_cash_negative_and_raise_leverage_conflicts() -> None:
    scenario = _pac_scenario(
        cash=R(10),
        fixed_fee=ONE,
        route_cap=ONE,
    )
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id(
                    "buy_quantum",
                    "route:buy:a",
                ): 1
            },
        ),
    )
    ledger = tuple(row for row in evaluation.ledgers if (row.broker_id, row.currency) == ("broker:a", "EUR"))
    assert len(ledger) == 1
    (row,) = ledger

    assert row.initial_selected == R(10)
    assert row.buy_debit == R(10)
    assert row.buy_fees == ONE
    assert row.final_spendable == R(-1)
    assert "SPENDABLE_CASH_NONNEGATIVE" in evaluation.conflict_codes
    assert "NO_SHORT_OR_LEVERAGE" in evaluation.conflict_codes
    assert evaluation.candidate_valid is True
    assert evaluation.feasible is False


def test_native_ledgers_and_accounting_identity_reconcile_all_fx_columns() -> None:
    scenario = _funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    fx_debit_id = exact_decision_id(
        "fx_debit",
        _fx_debit_key("route:buy:usd", "EUR"),
    )
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id(
                    "funding_transfer",
                    "route:funding:eur",
                ): 15_000,
                fx_debit_id: 10_000,
                exact_decision_id(
                    "buy_quantum",
                    "route:buy:usd",
                ): 1,
            },
        ),
    )
    ledger_by_key = {(row.broker_id, row.currency): row for row in evaluation.ledgers}

    assert tuple(ledger_by_key) == tuple(sorted(ledger_by_key))
    source_eur = ledger_by_key[("broker:source", "EUR")]
    destination_eur = ledger_by_key[("broker:destination", "EUR")]
    destination_usd = ledger_by_key[("broker:destination", "USD")]
    assert source_eur.initial_selected == R(200)
    assert source_eur.funding_out == R(150)
    assert source_eur.final_spendable == R(50)
    assert destination_eur.funding_in == R(150)
    assert destination_eur.fx_debit == R(100)
    assert destination_eur.final_spendable == R(50)
    assert destination_eur.final_physical == R(50)
    assert destination_usd.fx_credit == R(594, 5)
    assert destination_usd.buy_debit == R(100)
    assert destination_usd.final_spendable == R(94, 5)

    assert evaluation.accounting is not None
    accounting = evaluation.accounting
    # EUR/USD is now valued (mark-to-market) at the *official* rate derived
    # from the same canonical fx_rates map used for conversions (5/6, the
    # exact inverse of the declared 6/5 EUR->USD rate) -- there is no more
    # independent valuation_rates axis, so these no longer match the old
    # pre-redesign fixture numbers. current_invested/selected_funding/
    # reachable_funding/trapped_funding/fixed_reference are unaffected by the
    # FX redesign (no order in this scenario reaches a buy through more than
    # one direct pair), so those keep their previous values.
    assert accounting.selected_funding == R(200)
    assert accounting.reachable_funding == R(200)
    assert accounting.trapped_funding == ZERO
    assert accounting.fixed_reference == R(200)
    assert accounting.identity_delta == ZERO
    assert accounting.shortfall == (accounting.free_cash + accounting.physical_reserves + accounting.economic_losses + accounting.rounding_adjustment)
    assert abs(accounting.rounding_adjustment) <= accounting.rounding_bound


def test_sell_extension_keeps_fixed_reference_and_reconciles_u_identity() -> None:
    scenario = _invest_and_sell_scenario()
    baseline_view, baseline = _invest_only_baseline(scenario)
    baseline_result = evaluate_exact_candidate(
        scenario,
        baseline_view,
        baseline,
    )
    extension = _sell_extension(scenario, baseline)
    extension_result = evaluate_exact_candidate(
        scenario,
        extension,
        _candidate(
            extension,
            {
                exact_decision_id("buy_quantum", "route:buy:b"): 4,
                exact_decision_id("sell_quantum", "route:sell:a"): 2,
            },
        ),
    )

    assert baseline_result.accounting is not None
    assert extension_result.accounting is not None
    assert baseline_result.accounting.fixed_reference == R(120)
    assert extension_result.accounting.fixed_reference == R(120)
    assert extension_result.accounting.final_invested == R(120)
    assert extension_result.accounting.shortfall == ZERO
    assert extension_result.accounting.identity_delta == ZERO
    assert extension_result.accounting.shortfall == (extension_result.accounting.free_cash + extension_result.accounting.physical_reserves + extension_result.accounting.economic_losses + extension_result.accounting.rounding_adjustment)


def test_sell_extension_eligibility_and_gate_metadata_are_exact() -> None:
    scenario = _invest_and_sell_scenario()
    baseline_view, baseline = _invest_only_baseline(scenario)
    baseline_result = evaluate_exact_candidate(
        scenario,
        baseline_view,
        baseline,
    )
    view = _sell_extension(scenario, baseline)
    asset_a = _by_id(
        baseline_result.assets,
        "asset_id",
        "asset:a",
    )
    asset_b = _by_id(
        baseline_result.assets,
        "asset_id",
        "asset:b",
    )
    gate = _by_id(
        view.sell_gates,
        "sell_decision_id",
        exact_decision_id("sell_quantum", "route:sell:a"),
    )

    assert asset_a.residual == R(20)
    assert asset_b.residual == R(-20)
    assert (
        _decision(
            view,
            exact_decision_id("sell_quantum", "route:sell:a"),
        ).mode
        == "mutable"
    )
    assert (
        _decision(
            view,
            exact_decision_id("sell_quantum", "route:sell:b"),
        ).mode
        == "disabled"
    )
    assert gate.fixed_incremental_buy_decision_ids == (
        exact_decision_id("buy_quantum", "route:buy:a"),
        exact_decision_id("buy_quantum", "route:buy:b"),
    )
    # _invest_and_sell_scenario declares no fx_rates and a single broker, so
    # no fx_debit decision exists at all here (unlike the old fixture, which
    # had a broker-scoped fx_route present regardless of use).
    assert gate.reopened_decision_ids == (exact_decision_id("funding_transfer", "route:funding"),)
    assert gate.counterfactuals == (
        "decrement_one_quantum",
        "zero_row",
    )
    requirement = _by_id(
        view.proof_requirements,
        "requirement_id",
        "proof:sell-irreducibility",
    )
    assert baseline_view.scenario_fingerprint == exact_scenario_fingerprint(scenario)
    assert view.scenario_fingerprint == baseline_view.scenario_fingerprint
    assert baseline_view.sell_gates == ()
    assert baseline_view.proof_requirements == ()
    assert view.proof_requirements == (requirement,)
    assert requirement.allowed_sources == (
        "deterministic_conflict",
        "exhaustive_oracle",
    )


def test_sell_gates_exist_only_for_positive_eligible_domains() -> None:
    scenario = _invest_and_sell_scenario(zero_domain_sell=True)
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    zero_id = exact_decision_id(
        "sell_quantum",
        "route:sell:a:zero-domain",
    )

    zero_access = _decision(view, zero_id)
    assert zero_access.upper_quanta == 0
    assert zero_id not in {gate.sell_decision_id for gate in view.sell_gates}
    assert {gate.sell_decision_id for gate in view.sell_gates} == {
        exact_decision_id("sell_quantum", "route:sell:a"),
    }


def test_reconstructed_sell_view_revalidates_embedded_baseline_economics() -> None:
    scenario = _invest_and_sell_scenario()
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    buy_id = exact_decision_id("buy_quantum", "route:buy:b")
    access = _decision(view, buy_id)
    assert access.upper_quanta >= 3
    changed = replace(
        access,
        baseline_quanta=3,
        lower_quanta=3,
    )
    tampered = replace(
        view,
        decisions=tuple(changed if item.decision_id == buy_id else item for item in view.decisions),
    )

    with pytest.raises(
        ExactPolicyContractError,
        match="baseline is not exact-feasible",
    ):
        evaluate_exact_candidate(
            scenario,
            tampered,
            _candidate(tampered),
        )


@pytest.mark.parametrize(
    ("case", "expected_satisfied"),
    [
        pytest.param(
            "missing-incremental-buy",
            False,
            id="missing-incremental-buy",
        ),
        pytest.param(
            "unnecessary-sell",
            False,
            id="sell-zero-still-fundable",
        ),
        pytest.param(
            "necessary-sell",
            True,
            id="sell-zero-unfundable",
        ),
    ],
)
def test_active_sell_requires_incremental_buy_and_unfundable_zero_sell_vector(
    case: str,
    expected_satisfied: bool,
) -> None:
    contribution = R(40) if case == "unnecessary-sell" else R(20)
    scenario = _invest_and_sell_scenario(
        contribution_amount=contribution,
    )
    _baseline_view, baseline = _invest_only_baseline(scenario)
    view = _sell_extension(scenario, baseline)
    values = {
        exact_decision_id("sell_quantum", "route:sell:a"): 1,
    }
    if case != "missing-incremental-buy":
        values[exact_decision_id("buy_quantum", "route:buy:b")] = 3

    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view, values),
    )
    constraint = _by_id(
        evaluation.constraints,
        "ref_id",
        "constraint:sell_funds_incremental_buy:global",
    )

    assert constraint.value == (ONE if expected_satisfied else ZERO)
    assert constraint.satisfied is expected_satisfied
    assert ("SELL_FUNDS_INCREMENTAL_BUY" in evaluation.conflict_codes) is (not expected_satisfied)


def _objective_map(
    view: ExactPolicyView,
    evaluation: Any,
) -> dict[str, ExactRatio]:
    return {
        ref.code: _by_id(
            evaluation.objectives,
            "ref_id",
            ref.ref_id,
        ).value
        for ref in view.objectives
    }


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("proportional", id="proportional"),
        pytest.param("min-fragmentation", id="min-fragmentation"),
        pytest.param("invest-only", id="invest-only"),
        pytest.param("invest-and-sell", id="invest-and-sell"),
        pytest.param("deployment", id="deployment"),
    ],
)
def test_exact_objective_sequences_and_values(case: str) -> None:
    if case == "proportional":
        scenario = _pac_scenario(policy="proportional")
        view = build_exact_policy_view(scenario)
        evaluation = evaluate_exact_candidate(
            scenario,
            view,
            _candidate(
                view,
                {
                    exact_decision_id(
                        "buy_quantum",
                        "route:buy:a",
                    ): 3
                },
            ),
        )
        expected_codes = (
            "fixed_l2",
            "shortfall",
            "route_priority",
            "explicit_cost",
            "active_order_rows",
        )
        expected_values = {
            "fixed_l2": R(4_900),
            "shortfall": R(70),
            "route_priority": R(7),
            "explicit_cost": ZERO,
            "active_order_rows": ONE,
        }
    elif case == "min-fragmentation":
        scenario = _min_fragmentation_scenario()
        view = build_exact_policy_view(scenario)
        evaluation = evaluate_exact_candidate(
            scenario,
            view,
            _candidate(
                view,
                {
                    exact_decision_id(
                        "buy_quantum",
                        "route:buy:a",
                    ): 1,
                    exact_decision_id(
                        "buy_quantum",
                        "route:buy:b",
                    ): 1,
                },
            ),
        )
        expected_codes = (
            "fixed_l2",
            "shortfall",
            "split_asset_count",
            "active_order_rows",
            "route_priority",
            "explicit_cost",
        )
        expected_values = {
            "fixed_l2": R(6_400),
            "shortfall": R(80),
            "split_asset_count": ONE,
            "active_order_rows": R(2),
            "route_priority": R(4),
            "explicit_cost": ZERO,
        }
    elif case == "invest-only":
        scenario = _invest_only_scenario()
        view = build_exact_policy_view(scenario)
        evaluation = evaluate_exact_candidate(
            scenario,
            view,
            _candidate(
                view,
                {
                    exact_decision_id(
                        "funding_transfer",
                        "route:funding",
                    ): 2_000,
                    exact_decision_id(
                        "buy_quantum",
                        "route:buy:b",
                    ): 2,
                },
            ),
        )
        expected_codes = (
            "fixed_l2",
            "shortfall",
            "turnover",
            "explicit_cost",
            "active_order_rows",
        )
        expected_values = {
            "fixed_l2": R(800),
            "shortfall": ZERO,
            "turnover": R(20),
            "explicit_cost": ZERO,
            "active_order_rows": ONE,
        }
    else:
        scenario = _invest_and_sell_scenario()
        _baseline_view, baseline = _invest_only_baseline(scenario)
        extension = _sell_extension(scenario, baseline)
        primary = _candidate(
            extension,
            {
                exact_decision_id(
                    "buy_quantum",
                    "route:buy:b",
                ): 4,
                exact_decision_id(
                    "sell_quantum",
                    "route:sell:a",
                ): 2,
            },
            candidate_id="candidate:primary",
        )
        if case == "invest-and-sell":
            view = extension
            evaluation = evaluate_exact_candidate(
                scenario,
                view,
                primary,
            )
            expected_codes = (
                "fixed_l2",
                "shortfall",
                "turnover",
                "explicit_cost",
                "active_order_rows",
            )
            expected_values = {
                "fixed_l2": ZERO,
                "shortfall": ZERO,
                "turnover": R(60),
                "explicit_cost": ZERO,
                "active_order_rows": R(2),
            }
        elif case == "deployment":
            view = build_exact_policy_view(
                scenario,
                purpose="deployment",
                baseline=primary,
            )
            evaluation = evaluate_exact_candidate(
                scenario,
                view,
                _candidate(view),
            )
            expected_codes = (
                "shortfall",
                "fixed_l2",
                "incremental_cost",
                "incremental_order_rows",
            )
            expected_values = {
                "shortfall": ZERO,
                "fixed_l2": ZERO,
                "incremental_cost": ZERO,
                "incremental_order_rows": ZERO,
            }
        else:
            raise AssertionError(f"Unknown objective witness {case!r}")

    assert tuple(ref.code for ref in view.objectives) == expected_codes
    assert tuple(ref.ordinal for ref in view.objectives) == tuple(range(1, len(expected_codes) + 1))
    assert all(ref.sense == "min" for ref in view.objectives)
    assert _objective_map(view, evaluation) == expected_values


def test_deployment_objectives_measure_incremental_cost_and_rows() -> None:
    scenario = _pac_scenario(fixed_fee=ONE)
    primary_view = build_exact_policy_view(
        scenario,
        view_id="view:primary",
    )
    primary = _candidate(
        primary_view,
        candidate_id="candidate:primary-zero",
    )
    deployment = build_exact_policy_view(
        scenario,
        purpose="deployment",
        baseline=primary,
    )
    decision_id = exact_decision_id("buy_quantum", "route:buy:a")

    evaluation = evaluate_exact_candidate(
        scenario,
        deployment,
        _candidate(deployment, {decision_id: 1}),
    )
    values = _objective_map(deployment, evaluation)

    assert values["incremental_cost"] == ONE
    assert values["incremental_order_rows"] == ONE
    assert evaluation.costs is not None
    assert evaluation.costs.explicit_cost == ONE


def test_shortfall_objective_is_signed_and_rounding_bounded() -> None:
    scenario = _pac_scenario(
        price=ONE,
        capability_kind="monetary_amount",
        step=R(25_001, 250),
        cash=R(100),
        route_cap=R(101),
    )
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                exact_decision_id(
                    "buy_quantum",
                    "route:buy:a",
                ): 1
            },
        ),
    )

    assert evaluation.feasible is True
    assert evaluation.accounting is not None
    assert evaluation.accounting.fixed_reference == R(100)
    assert evaluation.accounting.final_invested == R(25_001, 250)
    assert evaluation.accounting.shortfall == R(-1, 250)
    assert evaluation.accounting.rounding_adjustment == R(-1, 250)
    assert evaluation.accounting.rounding_bound == R(1, 200)
    assert evaluation.accounting.identity_delta == ZERO
    assert _objective_map(view, evaluation)["shortfall"] == R(-1, 250)


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param("build", id="build-entry"),
        pytest.param("evaluate", id="evaluate-entry"),
    ],
)
def test_cancellation_callback_propagates_at_public_entry(entry: str) -> None:
    scenario = _pac_scenario()
    if entry == "build":
        checkpoint = _CancelIn("build_exact_policy_view")

        def operation() -> object:
            return build_exact_policy_view(
                scenario,
                checkpoint=checkpoint,
            )

    else:
        view = build_exact_policy_view(scenario)
        checkpoint = _CancelIn("evaluate_exact_candidate")

        def operation() -> object:
            return evaluate_exact_candidate(
                scenario,
                view,
                _candidate(view),
                checkpoint=checkpoint,
            )

    with pytest.raises(_Cancelled, match=entry):
        operation()

    assert checkpoint.observed is True


@pytest.mark.parametrize(
    "target",
    [
        pytest.param("_build_constraint_refs", id="constraint-ref-loop"),
        # NOTE: a "source-reachability-loop" case (target=_source_reachability)
        # existed before this redesign. It is removed here, not merely
        # reference-repaired: _source_reachability and its _can_reach_buy
        # callee (evaluator.py ~733/716) contain no internal check_budget
        # call, so cancellation can never be observed mid-function there no
        # matter how the scenario is shaped -- check_budget is only called by
        # _evaluate_funding's outer loops, before/after (never during) each
        # _source_reachability call. This is a possible production gap
        # (flagged out-of-scope in this session's final report), not a
        # test-side stale reference.
        pytest.param("_evaluate_orders", id="order-replay-loop"),
        pytest.param(
            "reconcile_broker_ledgers",
            id="ledger-reconciliation-loop",
        ),
        # Mandated regression (a): _global_constraint_facts threads a
        # Checkpoint through every scan loop (asset reconciliation, sell
        # postings reconciliation, no_short_or_leverage) so cancellation can
        # abort mid-scan, not just at function entry.
        pytest.param(
            "_global_constraint_facts",
            id="global-constraint-facts-loop",
        ),
    ],
)
def test_cancellation_propagates_from_nontrivial_exact_loops(
    target: str,
) -> None:
    scenario = _funding_fx_scenario()
    checkpoint = _CancelIn(target)

    if target == "_build_constraint_refs":

        def operation() -> object:
            return build_exact_policy_view(
                scenario,
                checkpoint=checkpoint,
            )

    else:
        view = build_exact_policy_view(scenario)
        values = {access.decision_id: 1 for access in view.decisions if access.family == "fx_debit"}
        if scenario.snapshot.snapshot_id == "scenario:funding-fx":
            values.update(
                {
                    exact_decision_id(
                        "funding_transfer",
                        "route:funding:eur",
                    ): 15_000,
                    exact_decision_id(
                        "fx_debit",
                        _fx_debit_key("route:buy:usd", "EUR"),
                    ): 100,
                    exact_decision_id(
                        "buy_quantum",
                        "route:buy:usd",
                    ): 1,
                }
            )

        def operation() -> object:
            return evaluate_exact_candidate(
                scenario,
                view,
                _candidate(view, values),
                checkpoint=checkpoint,
            )

    with pytest.raises(_Cancelled, match=target):
        operation()

    assert checkpoint.observed is True
