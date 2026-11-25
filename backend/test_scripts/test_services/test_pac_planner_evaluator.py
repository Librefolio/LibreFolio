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

from backend.app.schemas.pac_allocator.request import PacPlannerRequest
from backend.app.services.pac_allocator import models as pac_models
from backend.app.services.pac_allocator.evaluation import evaluator as EV
from backend.app.services.pac_allocator.evaluation.errors import ExactEvaluatorError, ExactPolicyContractError, ExactScenarioContractError
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.evaluation.keys import asset_broker_key, exact_decision_id
from backend.app.services.pac_allocator.evaluation.limits import limited_entries
from backend.app.services.pac_allocator.evaluation.reachability import fx_decision_specs
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, exact_scenario_fingerprint
from backend.app.services.pac_allocator.ledger import (
    DuplicatePostingError,
    ExactLedgerError,
    PostingFamilyError,
    exact_flow_posting,
    reconcile_broker_ledgers,
    rounded_money_posting,
)
from backend.app.services.pac_allocator.limits import check_maximum_below_current, check_minimum_above_maximum, check_minimums_exceed_reference, fixed_reference_of, trapped_cash_by_cell
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    DecisionAccess,
    EntityRef,
    ExactAsset,
    ExactAssetQuote,
    ExactAssetTax,
    ExactBroker,
    ExactBrokerLedgerEvaluation,
    ExactConflict,
    ExactContribution,
    ExactCostBasis,
    ExactCurrencySpec,
    ExactEvaluation,
    ExactExistingCash,
    ExactFeeSchedule,
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
from backend.app.services.pac_allocator.numeric import ExactRatio, post_floor
from backend.test_scripts.test_services import _reb_small_cases as cases
from backend.test_scripts.test_services._pac_fx_decisions import fx_id, fx_spec

R = ExactRatio
ZERO = R(0)
from backend.app.services.pac_allocator.evaluation.errors import ExactReplayRejectedError

ONE = R(1)
CENT = R(1, 100)
AS_OF = date(2026, 9, 16)
CAPTURED_AT = datetime(2026, 9, 16, 20, 0, tzinfo=UTC)
PROVENANCE_ID = "provenance:test"


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
    conversion_mode: str = "manual",
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
        conversion_mode=conversion_mode,
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
    target_fidelity: pac_models.ExactTargetFidelity | None = None,
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
        # A Rebalancer scenario is «Balanced» unless the test names another fidelity (B1 of project 67).
        target_fidelity=target_fidelity if target_fidelity is not None or product == "pac" else pac_models.BALANCED_FIDELITY,
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
                    "conversion_mode": "manual",
                }
            ],
            "existing_cash": [
                {
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
                    "kind": "asset",
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
                cap=route_cap,
                margin=margin,
                priority=priority,
                currency=quote_currency,
            ),
        ),
        currency_quantums=((quote_currency, CENT),),
    )


def _pac_scenario_with_asset_minimum(minimum: ExactRatio, **kwargs) -> ExactPlannerScenario:
    """``_pac_scenario`` with a minimum, in EUR, on the final value of its one Asset (V5): the construction that makes a PAC
    infeasible now that a route's «required minimum» is gone (M19). Doing nothing does not meet it, and a route cap below it
    cannot either."""
    scenario = _pac_scenario(**kwargs)
    return replace(scenario, target_weights=(ExactTargetWeight("asset:a", ONE, minimum=pac_models.ExactLimit("amount", minimum)),))


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


def _sell_door(
    scenario: ExactPlannerScenario,
    quanta: dict[str, int],
) -> ExactPolicyView:
    """The way into a replay with an active sell while ``primary`` keeps sells disabled (B1, D6 of project 67).

    A ``deployment`` view over a base that already holds ``quanta`` and the whole contribution: its sells are frozen at the
    base, its buys start from it, and a candidate equal to the base replays the sell with every rule. C1 changes only this
    body, to a ``primary`` view with the sells open; the expectations on the sale economy do not move.
    """
    primary = build_exact_policy_view(scenario, view_id="view:sell-door:decisions")
    funding = {}
    if any(item.contribution_id == "contribution:a" for item in scenario.contributions):
        contribution = _by_id(scenario.contributions, "contribution_id", "contribution:a")
        funding[exact_decision_id("funding_transfer", "route:funding")] = _integer_quanta(contribution.amount.amount)
    base = _candidate(primary, {**funding, **quanta}, candidate_id="candidate:sell-door")
    return build_exact_policy_view(scenario, purpose="deployment", baseline=base, view_id="view:sell-door")


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
    # were dropped in a538ee94d; the surviving set below is planner v2 only.
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

    fx_debit_id = fx_id(scenario, source="EUR", destination="USD")
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
    checkpoint = _ObserveIn("build_constraint_refs")

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
    funding_id = exact_decision_id("funding_transfer", "route:funding")
    buy_b_id = exact_decision_id("buy_quantum", "route:buy:b")
    sell_b_id = exact_decision_id("sell_quantum", "route:sell:b")
    # A disabled decision lives in ``primary`` (its sells, until C1); frozen and additive ones in ``deployment``.
    view = build_exact_policy_view(scenario) if case == "disabled" else _sell_door(scenario, {buy_b_id: 2})
    valid = _candidate(view, candidate_id=f"candidate:{case}")
    duplicate = _by_id(valid.decisions, "decision_id", buy_b_id)
    buy_access = _decision(view, buy_b_id)
    funding_access = _decision(view, funding_id)
    if case != "disabled":
        assert buy_access.baseline_quanta > 0
        assert funding_access.frozen_quanta is not None
    # The «disabled» case reads a primary view, where nothing is frozen or additive: its candidate is built apart.
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
        "not-frozen": _candidate(
            view,
            {funding_id: (funding_access.frozen_quanta or 1) - 1},
            candidate_id=valid.candidate_id,
        ),
        "not-additive": _candidate(
            view,
            {buy_b_id: max(buy_access.baseline_quanta - 1, 0)},
            candidate_id=valid.candidate_id,
        ),
    }
    candidate = _candidate(view, {sell_b_id: 1}, candidate_id=valid.candidate_id) if case == "disabled" else candidates[case]

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
        pytest.param("invest-and-sell-primary", id="invest-and-sell-primary"),
    ],
)
def test_primary_policy_views_start_from_zero(
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
    elif case == "invest-and-sell-primary":
        scenario = _invest_and_sell_scenario()
        view = build_exact_policy_view(scenario)
    else:
        raise AssertionError(f"Unknown policy-view witness {case!r}")

    assert all(item.baseline_quanta == 0 for item in view.decisions)
    assert all(item.lower_quanta == 0 for item in view.decisions)
    if view.policy == "invest_and_sell":
        assert all(item.mode == "disabled" for item in view.decisions if item.family == "sell_quantum")


def test_deployment_freezes_funding_fx_and_sell_but_keeps_buy_additive() -> None:
    scenario = _invest_and_sell_scenario()
    contribution = _by_id(scenario.contributions, "contribution_id", "contribution:a")
    primary = _candidate(
        build_exact_policy_view(scenario),
        {
            exact_decision_id("funding_transfer", "route:funding"): _integer_quanta(contribution.amount.amount),
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
    "policy",
    [
        pytest.param("proportional", id="pac"),
        pytest.param("invest_and_sell", id="rebalancer"),
    ],
)
def test_baseline_dependent_default_view_ids_use_full_sha256(
    policy: str,
) -> None:
    """``deployment`` is the one purpose with a baseline: its default view ID ends with the full SHA-256 of that baseline."""
    purpose = "deployment"
    scenario = _pac_scenario() if policy == "proportional" else _invest_and_sell_scenario()
    baseline_view = build_exact_policy_view(scenario, view_id="view:primary")
    buy_id = exact_decision_id("buy_quantum", "route:buy:a")
    first = _candidate(baseline_view, {buy_id: 0}, candidate_id="candidate:first")
    second = _candidate(baseline_view, {buy_id: 1}, candidate_id="candidate:second")

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


def test_total_tie_covers_every_decision_once_in_semantic_order() -> None:
    scenario = _invest_and_sell_scenario()
    view = build_exact_policy_view(scenario)
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
    """Mandated regression (b): asset_broker_key is the composite key used
    at the position-constraint ref/fact sites (formerly an ambiguous plain
    f"{asset_id}:{broker_id}" join). A naive join would produce the
    identical string "a:b:c" for both pairs below (the ':' separator could
    be reassigned across the asset_id/broker_id boundary); the
    length-prefixed scheme must keep them distinct.
    """
    key_one = asset_broker_key("a:b", "c")
    key_two = asset_broker_key("a", "b:c")

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
        fx_id(scenario, source="EUR", destination="USD"): 0,
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
        pytest.param("transfer_in", "credit", id="transfer-in"),
        pytest.param("transfer_out", "debit", id="transfer-out"),
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
    ("family", "direction"),
    [
        pytest.param("fx_credit", "credit", id="fx-credit"),
        pytest.param("buy_debit", "debit", id="buy-debit"),
        pytest.param("gross_sell_credit", "credit", id="sell-gross"),
        pytest.param("buy_fee", "debit", id="buy-fee"),
        pytest.param("sell_fee", "debit", id="sell-fee"),
        pytest.param("broker_withheld_tax", "debit", id="broker-tax"),
        pytest.param("self_reserved_tax", "debit", id="self-tax"),
    ],
)
@pytest.mark.parametrize(
    ("exact_amount", "credit_posting", "debit_posting"),
    [
        # (posted, rounding_delta, accounting adjustment): a credit posts its
        # floor and a debit its ceiling, so both adjustments cost the plan.
        # 1.005 is the half-cent tie, which HALF_UP posted as 1.01 either way.
        pytest.param(
            R(201, 200),
            (ONE, R(-1, 200), R(1, 200)),
            (R(101, 100), R(1, 200), R(1, 200)),
            id="tie",
        ),
        # 1.004 is below the tie, which HALF_UP posted as 1.00 either way.
        pytest.param(
            R(251, 250),
            (ONE, R(-1, 250), R(1, 250)),
            (R(101, 100), R(3, 500), R(3, 500)),
            id="below-tie",
        ),
    ],
)
def test_monetary_posting_families_round_against_the_plan_once(
    family: LedgerPostingFamily,
    direction: str,
    exact_amount: ExactRatio,
    credit_posting: tuple[ExactRatio, ExactRatio, ExactRatio],
    debit_posting: tuple[ExactRatio, ExactRatio, ExactRatio],
) -> None:
    posting = rounded_money_posting(
        posting_id=f"posting:{family}",
        family=family,
        broker_id="broker:a",
        currency="EUR",
        exact_amount=exact_amount,
        quantum=CENT,
    )
    posted_amount, rounding_delta, accounting_delta = credit_posting if direction == "credit" else debit_posting

    assert posting.direction == direction
    assert posting.exact_amount == exact_amount
    assert posting.posted_amount == posted_amount
    assert posting.quantum == CENT
    assert posting.rounding_delta == rounding_delta
    assert posting.accounting_rounding_adjustment == accounting_delta
    assert posting.rounding_delta == posting.posted_amount - posting.exact_amount
    assert ZERO <= posting.accounting_rounding_adjustment < posting.quantum


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
        ("transfer-in", "transfer_in", R(3)),
        ("transfer-out", "transfer_out", R(2)),
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
    assert (row.transfer_in, row.transfer_out) == (R(3), R(2))
    assert row.raw_rounding_delta == ZERO
    assert row.accounting_rounding_adjustment == ZERO
    assert row.final_spendable == R(10)
    assert row.final_physical == R(11)
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
        pytest.param("debit-rounded-down", id="debit-rounded-down"),
        pytest.param("credit-rounded-up", id="credit-rounded-up"),
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
    elif case == "debit-rounded-down":
        # 1.004 posted 1.00 is what HALF_UP gave; a debit must post its ceiling, 1.01.
        malformed = ExactLedgerPosting(
            posting_id="posting:a",
            family="buy_debit",
            direction="debit",
            broker_id="broker:a",
            currency="EUR",
            entity_refs=(),
            exact_amount=R(251, 250),
            posted_amount=ONE,
            quantum=CENT,
            rounding_delta=R(-1, 250),
        )
    elif case == "credit-rounded-up":
        # 1.005 posted 1.01 is what HALF_UP gave; a credit must post its floor, 1.00.
        malformed = ExactLedgerPosting(
            posting_id="posting:a",
            family="fx_credit",
            direction="credit",
            broker_id="broker:a",
            currency="EUR",
            entity_refs=(),
            exact_amount=R(201, 200),
            posted_amount=R(101, 100),
            quantum=CENT,
            rounding_delta=R(1, 200),
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
    fx_debit_id = fx_id(scenario, source="EUR", destination="USD")
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
    (action,) = evaluation.fx
    debit = _by_id(
        evaluation.postings,
        "posting_id",
        f"fx-debit:{fx_spec(scenario, source='EUR', destination='USD').key}",
    )
    credit = _by_id(
        evaluation.postings,
        "posting_id",
        f"fx-credit:{fx_spec(scenario, source='EUR', destination='USD').key}",
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


def _planning_rate_scenario(cross_rate: ExactRatio) -> ExactPlannerScenario:
    """RON 100 at one Broker, one USD 21.83 unit, and the RON/USD ``cross_rate``.

    The valuation currency is EUR (4.97 RON and 1.085 USD per EUR), so the
    triangle RON -> EUR -> USD is 1.085 / 4.97 = 31/142 = 0.21830985915...
    No spread, no fee: the conversion is the only arithmetic.
    """
    capability = _capability("capability:usd")
    buy_fee = _fee(
        "fee:buy:usd",
        capability.capability_id,
        "buy",
        currency="USD",
    )
    broker = _broker("broker:a", (capability,), (buy_fee,))
    return _scenario(
        "scenario:planning-rate",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:usd", price=R(2183, 100), currency="USD"),),
        brokers=(broker,),
        existing_cash=(_cash("cash:ron", broker.broker_id, R(100), currency="RON"),),
        order_routes=(
            _order_route(
                "route:buy:usd",
                broker_id=broker.broker_id,
                asset_id="asset:usd",
                capability=capability,
                fee_id=buy_fee.fee_schedule_id,
                side="buy",
                cap=ONE,
                currency="USD",
            ),
        ),
        fx_rates=(
            _fx_rate("EUR", "RON", R(497, 100)),
            _fx_rate("EUR", "USD", R(217, 200)),
            _fx_rate("RON", "USD", cross_rate),
        ),
        currency_quantums=(("EUR", CENT), ("RON", CENT), ("USD", CENT)),
    )


def _planning_rate_replay(cross_rate: ExactRatio) -> ExactEvaluation:
    """Convert the whole RON 100 to USD and buy the one unit with it."""
    scenario = _planning_rate_scenario(cross_rate)
    view = build_exact_policy_view(scenario)
    return evaluate_exact_candidate(
        scenario,
        view,
        _candidate(
            view,
            {
                fx_id(scenario, source="RON", destination="USD"): 10_000,
                exact_decision_id("buy_quantum", "route:buy:usd"): 1,
            },
        ),
    )


def test_fx_replay_plans_a_cross_rate_just_above_the_triangle_at_the_triangle() -> None:
    """A cross rate inside the coherence band converts at the triangle.

    RON/USD 0.2183098592 is the triangle rounded at the tenth decimal, a hair
    above it: the normalizer accepts it, and the conversion plans at
    min(approved x (1 - spread), val(RON) / val(USD)) = 31/142. The approved
    rate stays the user's. RON 100 credits exactly 1550/71 = USD 21.8309...,
    posted at its floor, 21.83, which pays the unit to the cent; valued in EUR
    the conversion loses nothing, where the user's rate would have gained.
    """
    evaluation = _planning_rate_replay(R(2_183_098_592, 10**10))
    (action,) = evaluation.fx

    assert evaluation.feasible is True, evaluation.conflict_codes
    assert action.source_currency == "RON"
    assert action.destination_currency == "USD"
    assert action.source_debit == R(100)
    assert action.approved_rate == R(2_183_098_592, 10**10)
    assert action.effective_rate == R(31, 142)
    assert action.exact_destination_credit == R(1550, 71)
    assert action.posted_destination_credit == R(2183, 100)
    assert action.spread_loss == ZERO
    assert _pool_ledger(evaluation, "broker:a", "RON").final_spendable == ZERO
    assert _pool_ledger(evaluation, "broker:a", "USD").final_spendable == ZERO


def test_fx_replay_keeps_a_cross_rate_below_the_triangle() -> None:
    """Below the triangle the user's rate is the planning rate, and it loses the gap.

    RON/USD 0.2183098591 sits under 31/142: the credit is RON 100 at the
    approved rate, USD 21.83098591, posted 21.83. The spread loss is the EUR
    value of the RON debit minus that of the exact USD credit: a few
    billionths of a euro, but strictly positive.
    """
    approved_rate = R(2_183_098_591, 10**10)
    evaluation = _planning_rate_replay(approved_rate)
    (action,) = evaluation.fx

    assert evaluation.feasible is True, evaluation.conflict_codes
    assert action.approved_rate == approved_rate
    assert action.effective_rate == approved_rate
    assert action.exact_destination_credit == R(2_183_098_591, 10**8)
    assert action.posted_destination_credit == R(2183, 100)
    assert action.spread_loss == R(10_000, 497) - R(2_183_098_591, 10**8) * R(200, 217)
    assert action.spread_loss > ZERO
    assert _pool_ledger(evaluation, "broker:a", "RON").final_spendable == ZERO
    assert _pool_ledger(evaluation, "broker:a", "USD").final_spendable == ZERO


def _multi_source_buy_scenario() -> ExactPlannerScenario:
    """One Broker with GBP and USD cash; route:buy:1 can convert both to EUR, route:buy:2 (the same Broker) shares GBP to EUR."""
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
    return scenario


def test_multi_source_buy_shares_a_cash_pool_across_two_buys() -> None:
    """A single BUY (route:buy:1) draws from two currency pools (GBP and USD
    existing cash) at the same Broker, each converting to its own EUR quote
    currency via a distinct direct fx_rate. A second BUY (route:buy:2)
    shares the same GBP pool. Asserts one ExactFxEvaluation per (Broker,
    source, destination) -- since A2 the two buys share one GBP -> EUR
    decision -- with spread applied once each, and that the shared GBP
    ledger row nets the combined draw from both BUYs correctly
    (SPENDABLE_CASH_NONNEGATIVE across combined postings -- already covered
    by the existing ledger-level check, no separate constraint code needed).
    A pure BUY-only (PAC) scenario is used deliberately: SELL requires the
    invest_and_sell two-phase baseline/extension flow, which is orthogonal to
    what this regression is about (multi-currency pool sharing).
    """
    scenario = _multi_source_buy_scenario()
    view = build_exact_policy_view(scenario)
    candidate = _candidate(
        view,
        {
            # route:buy:1 (2 units @ EUR99 = EUR198) and route:buy:2 (1 unit @
            # EUR99) draw on the hub's one GBP -> EUR decision (A2: one per
            # Broker and pair) and its one USD -> EUR decision: GBP100 ->
            # EUR198 + USD25 -> EUR99 cover the EUR297 of the three units.
            fx_id(scenario, source="GBP", destination="EUR"): 10_000,
            fx_id(scenario, source="USD", destination="EUR"): 2_500,
            exact_decision_id("buy_quantum", "route:buy:1"): 2,
            exact_decision_id("buy_quantum", "route:buy:2"): 1,
        },
    )

    evaluation = evaluate_exact_candidate(scenario, view, candidate)

    fx_by_key = {(item.broker_id, item.source_currency, item.destination_currency): item for item in evaluation.fx}
    assert set(fx_by_key) == {("broker:hub", "GBP", "EUR"), ("broker:hub", "USD", "EUR")}

    # GBP -> EUR: 1 GBP = 2 EUR official; effective = 2 * (1 - 1/100) = 99/50.
    # The two buys' GBP50 + GBP50 are one conversion of GBP100: 99 + 99 EUR.
    hub_gbp = fx_by_key[("broker:hub", "GBP", "EUR")]
    assert hub_gbp.source_debit == R(100)
    assert hub_gbp.approved_rate == R(2)
    assert hub_gbp.effective_rate == R(99, 50)
    assert hub_gbp.exact_destination_credit == R(198)
    assert hub_gbp.posted_destination_credit == R(198)
    assert hub_gbp.spread_loss == R(2)

    # USD -> EUR: 1 USD = 4 EUR official; effective = 4 * (1 - 1/100) = 99/25.
    hub_usd = fx_by_key[("broker:hub", "USD", "EUR")]
    assert hub_usd.source_debit == R(25)
    assert hub_usd.approved_rate == R(4)
    assert hub_usd.effective_rate == R(99, 25)
    assert hub_usd.exact_destination_credit == R(99)
    assert hub_usd.posted_destination_credit == R(99)
    assert hub_usd.spread_loss == R(1)

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
    a buy of the plan) while still
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
        # overweight (residual > 0).
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
    # The sell, and the USD buy it funds, reach the replay through the sale door (B1 of project 67).
    quanta = {exact_decision_id("sell_quantum", "route:sell-only"): 2, exact_decision_id("buy_quantum", "route:buy-usd"): 1}
    view = _sell_door(scenario, quanta)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta))

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


def test_positive_buy_quanta_post_a_nonzero_ceiling_debit() -> None:
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
    constraint = _by_id(
        evaluation.constraints,
        "ref_id",
        "constraint:buy_debit_positive:route:buy:a",
    )

    # One EUR 0.004 quantum posts its ceiling 0.01, never a zero debit (HALF_UP
    # posted 0.00, which only BUY_DEBIT_POSITIVE caught). The 0.006 rounding
    # cost stays inside the one-cent band and the pool keeps EUR 0.99.
    assert order.exact_cash_amount == R(1, 250)
    assert order.posted_cash_amount == CENT
    assert (constraint.value, constraint.satisfied) == (CENT, True)
    assert "BUY_DEBIT_POSITIVE" not in evaluation.conflict_codes
    assert evaluation.accounting is not None
    assert (evaluation.accounting.rounding_adjustment, evaluation.accounting.rounding_bound) == (R(3, 500), CENT)
    assert _pool_ledger(evaluation, "broker:a").final_spendable == R(99, 100)
    assert evaluation.candidate_valid is True
    assert evaluation.feasible is True


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
    quanta = {exact_decision_id("buy_quantum", "route:buy:b"): 3, exact_decision_id("sell_quantum", "route:sell:a"): 2}
    view = _sell_door(scenario, quanta)
    candidate = _candidate(view, quanta)

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
    assert evaluation.costs.explicit_cost == R(19, 4)
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
        view = _sell_door(scenario, {exact_decision_id("buy_quantum", "route:buy:b"): 3, exact_decision_id("sell_quantum", "route:sell:a"): 2})
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
    sell_id = exact_decision_id("sell_quantum", "route:sell:a")
    view = _sell_door(scenario, {exact_decision_id("buy_quantum", "route:buy:b"): 3, sell_id: 8})
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
    view = _sell_door(scenario, {})
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
    # The door freezes the sell at the base (zero), so the candidate is also not frozen: both contract codes, no replay.
    _assert_invalid_candidate_has_no_replay(
        evaluation,
        ("CANDIDATE_DECISION_NOT_FROZEN", "CANDIDATE_DECISION_OUT_OF_BOUNDS"),
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
    quanta = {
        exact_decision_id("buy_quantum", "route:buy:b"): 4,
        exact_decision_id("sell_quantum", "route:sell:a"): first_quanta,
        exact_decision_id("sell_quantum", "route:sell:a:second"): second_quanta,
    }
    view = _sell_door(scenario, quanta)

    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta))
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
    quanta = {exact_decision_id("buy_quantum", "route:buy:a"): 1, exact_decision_id("sell_quantum", "route:sell:a"): 1}
    view = _sell_door(scenario, quanta)

    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta))

    assert evaluation.candidate_valid is True
    assert "NO_ASSET_BUY_AND_SELL" in evaluation.conflict_codes
    assert evaluation.feasible is False


@pytest.mark.parametrize(
    ("minimum", "cap", "quanta", "expected_code"),
    [
        pytest.param(
            R(2),
            R(10),
            1,
            "ORDER_MIN_IF_ACTIVE",
            id="minimum-if-active",
        ),
        pytest.param(
            ZERO,
            R(3),
            3,
            None,
            id="cap-boundary",
        ),
    ],
)
def test_order_minimum_and_cap_contracts(
    minimum: ExactRatio,
    cap: ExactRatio,
    quanta: int,
    expected_code: str | None,
) -> None:
    scenario = _pac_scenario(
        minimum=minimum,
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
        assert "ORDER_CAP" not in evaluation.conflict_codes
    else:
        assert expected_code in evaluation.conflict_codes


@pytest.mark.parametrize(
    ("minimum", "constraint_code"),
    [
        pytest.param(
            R(2),
            "ORDER_MIN_IF_ACTIVE",
            id="minimum-if-active",
        ),
    ],
)
def test_monetary_sell_enforces_native_minimums(
    minimum: ExactRatio,
    constraint_code: str,
) -> None:
    scenario = _invest_and_sell_scenario(
        monetary_sell=True,
        sell_minimum=minimum,
    )
    quanta = {exact_decision_id("buy_quantum", "route:buy:b"): 3, exact_decision_id("sell_quantum", "route:sell:a"): 1}
    view = _sell_door(scenario, quanta)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta))
    constraint = _by_id(
        evaluation.constraints,
        "ref_id",
        f"constraint:{constraint_code.lower()}:route:sell:a",
    )

    assert constraint.value == ONE
    assert constraint.lower_bound == minimum
    assert constraint.satisfied is False
    assert constraint_code in evaluation.conflict_codes


def test_active_sell_requires_strictly_positive_posted_net() -> None:
    scenario = _invest_and_sell_scenario(
        sell_fixed=R(10),
    )
    quanta = {exact_decision_id("buy_quantum", "route:buy:b"): 3, exact_decision_id("sell_quantum", "route:sell:a"): 1}
    view = _sell_door(scenario, quanta)

    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta))
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
    # source_reachability now floors an overcommitted (negative) remaining
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
    fx_debit_id = fx_id(scenario, source="EUR", destination="USD")
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


def test_a_sell_keeps_fixed_reference_and_reconciles_u_identity() -> None:
    scenario = _invest_and_sell_scenario()
    buy_only = {exact_decision_id("buy_quantum", "route:buy:b"): 2}
    baseline = _sell_door(scenario, buy_only)
    baseline_result = evaluate_exact_candidate(scenario, baseline, _candidate(baseline, buy_only))
    with_sell = {exact_decision_id("buy_quantum", "route:buy:b"): 4, exact_decision_id("sell_quantum", "route:sell:a"): 2}
    extension = _sell_door(scenario, with_sell)
    extension_result = evaluate_exact_candidate(scenario, extension, _candidate(extension, with_sell))

    assert baseline_result.accounting is not None
    assert extension_result.accounting is not None
    assert baseline_result.accounting.fixed_reference == R(120)
    assert extension_result.accounting.fixed_reference == R(120)
    assert extension_result.accounting.final_invested == R(120)
    assert extension_result.accounting.shortfall == ZERO
    assert extension_result.accounting.identity_delta == ZERO
    assert extension_result.accounting.shortfall == (extension_result.accounting.free_cash + extension_result.accounting.physical_reserves + extension_result.accounting.economic_losses + extension_result.accounting.rounding_adjustment)


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
        # One score (B1 of project 67): F = 120, targets 60 and 60, final A 80 and B 40, nothing lost, so
        # D = 20² + 20² = 800 and J = 800 / 120 at «Balanced». Then the tie-breaks: a deposit and an order, every
        # route at priority zero.
        expected_codes = ("plan_score", "operation_count", "route_priority")
        expected_values = {"plan_score": R(20, 3), "operation_count": R(2), "route_priority": ZERO}
    else:
        scenario = _invest_and_sell_scenario()
        contribution_quanta = _integer_quanta(_by_id(scenario.contributions, "contribution_id", "contribution:a").amount.amount)
        if case == "invest-and-sell":
            # ``primary`` serves invest_and_sell with its sells disabled (B1-1); the sells reach a replay through the door.
            view = build_exact_policy_view(scenario)
            evaluation = evaluate_exact_candidate(
                scenario,
                view,
                _candidate(view, {exact_decision_id("funding_transfer", "route:funding"): contribution_quanta, exact_decision_id("buy_quantum", "route:buy:b"): 2}),
            )
            # The same score with the sells disabled: the same plan as invest-only, J = 800 / 120; the deposit has
            # priority 1 and the route of B priority 3.
            expected_codes = ("plan_score", "operation_count", "route_priority")
            expected_values = {"plan_score": R(20, 3), "operation_count": R(2), "route_priority": R(4)}
        elif case == "deployment":
            view = _sell_door(scenario, {exact_decision_id("buy_quantum", "route:buy:b"): 4, exact_decision_id("sell_quantum", "route:sell:a"): 2})
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


def test_shortfall_objective_carries_the_ceiling_rounding_cost() -> None:
    # One unit of 100.004 is a buy debit posted at its ceiling, 100.01: the 0.006
    # the rounding costs is the shortfall, inside the one-cent band.
    scenario = _pac_scenario(
        price=ONE,
        capability_kind="monetary_amount",
        step=R(25_001, 250),
        cash=R(10_001, 100),
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
    assert evaluation.accounting.fixed_reference == R(10_001, 100)
    assert evaluation.accounting.final_invested == R(25_001, 250)
    assert evaluation.accounting.shortfall == R(3, 500)
    assert evaluation.accounting.rounding_adjustment == R(3, 500)
    assert evaluation.accounting.rounding_bound == CENT
    assert evaluation.accounting.identity_delta == ZERO
    assert _objective_map(view, evaluation)["shortfall"] == R(3, 500)


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
        pytest.param("build_constraint_refs", id="constraint-ref-loop"),
        # NOTE: a "source-reachability-loop" case (target=source_reachability)
        # existed before this redesign. It is removed here, not merely
        # reference-repaired: source_reachability and its _can_reach_buy
        # callee (evaluation/reachability.py) contain no internal check_budget
        # call, so cancellation can never be observed mid-function there no
        # matter how the scenario is shaped -- check_budget is only called by
        # _evaluate_funding's outer loops, before/after (never during) each
        # source_reachability call. This is a possible production gap
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

    if target == "build_constraint_refs":

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
                    fx_id(scenario, source="EUR", destination="USD"): 100,
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


# Rounding top-ups (commit 5, QX1-b). The Decimal replay stays authoritative,
# every rounded posting against the plan (credits at their floor, debits at
# their ceiling), but a candidate whose ONLY violation is negative final
# spendable cash per pool (broker x currency), each pool short by
# D <= N x minor unit -- N = the pool's postings that carry a quantum: the buy
# debit of every order, a nonzero fee, the FX credit -- is published with one
# top-up per negative pool. Anything else is ``ExactReplayRejectedError``.
# The classifier and its dataclass are reached through the module objects
# (``EV``, ``pac_models``) so this suite still collects before they exist.
# Every case first asserts the evaluation facts it relies on (conflict codes,
# the pool's final cash, its rounded-posting count), so a red names its layer.

_TOP_UP_TOLERATED_CODES = frozenset(
    {
        "FX_SOURCE_CASH",
        "NO_SHORT_OR_LEVERAGE",
        "ROUNDING_BOUND",
        "SPENDABLE_CASH_NONNEGATIVE",
    }
)
_CASH_ONLY_CODES = ("NO_SHORT_OR_LEVERAGE", "SPENDABLE_CASH_NONNEGATIVE")
_TIE_PRICE = R(33335, 1000)  # 3 x 33.335 = 100.005, a buy debit posted at its ceiling, 100.01
_BUY_A = exact_decision_id("buy_quantum", "route:buy:a")
_BUY_B = exact_decision_id("buy_quantum", "route:buy:b")
_FUND_EUR = exact_decision_id("funding_transfer", "route:funding:eur")
_FX_EUR_TO_USD = fx_id(_funding_fx_scenario(), source="EUR", destination="USD")
_BUY_USD = exact_decision_id("buy_quantum", "route:buy:usd")


def _replay(
    scenario: ExactPlannerScenario,
    values: dict[str, int],
    *,
    view_id: str | None = None,
) -> tuple[ExactPolicyView, ExactEvaluation]:
    """The primary view and the exact replay of a hand-built candidate on it."""
    view = build_exact_policy_view(scenario, purpose="primary")
    return view, evaluate_exact_candidate(
        scenario,
        view,
        _candidate(view, values, view_id=view_id),
    )


def _pool_ledger(evaluation: ExactEvaluation, broker_id: str, currency: str = "EUR") -> ExactBrokerLedgerEvaluation:
    matches = tuple(row for row in evaluation.ledgers if (row.broker_id, row.currency) == (broker_id, currency))
    assert len(matches) == 1, f"expected one ({broker_id}, {currency}) ledger, found {[(row.broker_id, row.currency) for row in evaluation.ledgers]}"
    return matches[0]


def _pool_rounded_families(evaluation: ExactEvaluation, broker_id: str, currency: str = "EUR") -> list[str]:
    """The families of the pool's postings that carry a quantum: N is their count."""
    return sorted(posting.family for posting in evaluation.postings if (posting.broker_id, posting.currency) == (broker_id, currency) and posting.quantum is not None)


def _top_up(
    broker_id: str,
    amount: ExactRatio,
    rounded_postings: int,
    *,
    currency: str = "EUR",
    valuation_amount: ExactRatio | None = None,
) -> pac_models.ExactRoundingTopUp:
    return pac_models.ExactRoundingTopUp(
        broker_id=broker_id,
        currency=currency,
        amount=amount,
        rounded_postings=rounded_postings,
        valuation_amount=amount if valuation_amount is None else valuation_amount,
    )


def _eur_tie() -> tuple[ExactPlannerScenario, ExactPolicyView, ExactEvaluation]:
    """The EUR tie: 3 units at 33.335 against exactly EUR 100.00 end one cent short."""
    scenario = _pac_scenario(price=_TIE_PRICE, cash=R(100))
    view, evaluation = _replay(scenario, {_BUY_A: 3})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    assert _pool_ledger(evaluation, "broker:a").final_spendable == -CENT
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit"]
    return scenario, view, evaluation


def test_rounding_top_ups_of_a_feasible_replay_are_empty() -> None:
    """A replay that already balances announces nothing: the classifier answers ``()``.

    2 x 33.336 = 66.672 posts its ceiling 66.68 against EUR 100: every rule
    holds, so the plan is published exactly as before commit 5, with no top-up
    to show.
    """
    scenario = _pac_scenario(price=R(33336, 1000), cash=R(100))
    _, evaluation = _replay(scenario, {_BUY_A: 2})
    assert evaluation.feasible is True, evaluation.conflict_codes

    assert EV.rounding_top_ups(scenario, evaluation) == ()


def test_rounding_top_up_covers_a_one_cent_ceiling_deficit() -> None:
    """The EUR tie is published with a top-up of exactly the missing cent.

    100.005 posts its ceiling 100.01, so the pool ends at -0.01. Its one
    quantum-carrying posting is the buy debit (the initial cash carries none, a
    zero fee is not posted): D = 0.01 <= 1 x 0.01. Only the cash rules fail;
    ``ROUNDING_BOUND`` holds (shortfall -0.005 inside the 0.01 band). The pool is
    in the valuation currency, so the top-up is valued at its own amount.
    """
    scenario, _, evaluation = _eur_tie()
    assert "ROUNDING_BOUND" not in evaluation.conflict_codes
    assert (evaluation.accounting.shortfall, evaluation.accounting.rounding_bound) == (-R(1, 200), CENT)

    assert EV.rounding_top_ups(scenario, evaluation) == (_top_up("broker:a", CENT, 1),)


def test_rounding_top_up_counts_a_posted_fee_as_a_second_rounded_posting() -> None:
    """A nonzero fee is posted with its own quantum: N = 2 tolerates two cents.

    The EUR 0.01 fixed fee joins the buy debit, so 100.01 + 0.01 against EUR
    100.00 leaves -0.02 = 2 x 0.01: accepted, and the top-up reports the two
    postings the deficit spreads over.
    """
    scenario = _pac_scenario(price=_TIE_PRICE, cash=R(100), fixed_fee=CENT)
    _, evaluation = _replay(scenario, {_BUY_A: 3})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    assert _pool_ledger(evaluation, "broker:a").final_spendable == -R(2, 100)
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit", "buy_fee"]

    assert EV.rounding_top_ups(scenario, evaluation) == (_top_up("broker:a", R(2, 100), 2),)


def test_rounding_top_up_rejects_three_cents_over_two_rounded_postings() -> None:
    """One cent past N x minor unit is no longer rounding: the replay rejects.

    A EUR 0.02 fee leaves -0.03 over the same two postings: D = 0.03 > 2 x 0.01.
    (Cash 99.99 with the 0.01 fee is not a usable variant: the view bounds the
    route at 2 units there, so 3 units would be out of bounds, not short.)
    """
    scenario = _pac_scenario(price=_TIE_PRICE, cash=R(100), fixed_fee=R(2, 100))
    _, evaluation = _replay(scenario, {_BUY_A: 3})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    assert _pool_ledger(evaluation, "broker:a").final_spendable == -R(3, 100)
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit", "buy_fee"]

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, evaluation)


def test_rounding_top_up_rejects_a_unit_the_cash_cannot_pay() -> None:
    """A unit the cash cannot pay leaves a real deficit, far beyond rounding.

    EUR 10 buys the EUR 10 unit but not its EUR 1 fixed fee: the pool ends EUR 1
    short over two rounded postings, fifty times N x minor unit. (The view bounds
    whole units by cash / price, so "one unit more" of the tie is out of bounds;
    the fee is what makes an in-bounds unit unaffordable.)
    """
    scenario = _pac_scenario(cash=R(10), fixed_fee=ONE)
    _, evaluation = _replay(scenario, {_BUY_A: 1})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    assert _pool_ledger(evaluation, "broker:a").final_spendable == -ONE
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit", "buy_fee"]

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, evaluation)


def test_rounding_top_up_does_not_excuse_another_violation() -> None:
    """A deficit within the threshold never excuses a rule a top-up cannot repair.

    The EUR tie again (-0.01, N = 1), on a route that requires 4 units once
    active: ``ORDER_MIN_IF_ACTIVE`` fails next to the cash rules. (A route cap
    below 3 units would make the candidate out of bounds instead: a contract
    failure, covered by the invalid-candidate case.)
    """
    scenario = _pac_scenario(price=_TIE_PRICE, cash=R(100), minimum=R(4))
    _, evaluation = _replay(scenario, {_BUY_A: 3})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == ("NO_SHORT_OR_LEVERAGE", "ORDER_MIN_IF_ACTIVE", "SPENDABLE_CASH_NONNEGATIVE")
    assert _pool_ledger(evaluation, "broker:a").final_spendable == -CENT
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit"]

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, evaluation)


def _two_pool_scenario(cash_a: ExactRatio, cash_b: ExactRatio) -> ExactPlannerScenario:
    """The tie Asset bought on two brokers, each paying from its own EUR pool."""
    capability_a = _capability("capability:a")
    capability_b = _capability("capability:b")
    fee_a = _fee("fee:buy:a", capability_a.capability_id, "buy")
    fee_b = _fee("fee:buy:b", capability_b.capability_id, "buy")
    return _scenario(
        "scenario:two-pools",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=_TIE_PRICE),),
        brokers=(
            _broker("broker:a", (capability_a,), (fee_a,)),
            _broker("broker:b", (capability_b,), (fee_b,)),
        ),
        existing_cash=(
            _cash("cash:a", "broker:a", cash_a),
            _cash("cash:b", "broker:b", cash_b),
        ),
        order_routes=(
            _order_route(
                "route:buy:a",
                broker_id="broker:a",
                asset_id="asset:a",
                capability=capability_a,
                fee_id=fee_a.fee_schedule_id,
                side="buy",
            ),
            _order_route(
                "route:buy:b",
                broker_id="broker:b",
                asset_id="asset:a",
                capability=capability_b,
                fee_id=fee_b.fee_schedule_id,
                side="buy",
            ),
        ),
    )


def test_rounding_top_ups_are_one_per_negative_pool_in_ledger_order() -> None:
    """Two pools one cent short each get two top-ups, in the evaluation's ledger order.

    The threshold is per pool: each pool carries its own buy debit (N = 1) and
    its own -0.01, and the top-up tells the user which broker needs the cent.
    """
    scenario = _two_pool_scenario(R(100), R(100))
    _, evaluation = _replay(scenario, {_BUY_A: 3, _BUY_B: 3})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    negative_pools = [(row.broker_id, row.currency) for row in evaluation.ledgers if row.final_spendable < ZERO]
    assert negative_pools == [("broker:a", "EUR"), ("broker:b", "EUR")]
    for broker_id, _ in negative_pools:
        assert _pool_ledger(evaluation, broker_id).final_spendable == -CENT
        assert _pool_rounded_families(evaluation, broker_id) == ["buy_debit"]

    assert EV.rounding_top_ups(scenario, evaluation) == (
        _top_up("broker:a", CENT, 1),
        _top_up("broker:b", CENT, 1),
    )


def test_rounding_top_up_threshold_is_per_pool_not_summed() -> None:
    """Spare threshold on one pool never covers another pool's deficit.

    Pool A buys 2 units and ends positive with one rounded posting; pool B buys
    3 units on EUR 99.99 and ends at -0.02 with one rounded posting. A summed
    rule would accept (0.02 <= 2 x 0.01); per pool, B's 0.02 > 1 x 0.01 rejects.
    """
    scenario = _two_pool_scenario(R(100), R(9999, 100))
    _, evaluation = _replay(scenario, {_BUY_A: 2, _BUY_B: 3})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    assert _pool_ledger(evaluation, "broker:a").final_spendable == R(3333, 100)
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit"]
    assert _pool_ledger(evaluation, "broker:b").final_spendable == -R(2, 100)
    assert _pool_rounded_families(evaluation, "broker:b") == ["buy_debit"]

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, evaluation)


def _funding_fx_evaluation(fx_debit_cents: int) -> tuple[ExactPlannerScenario, ExactEvaluation]:
    """Fund EUR 150 to the destination, convert ``fx_debit_cents`` to USD, buy one USD 100 unit."""
    scenario = _funding_fx_scenario()
    _, evaluation = _replay(
        scenario,
        {_FUND_EUR: 15_000, _FX_EUR_TO_USD: fx_debit_cents, _BUY_USD: 1},
    )
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    # N counts the floored FX credit next to the buy debit; the funding transfer
    # and the FX debit carry no quantum on this scenario (read off the postings).
    assert _pool_rounded_families(evaluation, "broker:destination", "USD") == ["buy_debit", "fx_credit"]
    return scenario, evaluation


def test_rounding_top_up_counts_the_fx_credit_and_values_the_deficit_in_eur() -> None:
    """The FX credit is a rounded posting, and the top-up is valued in EUR.

    EUR 84.16 converted with the spread credits a USD amount, posted at its
    floor, that leaves the USD pool at -0.02 after the USD 100 unit: two rounded postings
    (FX credit + buy debit), so D = 0.02 <= 2 x 0.01 is accepted. The valuation
    uses the evaluator's own conversion, pinned first against its free cash:
    every final pool converted at the scenario's EUR/USD rate.
    """
    scenario, evaluation = _funding_fx_evaluation(8416)
    usd_final = _pool_ledger(evaluation, "broker:destination", "USD").final_spendable
    assert usd_final == -R(2, 100)
    (rate,) = scenario.fx_rates
    assert (rate.pair_first, rate.pair_second, scenario.valuation_currency) == ("EUR", "USD", "EUR")
    eur_finals = sum((row.final_spendable for row in evaluation.ledgers if row.currency == "EUR"), ZERO)
    assert evaluation.accounting.free_cash == eur_finals + usd_final / rate.rate

    assert EV.rounding_top_ups(scenario, evaluation) == (
        _top_up(
            "broker:destination",
            R(2, 100),
            2,
            currency="USD",
            valuation_amount=R(2, 100) / rate.rate,
        ),
    )


def test_rounding_top_up_rejects_three_cents_over_the_fx_pool_two_postings() -> None:
    """One more cent of FX debit short leaves -0.03 over two rounded postings: rejected."""
    scenario, evaluation = _funding_fx_evaluation(8415)
    assert _pool_ledger(evaluation, "broker:destination", "USD").final_spendable == -R(3, 100)

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, evaluation)


def test_rounding_top_ups_reject_a_contract_invalid_candidate() -> None:
    """A candidate built for another view is not a plan at all: nothing to top up."""
    scenario = _pac_scenario(price=_TIE_PRICE, cash=R(100))
    _, evaluation = _replay(scenario, {_BUY_A: 3}, view_id="other")
    assert evaluation.candidate_valid is False
    assert evaluation.conflict_codes == ("CANDIDATE_VIEW_MISMATCH",)

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, evaluation)


def test_rounding_top_up_covers_an_unrounded_one_cent_deficit_inside_the_band() -> None:
    """A deficit nothing rounded is still published when one cent per posting covers it.

    Four EUR 25 units cost exactly EUR 100.00 (nothing rounds; the buy debit
    still carries its quantum) against EUR 99.99: the pool and the shortfall end
    at -0.01, on the edge of the one-cent band, so ``ROUNDING_BOUND`` holds and
    only the cash rules fail. D = 0.01 <= 1 x 0.01: the top-up is the missing cent.
    """
    scenario = _pac_scenario(price=R(25), cash=R(9999, 100))
    _, evaluation = _replay(scenario, {_BUY_A: 4})
    assert evaluation.candidate_valid is True
    assert evaluation.conflict_codes == _CASH_ONLY_CODES
    assert _pool_ledger(evaluation, "broker:a").final_spendable == -CENT
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit"]
    accounting = evaluation.accounting
    assert (accounting.shortfall, accounting.rounding_adjustment, accounting.rounding_bound) == (-CENT, ZERO, CENT)

    assert EV.rounding_top_ups(scenario, evaluation) == (_top_up("broker:a", CENT, 1),)


def test_rounding_top_up_accepts_a_failed_rounding_bound_the_top_up_explains() -> None:
    """``ROUNDING_BOUND`` may fail when the top-up is exactly what it lacks.

    Fabricated on the same EUR 100.00 cost against EUR 99.99: the bound drops to
    0.005 and ``ROUNDING_BOUND`` fails next to the cash rules, the -0.01
    shortfall being beyond it. The rounding adjustment is 0 (within the bound)
    and shortfall + top-up valuation = 0 >= -bound: the classifier accepts the
    one-cent top-up, where an adjustment beyond the bound is rejected (below).
    """
    scenario = _pac_scenario(price=R(25), cash=R(9999, 100))
    view, evaluation = _replay(scenario, {_BUY_A: 4})
    assert evaluation.candidate_valid is True
    assert _pool_ledger(evaluation, "broker:a").final_spendable == -CENT
    assert _pool_rounded_families(evaluation, "broker:a") == ["buy_debit"]
    (ref,) = (row for row in view.constraints if row.code == "ROUNDING_BOUND")
    conflicts = tuple(
        sorted(
            {*evaluation.conflicts, ExactConflict(code=ref.code, entity_refs=ref.entity_refs)},
            key=lambda item: (item.code, tuple((entity.kind, entity.entity_id) for entity in item.entity_refs)),
        )
    )
    fabricated = replace(
        evaluation,
        conflicts=conflicts,
        conflict_codes=tuple(sorted({item.code for item in conflicts})),
        constraints=tuple(replace(row, satisfied=False, upper_bound=R(1, 200)) if row.ref_id == ref.ref_id else row for row in evaluation.constraints),
        accounting=replace(evaluation.accounting, rounding_bound=R(1, 200)),
    )
    accounting = fabricated.accounting
    assert fabricated.conflict_codes == ("NO_SHORT_OR_LEVERAGE", "ROUNDING_BOUND", "SPENDABLE_CASH_NONNEGATIVE")
    assert (accounting.shortfall, accounting.rounding_adjustment, accounting.rounding_bound) == (-CENT, ZERO, R(1, 200))
    assert accounting.shortfall < -accounting.rounding_bound
    assert accounting.shortfall + CENT >= -accounting.rounding_bound

    assert EV.rounding_top_ups(scenario, fabricated) == (_top_up("broker:a", CENT, 1),)


def test_rounding_top_ups_reject_a_negative_holding() -> None:
    """A short position is never a rounding artefact, whatever the conflict codes say.

    Fabricated on the EUR tie: the holding sells one unit it never had. The
    conflict codes stay the tolerated cash pair (``NO_SHORT_OR_LEVERAGE`` is
    already there), so only the classifier's own holding guard can reject it.
    """
    scenario, _, evaluation = _eur_tie()
    (holding,) = evaluation.holdings
    assert holding.initial_quantity == ZERO
    short = replace(evaluation, holdings=(replace(holding, buy_quantity=ZERO, sell_quantity=ONE, final_quantity=-ONE),))
    assert short.conflict_codes == _CASH_ONLY_CODES

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, short)


def test_rounding_top_ups_reject_a_rounding_adjustment_beyond_its_bound() -> None:
    """A failed ``ROUNDING_BOUND`` is accepted only while the adjustment is within it.

    Fabricated on the EUR tie: the bound drops to 0 and ``ROUNDING_BOUND`` fails,
    while the 0.005 rounding adjustment stays. Shortfall + top-up valuation is
    still >= -bound, so the rejection is attributable to |adjustment| > bound.
    """
    scenario, view, evaluation = _eur_tie()
    (ref,) = (row for row in view.constraints if row.code == "ROUNDING_BOUND")
    conflicts = tuple(
        sorted(
            {*evaluation.conflicts, ExactConflict(code=ref.code, entity_refs=ref.entity_refs)},
            key=lambda item: (item.code, tuple((entity.kind, entity.entity_id) for entity in item.entity_refs)),
        )
    )
    fabricated = replace(
        evaluation,
        conflicts=conflicts,
        conflict_codes=tuple(sorted({item.code for item in conflicts})),
        constraints=tuple(replace(row, satisfied=False, upper_bound=ZERO) if row.ref_id == ref.ref_id else row for row in evaluation.constraints),
        accounting=replace(evaluation.accounting, rounding_bound=ZERO),
    )
    accounting = fabricated.accounting
    assert fabricated.conflict_codes == ("NO_SHORT_OR_LEVERAGE", "ROUNDING_BOUND", "SPENDABLE_CASH_NONNEGATIVE")
    assert abs(accounting.rounding_adjustment) > accounting.rounding_bound
    assert accounting.shortfall + CENT >= -accounting.rounding_bound

    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, fabricated)


_VALID_TOP_UP = {
    "broker_id": "broker:a",
    "currency": "EUR",
    "amount": CENT,
    "rounded_postings": 1,
    "valuation_amount": CENT,
}


@pytest.mark.parametrize(
    "override",
    [
        pytest.param({"amount": ZERO}, id="zero-amount"),
        pytest.param({"amount": -CENT}, id="negative-amount"),
        pytest.param({"valuation_amount": ZERO}, id="zero-valuation"),
        pytest.param({"valuation_amount": -CENT}, id="negative-valuation"),
        pytest.param({"rounded_postings": 0}, id="no-rounded-posting"),
        pytest.param({"rounded_postings": True}, id="bool-rounded-postings"),
    ],
)
def test_exact_rounding_top_up_rejects_an_impossible_top_up(override: dict[str, Any]) -> None:
    """A top-up is a positive amount, positively valued, over at least one posting."""
    assert pac_models.ExactRoundingTopUp(**_VALID_TOP_UP).rounded_postings == 1

    with pytest.raises(ValueError):
        pac_models.ExactRoundingTopUp(**{**_VALID_TOP_UP, **override})


# ---------------------------------------------------------------------------
# A2 (project 67): which FX decisions exist is one list, ``reachability.fx_decision_specs``
# ---------------------------------------------------------------------------

_FX_CONSTRAINT_CODES = frozenset({"FX_DEBIT_CREDIT_COUPLED", "FX_CREDIT_POSITIVE", "FX_NATIVE_QUANTUM", "FX_SOURCE_CASH"})


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(_funding_fx_scenario, id="one-buy-one-pool"),
        pytest.param(_multi_source_buy_scenario, id="two-buys-share-a-pool"),
        pytest.param(lambda: _two_pool_scenario(R(10), R(10)), id="no-fx-at-all"),
    ],
)
def test_fx_decisions_come_from_one_list_shared_by_view_and_replay(build) -> None:
    """Step 1: the view's ``fx_debit`` decisions, the FX constraint refs and the FX evaluations of the replay all name the
    entries of one list, and only them: no consumer derives an FX decision on its own."""
    scenario = build()
    specs = fx_decision_specs(scenario, build_scenario_index(scenario), None)
    view = build_exact_policy_view(scenario)

    assert len({spec.decision_id for spec in specs}) == len(specs)
    assert sorted(spec.decision_id for spec in specs) == sorted(item.decision_id for item in view.decisions if item.family == "fx_debit")
    fx_refs = [ref for ref in view.constraints if ref.code in _FX_CONSTRAINT_CODES]
    assert {ref.ref_id for ref in fx_refs} == {f"constraint:{code.lower()}:{spec.key}" for spec in specs for code in _FX_CONSTRAINT_CODES}
    assert all(ref.scope == next(spec.scope for spec in specs if ref.ref_id.endswith(f":{spec.key}")) for ref in fx_refs)

    one_quantum_each = _candidate(view, {spec.decision_id: 1 for spec in specs})
    evaluation = evaluate_exact_candidate(scenario, view, one_quantum_each)
    assert {action.decision_id for action in evaluation.fx} <= {spec.decision_id for spec in specs}


# ---------------------------------------------------------------------------
# A2 step 7 (project 67): one FX decision per Broker and ordered currency pair
# ---------------------------------------------------------------------------


def _shared_pair_scenario(*, cap: ExactRatio = R(2)) -> ExactPlannerScenario:
    """N1 in small: one Broker holding EUR, two USD Assets on two buy routes, so both routes need the one EUR to USD pair.

    Whole-unit quanta make the floor of a credit visible: at 5/4 USD per EUR with a 10% spread, 4 EUR credit an exact 4.5 USD.
    """
    capability = _capability("capability:whole")
    usd_fee = _fee("fee:buy:usd", capability.capability_id, "buy", currency="USD")
    broker = _broker("broker:hub", (capability,), (usd_fee,))

    def buy(route_id: str, asset_id: str) -> ExactOrderRoute:
        return _order_route(route_id, broker_id=broker.broker_id, asset_id=asset_id, capability=capability, fee_id=usd_fee.fee_schedule_id, side="buy", cap=cap)

    return _scenario(
        "scenario:shared-pair",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(5), currency="USD"), _asset("asset:b", price=R(10), currency="USD")),
        brokers=(broker,),
        existing_cash=(_cash("cash:hub", broker.broker_id, R(20)),),
        order_routes=(buy("route:buy:a", "asset:a"), buy("route:buy:b", "asset:b")),
        fx_rates=(_fx_rate("EUR", "USD", R(5, 4)),),
        fx_spread_rate=R(1, 10),
        currency_quantums=(("EUR", ONE), ("USD", ONE)),
    )


def _reverse_order_pairs_scenario() -> ExactPlannerScenario:
    """Two Brokers, each converting EUR to USD; route ids sort broker b's route first, the canonical order puts broker a first."""
    capability = _capability("capability:whole")
    usd_fee = _fee("fee:buy:usd", capability.capability_id, "buy", currency="USD")
    brokers = (_broker("broker:a", (capability,), (usd_fee,)), _broker("broker:b", (capability,), (usd_fee,)))
    return _scenario(
        "scenario:reverse-order-pairs",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(5), currency="USD"),),
        brokers=brokers,
        existing_cash=(_cash("cash:a", "broker:a", R(20)), _cash("cash:b", "broker:b", R(20))),
        order_routes=(
            _order_route("route:1", broker_id="broker:b", asset_id="asset:a", capability=capability, fee_id=usd_fee.fee_schedule_id, side="buy", cap=R(2)),
            _order_route("route:2", broker_id="broker:a", asset_id="asset:a", capability=capability, fee_id=usd_fee.fee_schedule_id, side="buy", cap=R(2)),
        ),
        fx_rates=(_fx_rate("EUR", "USD", R(5, 4)),),
        currency_quantums=(("EUR", ONE), ("USD", ONE)),
    )


def test_fx_decisions_are_one_per_broker_and_ordered_pair() -> None:
    """Two buy routes on one pair share one decision; a Broker with two source currencies has one decision per pair.

    The decision is keyed by Broker, source and destination (``len(broker):broker:SRC:DST``), scoped to the Broker, and names the
    first buy route of that Broker in the destination currency (canonical order) as the route the published action names until A4.
    """
    shared = fx_decision_specs(_shared_pair_scenario(), build_scenario_index(_shared_pair_scenario()), None)
    assert [(spec.broker_id, spec.source_currency, spec.destination_currency) for spec in shared] == [("broker:hub", "EUR", "USD")]
    (spec,) = shared
    assert spec.key == "10:broker:hub:EUR:USD"
    assert spec.decision_id == "fx:10:broker:hub:EUR:USD"
    assert spec.scope == "broker"
    assert {(ref.kind, ref.entity_id) for ref in spec.entity_refs} == {("broker", "broker:hub"), ("source_currency", "EUR"), ("destination_currency", "USD")}

    multi = _multi_source_buy_scenario()
    pairs = [(spec.broker_id, spec.source_currency, spec.destination_currency) for spec in fx_decision_specs(multi, build_scenario_index(multi), None)]
    assert pairs == [("broker:hub", "GBP", "EUR"), ("broker:hub", "USD", "EUR")]


def test_two_buys_on_one_pair_post_one_floored_credit() -> None:
    """The rule of 09/10, on one decision: a pair posts the floor of its whole credit, never less than the floors of its parts.

    8 EUR credit an exact 9 USD and post 9; split over the two routes as 4 + 4, each part would credit 4.5 and post 4, 8 in all.
    """
    scenario = _shared_pair_scenario()
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, {fx_id(scenario, source="EUR", destination="USD"): 8}))

    (action,) = evaluation.fx
    assert (action.source_debit, action.exact_destination_credit, action.posted_destination_credit) == (R(8), R(9), R(9))
    split_floors = 2 * post_floor(R(9, 2), ONE).posted
    assert action.posted_destination_credit >= split_floors == R(8)


def test_fx_evaluations_are_ordered_by_broker_source_destination() -> None:
    """The canonical order of the FX evaluations is (Broker, source, destination), whatever the order of the routes."""
    scenario = _reverse_order_pairs_scenario()
    view = build_exact_policy_view(scenario)
    values = {spec.decision_id: 4 for spec in fx_decision_specs(scenario, build_scenario_index(scenario), None)}
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, values))

    assert [(item.broker_id, item.source_currency, item.destination_currency) for item in evaluation.fx] == [("broker:a", "EUR", "USD"), ("broker:b", "EUR", "USD")]


# ---------------------------------------------------------------------------
# A2 steps 9-11 (project 67): the transfer family between Brokers, at the exact level
# ---------------------------------------------------------------------------


def _transfer_lane_scenario(*, quantum: ExactRatio = CENT) -> ExactPlannerScenario:
    """A PAC scenario with one transfer lane set by hand (D4 a: the normalizer never sets one in the PAC).

    broker:a holds EUR100 and can buy the Asset (EUR10 a unit) at most 3 times, so its cash is reachable and the reference is
    EUR100; broker:b holds nothing and can buy it at most 10 times. Reaching the target takes moving cash from a to b.
    ``quantum`` is EUR's minor unit: a whole euro keeps the transfer's domain small enough for the exhaustive oracle. The lane
    is added by ``_with_lane``.
    """
    capability_a = _capability("capability:a")
    capability_b = _capability("capability:b")
    fee_a = _fee("fee:buy:a", capability_a.capability_id, "buy")
    fee_b = _fee("fee:buy:b", capability_b.capability_id, "buy")
    return _scenario(
        "scenario:transfer-lane",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(10)),),
        brokers=(_broker("broker:a", (capability_a,), (fee_a,)), _broker("broker:b", (capability_b,), (fee_b,))),
        existing_cash=(_cash("cash:a", "broker:a", R(100)),),
        order_routes=(
            _order_route("route:buy:a", broker_id="broker:a", asset_id="asset:a", capability=capability_a, fee_id=fee_a.fee_schedule_id, side="buy", cap=R(3)),
            _order_route("route:buy:b", broker_id="broker:b", asset_id="asset:a", capability=capability_b, fee_id=fee_b.fee_schedule_id, side="buy", cap=R(10)),
        ),
        currency_quantums=(("EUR", quantum),),
    )


def _with_lane(scenario: ExactPlannerScenario, source: str, destination: str) -> ExactPlannerScenario:
    return replace(scenario, transfer_lanes=(pac_models.ExactTransferLane(source_broker_id=source, destination_broker_id=destination, currency="EUR"),))


def test_broker_transfer_posts_exact_in_and_out_and_keeps_the_total() -> None:
    """Property P4: moving money between Brokers is free and keeps the total. One decision per lane, quantum the currency's
    minor unit; two exact postings (out of the source cell, into the destination cell), and the scenario's wealth unchanged."""
    scenario = _with_lane(_transfer_lane_scenario(), "broker:a", "broker:b")
    view = build_exact_policy_view(scenario)
    (transfer,) = [access for access in view.decisions if access.family == "broker_transfer"]
    assert {(item.kind, item.entity_id) for item in transfer.entity_refs} == {("source_broker", "broker:a"), ("destination_broker", "broker:b"), ("currency", "EUR")}
    assert transfer.decision_id == "transfer:8:broker:a8:broker:b:EUR"

    idle = evaluate_exact_candidate(scenario, view, _candidate(view, {}))
    moved = evaluate_exact_candidate(scenario, view, _candidate(view, {transfer.decision_id: 4_000}))

    assert moved.feasible is True
    postings = {(item.family, item.broker_id, item.currency): item for item in moved.postings if item.family in {"transfer_in", "transfer_out"}}
    assert set(postings) == {("transfer_out", "broker:a", "EUR"), ("transfer_in", "broker:b", "EUR")}
    assert all(item.posted_amount == item.exact_amount == R(40) for item in postings.values())
    ledgers = {(row.broker_id, row.currency): row for row in moved.ledgers}
    assert (ledgers[("broker:a", "EUR")].transfer_out, ledgers[("broker:a", "EUR")].final_spendable) == (R(40), R(60))
    assert (ledgers[("broker:b", "EUR")].transfer_in, ledgers[("broker:b", "EUR")].final_spendable) == (R(40), R(40))
    total = sum((row.final_spendable for row in moved.ledgers), ZERO)
    assert total == sum((row.final_spendable for row in idle.ledgers), ZERO) == R(100)
    assert moved.accounting.identity_delta == idle.accounting.identity_delta == ZERO
    assert moved.accounting.fixed_reference == idle.accounting.fixed_reference


def test_a_transfer_lane_to_the_same_broker_is_refused() -> None:
    """A transfer moves money between two Brokers in one currency: a lane from a Broker to itself is not a scenario."""
    looping = _with_lane(_transfer_lane_scenario(), "broker:a", "broker:a")
    with pytest.raises(ExactScenarioContractError, match="same Broker"):
        build_exact_policy_view(looping)


# ---------------------------------------------------------------------------
# A2 step 13 (project 67): V7, one direction per Broker and currency pair (T6 in PAC form)
# ---------------------------------------------------------------------------


def _two_way_scenario() -> ExactPlannerScenario:
    """N2 in small: one Broker holding EUR4 and USD6, one EUR Asset and one USD Asset (4 each, at most 2 units).

    Both directions of EUR/USD exist at the Broker: EUR to USD for the USD buy, USD to EUR for the EUR buy. Whole-unit
    quanta keep the domains small enough for the exhaustive oracle.
    """
    capability = _capability("capability:whole")
    eur_fee = _fee("fee:buy:eur", capability.capability_id, "buy")
    usd_fee = _fee("fee:buy:usd", capability.capability_id, "buy", currency="USD")
    broker = _broker("broker:hub", (capability,), (eur_fee, usd_fee))

    def buy(route_id: str, asset_id: str, fee: ExactFeeSchedule) -> ExactOrderRoute:
        return _order_route(route_id, broker_id=broker.broker_id, asset_id=asset_id, capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(2))

    return _scenario(
        "scenario:two-way",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:eur", price=R(4), currency="EUR"), _asset("asset:usd", price=R(4), currency="USD")),
        brokers=(broker,),
        existing_cash=(_cash("cash:eur", broker.broker_id, R(4)), _cash("cash:usd", broker.broker_id, R(6), currency="USD")),
        order_routes=(buy("route:buy:eur", "asset:eur", eur_fee), buy("route:buy:usd", "asset:usd", usd_fee)),
        fx_rates=(_fx_rate("EUR", "USD", R(5, 4)),),
        fx_spread_rate=R(1, 100),
        currency_quantums=(("EUR", ONE), ("USD", ONE)),
    )


def test_both_directions_of_a_pair_fail_the_exact_replay() -> None:
    """V7 in the replay: converting EUR to USD and USD to EUR at one Broker in one plan is refused (one fact per Broker and
    pair that has both directions); either direction alone is not."""
    scenario = _two_way_scenario()
    view = build_exact_policy_view(scenario)
    to_usd = fx_id(scenario, source="EUR", destination="USD")
    to_eur = fx_id(scenario, source="USD", destination="EUR")
    fact_id = "constraint:fx_no_relay:10:broker:hub:EUR"

    both = evaluate_exact_candidate(scenario, view, _candidate(view, {to_usd: 1, to_eur: 2}))
    (fact,) = [item for item in both.constraints if item.ref_id == fact_id]
    assert (fact.satisfied, both.feasible) == (False, False)

    for one_way in ({to_usd: 1}, {to_eur: 2}, {}):
        evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, one_way))
        (fact,) = [item for item in evaluation.constraints if item.ref_id == fact_id]
        assert fact.satisfied is True, one_way
        assert evaluation.feasible is True, one_way


# ---------------------------------------------------------------------------
# A3 step 1 (project 67): entry limits (V5) in the exact scenario
# ---------------------------------------------------------------------------


def test_entry_limits_default_to_absent_and_a_scenario_carries_them() -> None:
    """Minimum and maximum of an Asset and of a cash cell are each absent, an amount (valuation currency) or a share of the
    reference (D10, M17). Absent by default: every scenario built before A3 keeps its meaning."""
    scenario = _two_pool_scenario(R(100), R(100))
    assert all((item.minimum, item.maximum) == (None, None) for item in scenario.target_weights)
    assert scenario.cash_entries == ()

    limited = replace(
        scenario,
        target_weights=(replace(scenario.target_weights[0], minimum=pac_models.ExactLimit("amount", R(10)), maximum=pac_models.ExactLimit("share", R(1, 2))),),
        cash_entries=(pac_models.ExactCashEntry(broker_id="broker:a", currency="EUR", minimum=None, maximum=pac_models.ExactLimit("amount", R(30))),),
    )
    assert limited.target_weights[0].maximum == pac_models.ExactLimit("share", R(1, 2))
    assert limited.cash_entries[0].maximum.value == R(30)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        pytest.param("amount", R(-1), id="negative-amount"),
        pytest.param("share", R(-1, 100), id="negative-share"),
        pytest.param("share", R(101, 100), id="share-above-one"),
        pytest.param("ratio", R(1, 2), id="unknown-kind"),
    ],
)
def test_an_entry_limit_refuses_a_negative_value_a_share_above_one_and_an_unknown_kind(kind: str, value: ExactRatio) -> None:
    with pytest.raises(ValueError):
        pac_models.ExactLimit(kind, value)


def test_a_cash_limit_names_a_known_broker_and_a_covered_currency_and_is_unique() -> None:
    scenario = _two_pool_scenario(R(100), R(100))
    limit = pac_models.ExactCashEntry(broker_id="broker:a", currency="EUR", minimum=None, maximum=pac_models.ExactLimit("amount", R(30)))

    build_exact_policy_view(replace(scenario, cash_entries=(limit,)))  # known broker and currency: builds
    with pytest.raises(ExactScenarioContractError, match="unknown Broker"):
        build_exact_policy_view(replace(scenario, cash_entries=(replace(limit, broker_id="broker:zzz"),)))
    with pytest.raises(ExactScenarioContractError, match="JPY"):
        build_exact_policy_view(replace(scenario, cash_entries=(replace(limit, currency="JPY"),)))
    with pytest.raises(ValueError, match="canonical sorted order|duplicate"):
        replace(scenario, cash_entries=(limit, limit))
    with pytest.raises(ValueError, match="needs a weight, a minimum or a maximum"):
        pac_models.ExactCashEntry(broker_id="broker:a", currency="EUR", minimum=None, maximum=None)


# ---------------------------------------------------------------------------
# A3 step 2 (project 67): the three checks before the calculation, pure, naming the entries (T12)
# ---------------------------------------------------------------------------

_LIMIT_A = pac_models.ExactLimit


def _limited_scenario(
    *,
    asset_a: tuple[pac_models.ExactLimit | None, pac_models.ExactLimit | None] = (None, None),
    asset_b: tuple[pac_models.ExactLimit | None, pac_models.ExactLimit | None] = (None, None),
    cash: tuple[pac_models.ExactCashEntry, ...] = (),
) -> ExactPlannerScenario:
    """Two Assets (50% each) bought at two Brokers holding EUR100 and EUR50: the reference of the plan is EUR150."""
    base = _two_pool_scenario(R(100), R(50))
    capability = _capability("capability:b2")
    fee = _fee("fee:buy:b2", capability.capability_id, "buy")
    broker_b = replace(base.brokers[1], capabilities=(*base.brokers[1].capabilities, capability), fee_schedules=(*base.brokers[1].fee_schedules, fee))
    second_asset = _asset("asset:b", price=R(10))
    route_b = _order_route("route:buy:asset-b", broker_id="broker:b", asset_id="asset:b", capability=capability, fee_id=fee.fee_schedule_id, side="buy")
    weights = (
        pac_models.ExactTargetWeight("asset:a", R(1, 2), minimum=asset_a[0], maximum=asset_a[1]),
        pac_models.ExactTargetWeight("asset:b", R(1, 2), minimum=asset_b[0], maximum=asset_b[1]),
    )
    return replace(
        base,
        assets=tuple(sorted((*base.assets, second_asset), key=lambda item: item.asset_id)),
        brokers=(base.brokers[0], broker_b),
        order_routes=tuple(sorted((*base.order_routes, route_b), key=lambda item: item.route_id)),
        target_weights=weights,
        cash_entries=cash,
    )


def test_sum_of_minimums_above_the_reference_names_the_entries() -> None:
    """T12: minimums of EUR100 and 60% of the reference (EUR90) add up to EUR190 > EUR150. The check names every entry with a
    minimum, the Assets and the cash cells alike, on the base of D7: ``fixed_reference``."""
    scenario = _limited_scenario(asset_a=(_LIMIT_A("amount", R(100)), None), asset_b=(_LIMIT_A("share", R(3, 5)), None))
    reference = fixed_reference_of(scenario)
    assert reference == R(150)

    (problem,) = check_minimums_exceed_reference(scenario, reference)
    assert problem.code == "bounds_min_sum_exceeds_reference"
    assert [entry.key for entry in problem.entries] == ["asset:asset:a", "asset:asset:b"]
    assert problem.sums == (R(190), R(150))  # TL-4 of project 67: the two figures the check compared

    fine = _limited_scenario(asset_a=(_LIMIT_A("amount", R(100)), None), asset_b=(_LIMIT_A("share", R(1, 3)), None))
    assert check_minimums_exceed_reference(fine, reference) == ()  # 100 + 50 = 150 is not above 150
    cash_pushes_over = _limited_scenario(asset_a=(_LIMIT_A("amount", R(100)), None), cash=(pac_models.ExactCashEntry(broker_id="broker:a", currency="EUR", minimum=_LIMIT_A("amount", R(51)), maximum=None),))
    (problem,) = check_minimums_exceed_reference(cash_pushes_over, reference)
    assert [entry.key for entry in problem.entries] == ["asset:asset:a", "cash:broker:a:EUR"]


def test_minimum_above_maximum_names_the_entry() -> None:
    """Check 1: one problem per entry whose minimum exceeds its maximum, forms mixed: a share is resolved on the reference."""
    scenario = _limited_scenario(
        asset_a=(_LIMIT_A("amount", R(80)), _LIMIT_A("amount", R(70))),
        asset_b=(_LIMIT_A("share", R(1, 2)), _LIMIT_A("amount", R(74))),
        cash=(pac_models.ExactCashEntry(broker_id="broker:a", currency="EUR", minimum=_LIMIT_A("amount", R(10)), maximum=_LIMIT_A("amount", R(10))),),
    )
    problems = check_minimum_above_maximum(scenario, fixed_reference_of(scenario))
    assert [(problem.code, [entry.key for entry in problem.entries]) for problem in problems] == [
        ("bound_min_above_max", ["asset:asset:a"]),
        ("bound_min_above_max", ["asset:asset:b"]),
    ]  # asset b: 50% of EUR150 = 75 > 74; the cash cell's equal bounds are fine


def test_asset_maximum_below_current_value_cannot_fire_in_a_pac() -> None:
    """Check 3 needs a holding: a PAC has none (``ExactPlannerScenario`` refuses them), so the check names nothing there,
    even with a maximum of zero. It fires in a scenario that holds the Asset and cannot sell it (block B)."""
    scenario = _limited_scenario(asset_a=(None, _LIMIT_A("amount", R(0))))
    assert check_maximum_below_current(scenario, build_scenario_index(scenario), fixed_reference_of(scenario)) == ()
    with pytest.raises(ValueError, match="holdings"):
        replace(scenario, holdings=(object(),))


# ---------------------------------------------------------------------------
# A3 step 3 (project 67): V5 in the exact replay (V10 was removed after the consultant's re-read)
# ---------------------------------------------------------------------------


def _limit_plan_scenario(
    *,
    weights: tuple[ExactRatio, ExactRatio] = (R(1, 2), R(1, 2)),
    asset_a: tuple[pac_models.ExactLimit | None, pac_models.ExactLimit | None] = (None, None),
    asset_b: tuple[pac_models.ExactLimit | None, pac_models.ExactLimit | None] = (None, None),
    cash: tuple[pac_models.ExactCashEntry, ...] = (),
) -> ExactPlannerScenario:
    """One Broker holding EUR100, two EUR Assets at EUR10 a unit (at most 10 units each), whole-euro quanta: the reference is EUR100."""
    capability = _capability("capability:whole")
    fee = _fee("fee:buy", capability.capability_id, "buy")
    broker = _broker("broker:hub", (capability,), (fee,))

    def buy(asset_id: str) -> ExactOrderRoute:
        return _order_route(f"route:buy:{asset_id[-1]}", broker_id=broker.broker_id, asset_id=asset_id, capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(10))

    return replace(
        _scenario(
            "scenario:limit-plan",
            product="pac",
            policy="proportional",
            assets=(_asset("asset:a", price=R(10)), _asset("asset:b", price=R(10))),
            brokers=(broker,),
            existing_cash=(_cash("cash:hub", broker.broker_id, R(100)),),
            order_routes=(buy("asset:a"), buy("asset:b")),
            currency_quantums=(("EUR", ONE),),
        ),
        target_weights=(
            pac_models.ExactTargetWeight("asset:a", weights[0], minimum=asset_a[0], maximum=asset_a[1]),
            pac_models.ExactTargetWeight("asset:b", weights[1], minimum=asset_b[0], maximum=asset_b[1]),
        ),
        cash_entries=cash,
    )


def _buys(scenario: ExactPlannerScenario, a: int = 0, b: int = 0) -> ExactEvaluation:
    view = build_exact_policy_view(scenario)
    return evaluate_exact_candidate(scenario, view, _candidate(view, {exact_decision_id("buy_quantum", "route:buy:a"): a, exact_decision_id("buy_quantum", "route:buy:b"): b}))


def _failed(evaluation: ExactEvaluation) -> set[str]:
    return {item.ref_id for item in evaluation.constraints if not item.satisfied}


_CASH_MAX_40 = (pac_models.ExactCashEntry(broker_id="broker:hub", currency="EUR", minimum=None, maximum=pac_models.ExactLimit("amount", R(40))),)


def test_cash_maximum_makes_the_plan_invest_the_excess() -> None:
    """T11, PAC form, at the exact level: EUR100 of cash and a maximum of EUR40 on the cell. A plan that leaves more than 40 in
    the cell fails V5; one that invests at least 60 passes."""
    scenario = _limit_plan_scenario(cash=_CASH_MAX_40)
    entry = "constraint:entry_value_within_limits:cash:broker:hub:EUR"

    nothing = _buys(scenario)
    assert entry in _failed(nothing)
    assert nothing.feasible is False
    five = _buys(scenario, a=3, b=2)  # invests 50: 50 left in the cell, one unit short
    assert entry in _failed(five)
    six = _buys(scenario, a=3, b=3)
    assert entry not in _failed(six)
    assert six.feasible is True


def test_necessary_fees_are_not_uninvested_cash() -> None:
    """A3 fix: EUR1000 of cash, an Asset at EUR99, a fixed fee of EUR3 and a cash maximum of EUR8. The honest plan buys 10 units,
    pays EUR3 and leaves EUR7, inside the maximum. A rule «what is not invested is at most the sum of the maxima» (the old V10)
    counted the fee as uninvested, saw 1000 - 990 = 10 > 8 and declared there was no solution."""
    capability = _capability("capability:whole")
    fee = _fee("fee:buy", capability.capability_id, "buy", fixed=R(3))
    broker = _broker("broker:hub", (capability,), (fee,))
    scenario = replace(
        _scenario(
            "scenario:fees-and-cash-maximum",
            product="pac",
            policy="proportional",
            assets=(_asset("asset:a", price=R(99)),),
            brokers=(broker,),
            existing_cash=(_cash("cash:hub", broker.broker_id, R(1000)),),
            order_routes=(_order_route("route:buy:a", broker_id=broker.broker_id, asset_id="asset:a", capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(20)),),
            currency_quantums=(("EUR", ONE),),
        ),
        cash_entries=(pac_models.ExactCashEntry(broker_id=broker.broker_id, currency="EUR", minimum=None, maximum=pac_models.ExactLimit("amount", R(8))),),
    )
    view = build_exact_policy_view(scenario)
    candidate = _candidate(view, {exact_decision_id("buy_quantum", "route:buy:a"): 10})
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.feasible is True, evaluation.conflict_codes
    assert [item.final_spendable for item in evaluation.ledgers] == [R(7)]


def test_asset_maximum_caps_the_final_value() -> None:
    scenario = _limit_plan_scenario(asset_a=(None, pac_models.ExactLimit("amount", R(30))))
    ref = "constraint:entry_value_within_limits:asset:asset:a"
    assert ref not in _failed(_buys(scenario, a=3, b=3))  # 30 is the maximum, not above it
    assert ref in _failed(_buys(scenario, a=4, b=0))
    (fact,) = [item for item in _buys(scenario, a=4).constraints if item.ref_id == ref]
    assert (fact.value, fact.lower_bound, fact.upper_bound) == (R(40), None, R(30)), "the limits are published in the fact"


def test_asset_minimum_forces_a_buy_at_zero_target() -> None:
    """Absurdity n. 17: an Asset with a target of zero and a minimum of EUR20 is bought, not ignored; a share resolves on the
    reference (a fifth of EUR100 is 20)."""
    for minimum in (pac_models.ExactLimit("amount", R(20)), pac_models.ExactLimit("share", R(1, 5))):
        scenario = _limit_plan_scenario(weights=(R(0), R(1)), asset_a=(minimum, None))
        ref = "constraint:entry_value_within_limits:asset:asset:a"
        assert ref in _failed(_buys(scenario, a=1, b=5)), minimum
        assert ref not in _failed(_buys(scenario, a=2, b=5)), minimum


def test_a_scenario_without_limits_has_no_limit_facts() -> None:
    """Nothing is added to the view without limits: the replay of a limitless scenario is what it was in A2."""
    scenario = _limit_plan_scenario()
    view = build_exact_policy_view(scenario)
    assert not [ref for ref in view.constraints if ref.code in {"ENTRY_VALUE_WITHIN_LIMITS"}]


def test_limit_violation_is_never_a_rounding_top_up() -> None:
    """D9: a plan the replay finds outside a limit is an error of the model, not a cash a rounding left short; no top-up
    repairs it, however small the excess. The classifier raises instead of proposing cash."""
    scenario = _limit_plan_scenario(asset_a=(None, pac_models.ExactLimit("amount", R(30))))
    evaluation = _buys(scenario, a=4, b=0)  # one unit above the maximum: the smallest excess there is
    assert evaluation.feasible is False
    assert "ENTRY_VALUE_WITHIN_LIMITS" in evaluation.conflict_codes
    with pytest.raises(ExactReplayRejectedError):
        EV.rounding_top_ups(scenario, evaluation)


# ---------------------------------------------------------------------------
# A3 fix (consultant's re-read): V5 rows hold to the unit, not to SCIP's float tolerance
# ---------------------------------------------------------------------------


def _usd_by_amount_scenario(maximum: ExactRatio | None, *, minimum: ExactRatio | None = None) -> ExactPlannerScenario:
    """One USD Asset (price 1) bought by amount (cents) at a Broker holding EUR1500, FX 1.085, one EUR limit on the Asset.

    A cent of USD is worth 1/108.5 EUR, so reachable values are 100000/108.5 = 921.658986... EUR and its neighbours 0.0092
    EUR apart. A limit less than a thousandth of a euro under one of them is inside SCIP's relative tolerance on a row near EUR1000.
    """
    capability = _capability("capability:amount", kind="monetary_amount", step=CENT)
    fee = _fee("fee:buy:usd", capability.capability_id, "buy", currency="USD")
    broker = _broker("broker:hub", (capability,), (fee,))
    route = _order_route("route:buy:usd", broker_id=broker.broker_id, asset_id="asset:usd", capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(10_000), currency="USD")
    base = _scenario(
        "scenario:usd-by-amount",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:usd", price=ONE, currency="USD"),),
        brokers=(broker,),
        existing_cash=(_cash("cash:eur", broker.broker_id, R(1500)),),
        order_routes=(route,),
        fx_rates=(_fx_rate("EUR", "USD", R(1085, 1000)),),
        currency_quantums=(("EUR", CENT), ("USD", CENT)),
    )
    (weight,) = base.target_weights
    return replace(
        base,
        target_weights=(replace(weight, minimum=None if minimum is None else pac_models.ExactLimit("amount", minimum), maximum=None if maximum is None else pac_models.ExactLimit("amount", maximum)),),
    )


_CENTS_BOUGHT = 100_000
_VALUE_OF_THOSE_CENTS = R(_CENTS_BOUGHT, 1085) * R(10)  # 100000 cents = 1000 USD = 921.658986... EUR
_MAXIMUM_JUST_UNDER_IT = _VALUE_OF_THOSE_CENTS - R(4, 10_000)


def _relay_scenario() -> ExactPlannerScenario:
    """One Broker holding EUR2 and USD2; a USD Asset and a CHF Asset (2 each, at most 1 unit): EUR to USD and USD to CHF could chain."""
    capability = _capability("capability:whole")
    fees = tuple(_fee(f"fee:buy:{currency.lower()}", capability.capability_id, "buy", currency=currency) for currency in ("CHF", "USD"))
    broker = _broker("broker:hub", (capability,), fees)
    fee_by_currency = {"CHF": fees[0], "USD": fees[1]}

    def buy(route_id: str, asset_id: str, currency: str) -> ExactOrderRoute:
        return _order_route(route_id, broker_id=broker.broker_id, asset_id=asset_id, capability=capability, fee_id=fee_by_currency[currency].fee_schedule_id, side="buy", cap=R(1), currency=currency)

    return _scenario(
        "scenario:relay",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:chf", price=R(2), currency="CHF"), _asset("asset:usd", price=R(2), currency="USD")),
        brokers=(broker,),
        existing_cash=(_cash("cash:eur", broker.broker_id, R(2)), _cash("cash:usd", broker.broker_id, R(2), currency="USD")),
        order_routes=(buy("route:buy:chf", "asset:chf", "CHF"), buy("route:buy:usd", "asset:usd", "USD")),
        fx_rates=(_fx_rate("CHF", "EUR", ONE), _fx_rate("CHF", "USD", R(5, 4)), _fx_rate("EUR", "USD", R(5, 4))),
        currency_quantums=(("CHF", ONE), ("EUR", ONE), ("USD", ONE)),
    )


def test_a_currency_that_receives_a_conversion_does_not_give_one() -> None:
    """V7, widened: on a Broker a currency that receives a conversion gives none. EUR to USD followed by USD to CHF would
    burn cash through a chain, and the engine never pays a buy through a chain (``buy_pool_currencies``); either step alone is
    fine, and so is a currency that only gives (EUR to USD and EUR to CHF)."""
    scenario = _relay_scenario()
    view = build_exact_policy_view(scenario)
    eur_usd = fx_id(scenario, source="EUR", destination="USD")
    usd_chf = fx_id(scenario, source="USD", destination="CHF")
    eur_chf = fx_id(scenario, source="EUR", destination="CHF")
    relay = "constraint:fx_no_relay:10:broker:hub:USD"

    chained = evaluate_exact_candidate(scenario, view, _candidate(view, {eur_usd: 2, usd_chf: 2}))
    (fact,) = [item for item in chained.constraints if item.ref_id == relay]
    assert (fact.satisfied, chained.feasible) == (False, False)
    for allowed in ({eur_usd: 2}, {usd_chf: 2}, {eur_usd: 1, eur_chf: 1}):
        evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, allowed))
        (fact,) = [item for item in evaluation.constraints if item.ref_id == relay]
        assert fact.satisfied is True, allowed


def test_sum_of_minimums_ignores_the_trapped_cash_of_a_cell() -> None:
    """A3 fix: cash that reaches no buy is outside ``fixed_reference`` but sits in its cell, so it already honours that cell's
    minimum. For each cash cell only the part of the minimum above its trapped cash counts: a check before the calculation
    must never be stricter than reality."""
    base = _limit_plan_scenario()
    idle = _broker("broker:idle")
    scenario = replace(
        base,
        brokers=tuple(sorted((*base.brokers, idle), key=lambda item: item.broker_id)),
        existing_cash=(*base.existing_cash, _cash("cash:idle", "broker:idle", R(30))),
        target_weights=(replace(base.target_weights[0], minimum=pac_models.ExactLimit("amount", R(100))), base.target_weights[1]),
        cash_entries=(pac_models.ExactCashEntry(broker_id="broker:idle", currency="EUR", minimum=pac_models.ExactLimit("amount", R(30)), maximum=None),),
    )
    reference = fixed_reference_of(scenario)
    trapped = trapped_cash_by_cell(scenario)
    assert reference == R(100), "the idle broker's EUR30 reaches no buy: it is outside the reference"
    assert trapped == {("broker:idle", "EUR"): R(30)}

    assert check_minimums_exceed_reference(scenario, reference, trapped) == ()  # 100 for the Asset, and 30 already there
    (problem,) = check_minimums_exceed_reference(scenario, reference)  # ignoring the trapped cash, 100 + 30 > 100
    assert [entry.key for entry in problem.entries] == ["asset:asset:a", "cash:broker:idle:EUR"]
    above = replace(scenario, cash_entries=(replace(scenario.cash_entries[0], minimum=pac_models.ExactLimit("amount", R(31))),))
    (problem,) = check_minimums_exceed_reference(above, reference, trapped)  # one euro beyond the trapped 30 needs reachable money
    assert [entry.key for entry in problem.entries] == ["asset:asset:a", "cash:broker:idle:EUR"]
    # TL-4 of project 67: the sum counts only the cell's euro above its trapped cash, and the base is the reachable 100, below
    # the 130 of cash the scenario holds. The sentence says «101 … more than 100», never a sum below its base.
    assert problem.sums == (R(101), R(100))


# ---------------------------------------------------------------------------
# B1 (project 67): the single objective at the exact level, without the two phases
# ---------------------------------------------------------------------------


def test_primary_view_serves_invest_and_sell_with_sells_disabled() -> None:
    """B1-1: ``primary`` serves every policy. On ``invest_and_sell`` its sells stay ``disabled`` until C1 opens them, it
    starts from the zero vector, and doing nothing replays."""
    scenario = _invest_and_sell_scenario()

    view = build_exact_policy_view(scenario)

    assert (view.purpose, view.policy) == ("primary", "invest_and_sell")
    assert all(item.baseline_quanta == 0 and item.lower_quanta == 0 for item in view.decisions)
    sells = [item for item in view.decisions if item.family == "sell_quantum"]
    assert sells and all((item.mode, item.upper_quanta) == ("disabled", 0) for item in sells)
    assert evaluate_exact_candidate(scenario, view, _candidate(view)).candidate_valid


def _reb_view_and_candidate(scenario: ExactPlannerScenario, quanta: dict[str, int] | None = None) -> tuple[ExactPolicyView, CandidateActionVector]:
    view = build_exact_policy_view(scenario)
    return view, _candidate(view, quanta or {})


def test_plan_accounts_reconcile_to_initial_minus_final_wealth() -> None:
    """B1-6, specifica §5: ``F`` is what enters the plan (invested plus selected cash and contributions), ``W`` what it is worth
    at the end (Assets plus spendable cash plus contributions left undeposited), ``C = F − W`` the money lost, and it is the
    accounting identity the replay already checks: reserves plus losses plus rounding. ``N`` is ``F`` less the Assets and the
    cash cells with a target. T4: buying 195 of B for a fee of 5 loses exactly 5."""
    scenario = cases.t4()
    for quanta, expected in (
        ({}, {"F": R(10_000), "W": R(10_000), "C": ZERO, "N": R(200)}),
        ({cases.buy_decision("asset:b"): 195}, {"F": R(10_000), "W": R(9_995), "C": R(5), "N": R(5)}),
    ):
        view, candidate = _reb_view_and_candidate(scenario, quanta)
        accounting = evaluate_exact_candidate(scenario, view, candidate).accounting
        assert {"F": accounting.initial_wealth, "W": accounting.final_wealth, "C": accounting.wealth_loss, "N": accounting.uninvested} == expected
        assert accounting.wealth_loss == accounting.physical_reserves + accounting.economic_losses + accounting.rounding_adjustment + accounting.identity_delta


def test_rebalancer_share_limits_resolve_against_initial_wealth() -> None:
    """Specifica §15 n. 17: a share limit reads the Tool's reference, ``F`` in the Rebalancer. With cash that no route can spend
    (here 1 000 EUR on a Broker without capabilities) ``F`` = 11 000 while ``fixed_reference`` = 10 000: a maximum of one half
    on B is 5 500, not 5 000."""
    base = cases.t4()
    idle = replace(
        base,
        brokers=tuple(sorted((*base.brokers, replace(base.brokers[0], broker_id="broker:y", name="broker:y", capabilities=(), fee_schedules=())), key=lambda item: item.broker_id)),
        existing_cash=tuple(sorted((*base.existing_cash, replace(base.existing_cash[0], cash_id="cash:y:eur", broker_id="broker:y", available=cases.money(R(1_000)), selected=cases.money(R(1_000)))), key=lambda item: item.cash_id)),
        target_weights=tuple(replace(item, maximum=pac_models.ExactLimit("share", R(1, 2))) if item.asset_id == "asset:b" else item for item in base.target_weights),
    )
    view, candidate = _reb_view_and_candidate(idle)
    evaluation = evaluate_exact_candidate(idle, view, candidate)

    assert (evaluation.accounting.initial_wealth, evaluation.accounting.fixed_reference) == (R(11_000), R(10_000))
    limit = _by_id(evaluation.constraints, "ref_id", "constraint:entry_value_within_limits:asset:asset:b")
    assert limit.upper_bound == R(5_500)


def test_pac_view_and_values_ignore_the_target_fidelity() -> None:
    """B1-7: the PAC keeps its five objectives in today's order and never carries a fidelity; a PAC scenario that names one,
    or a Rebalancer that names none, is refused at construction. ``λ`` must be positive."""
    scenario = _pac_scenario()
    view = build_exact_policy_view(scenario)
    assert scenario.target_fidelity is None
    assert tuple(ref.code for ref in view.objectives) == ("fixed_l2", "shortfall", "route_priority", "explicit_cost", "active_order_rows")

    with pytest.raises(ValueError, match="fidelity"):
        replace(scenario, target_fidelity=pac_models.ExactTargetFidelity(kind="weighted", distance_weight=ONE))
    with pytest.raises(ValueError, match="fidelity"):
        replace(_invest_only_scenario(), target_fidelity=None)
    for kind, distance_weight in (("weighted", ZERO), ("weighted", None), ("target_first", ONE)):
        with pytest.raises(ValueError):
            pac_models.ExactTargetFidelity(kind=kind, distance_weight=distance_weight)


def _t4_with_cash_target() -> ExactPlannerScenario:
    """T4 with the weights of the plan's test 6: A 50 %, B 48 %, the Broker's EUR cash 2 %."""
    return cases.t4(
        weights_override={"asset:a": R(1, 2), "asset:b": R(12, 25)},
        cash_entries=(pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=None, maximum=None, weight=R(1, 50)),),
    )


def test_rebalancer_targets_read_initial_wealth_and_cash_cells_with_a_target_are_rows() -> None:
    """B1-8, specifica §6.1: in the Rebalancer a target is ``w · F`` and a cash cell with a target is an entry of its own, with a
    row like an Asset's; ``N`` leaves it out. T4 with A 50 %, B 48 %, cash 2 %: doing nothing hits every target (``N = 0``);
    buying 195 of B leaves the cell empty, 200 under its target, and ``N`` = the 5 of fee."""
    scenario = _t4_with_cash_target()
    for quanta, cash_final, b_final, uninvested in (({}, R(200), R(4_800), ZERO), ({cases.buy_decision("asset:b"): 195}, ZERO, R(4_995), R(5))):
        view, candidate = _reb_view_and_candidate(scenario, quanta)
        evaluation = evaluate_exact_candidate(scenario, view, candidate)
        (cash,) = evaluation.cash_targets
        b = _by_id(evaluation.assets, "asset_id", "asset:b")
        assert (cash.broker_id, cash.currency, cash.target_weight, cash.target_value) == (cases.BROKER, "EUR", R(1, 50), R(200))
        assert (cash.final_value, cash.residual) == (cash_final, cash_final - R(200))
        assert (b.target_value, b.final_value) == (R(4_800), b_final)
        assert evaluation.accounting.uninvested == uninvested


def test_a_cash_entry_with_only_a_weight_is_no_limit() -> None:
    """A cash entry with a target and no minimum or maximum carries no limit: no ``ENTRY_VALUE_WITHIN_LIMITS`` fact, and a «no
    solution» does not name it (M20)."""
    scenario = _t4_with_cash_target()
    view = build_exact_policy_view(scenario)
    assert limited_entries(scenario) == ()
    assert not [ref for ref in view.constraints if ref.code == "ENTRY_VALUE_WITHIN_LIMITS"]


def test_pac_cash_entries_never_carry_a_weight() -> None:
    with pytest.raises(ValueError, match="cash"):
        replace(_pac_scenario(), cash_entries=(pac_models.ExactCashEntry(broker_id="broker:a", currency="EUR", minimum=None, maximum=None, weight=R(1, 2)),))


_TARGET_FIRST = pac_models.ExactTargetFidelity(kind="target_first", distance_weight=None)


def _reb_scores(build: Any, quanta: dict[str, int] | None = None, *, distance_weight: ExactRatio = ONE, **fields: Any) -> dict[str, ExactRatio]:
    """``J`` under a weighted fidelity, and ``D`` and ``C`` under «Target first», for one candidate of one small case.

    The two views of the Rebalancer (B1-9, B1-10): a weighted fidelity publishes ``plan_score`` alone, «Target first» the chain
    ``target_distance`` then ``wealth_loss``. ``N`` comes from the accounting."""
    scores: dict[str, ExactRatio] = {}
    for fidelity in (pac_models.ExactTargetFidelity(kind="weighted", distance_weight=distance_weight), _TARGET_FIRST):
        scenario = build(target_fidelity=fidelity, **fields)
        view, candidate = _reb_view_and_candidate(scenario, quanta)
        evaluation = evaluate_exact_candidate(scenario, view, candidate)
        assert evaluation.feasible, evaluation.conflict_codes
        scores |= _objective_map(view, evaluation)
        scores["N"] = evaluation.accounting.uninvested
    return {"D": scores["target_distance"], "N": scores["N"], "C": scores["wealth_loss"], "J": scores["plan_score"]}


def test_rebalancer_views_publish_one_score_or_the_target_first_chain() -> None:
    """B1-9, B1-10, B2-1: a weighted fidelity is one score, ``plan_score``; «Target first» is ``target_distance`` then
    ``wealth_loss``. Both end with the tie-breaks of specifica §6.4: fewer operations, then the route priorities. No
    ``turnover`` any more."""
    weighted = build_exact_policy_view(cases.t4())
    target_first = build_exact_policy_view(cases.t4(target_fidelity=_TARGET_FIRST))
    tie_breaks = [("operation_count", "count"), ("route_priority", "ordinal_penalty")]
    assert [(ref.code, ref.unit.kind) for ref in weighted.objectives] == [("plan_score", "valuation_money"), *tie_breaks]
    assert [(ref.code, ref.unit.kind) for ref in target_first.objectives] == [("target_distance", "valuation_money_squared"), ("wealth_loss", "valuation_money"), *tie_breaks]


def test_rebalancer_no_trade_scores_scaled_distance() -> None:
    """T1: A 5 040, B 4 960, no cash. No operation: ``D`` = 40² + 40² = 3 200, nothing lost, ``J`` = 3 200 / 10 000."""
    assert _reb_scores(cases.t1) == {"D": R(3_200), "N": ZERO, "C": ZERO, "J": R(8, 25)}


def test_rebalancer_buy_beats_idle_cash_when_penalty_exceeds_fee() -> None:
    """T4: A 5 000, B 4 800, cash 200. Buying 195 of B: ``N`` = 5 (the fee), ``D`` = 5² + 5² = 50, ``C`` = 5,
    ``J`` = 50 / 10 000 + 5 = 1 001 / 200. Doing nothing: ``D`` = 200² + 200² = 80 000, ``J`` = 8."""
    assert _reb_scores(cases.t4, {cases.buy_decision("asset:b"): 195}) == {"D": R(50), "N": R(5), "C": R(5), "J": R(1_001, 200)}
    assert _reb_scores(cases.t4)["J"] == R(8)


def test_rebalancer_idle_cash_wins_when_fee_exceeds_penalty() -> None:
    """T5: A 5 000, B 4 900, cash 100. Doing nothing: ``D`` = 100² + 100² = 20 000, ``J`` = 2. Buying 95 of B: ``J`` = 1 001 / 200."""
    assert _reb_scores(cases.t5) == {"D": R(20_000), "N": R(100), "C": ZERO, "J": R(2)}
    assert _reb_scores(cases.t5, {cases.buy_decision("asset:b"): 95})["J"] == R(1_001, 200)


def test_rebalancer_wasted_money_never_lowers_the_score() -> None:
    """T6 (specifica §6.2), ``λ = 4``: one unit at 4 000, cash 6 000. Buying one unit: ``D`` = 2 000² + 2 000², ``J`` = 3 205.
    Doing nothing: ``J`` = 28 800. The same plan plus a conversion that buys nothing (100 EUR into USD, which lands as 99 USD
    and stays idle) keeps the same ``D`` and adds exactly what it loses, ``w = F − W`` of the extra (P1)."""
    one_unit = {cases.buy_decision("asset:a"): 1}
    four = R(4)
    assert _reb_scores(cases.t6, one_unit, distance_weight=four) == {"D": R(8_000_000), "N": R(2_000), "C": R(5), "J": R(3_205)}
    assert _reb_scores(cases.t6, distance_weight=four)["J"] == R(28_800)

    honest = _reb_scores(cases.t6, one_unit, distance_weight=four, with_usd=True)
    wasteful = _reb_scores(cases.t6, one_unit | {"fx:8:broker:x:EUR:USD": 10_000}, distance_weight=four, with_usd=True)
    wasted = wasteful["C"] - honest["C"]
    assert wasted == ONE  # 100 EUR became 99 USD, worth 99 EUR
    assert (wasteful["D"], wasteful["J"]) == (honest["D"], honest["J"] + wasted)


def test_target_first_puts_distance_before_lost_money() -> None:
    """«Target first» on T5: buying 95 of B wins on the first objective (``D`` = 50 against 20 000), then pays ``C`` = 5."""
    buy = _reb_scores(cases.t5, {cases.buy_decision("asset:b"): 95})
    idle = _reb_scores(cases.t5)
    assert (buy["D"], buy["C"]) == (R(50), R(5))
    assert (buy["D"], buy["C"]) < (idle["D"], idle["C"])


def test_rebalancer_cash_item_with_target_enters_the_distance() -> None:
    """T4 with A 50 %, B 48 %, cash 2 %: doing nothing is on target, ``D`` = 0; buying 195 of B gives
    ``D`` = 195² + 200² + 5² = 78 050 (B over its target, the cell under it, ``N`` = the fee)."""

    def build(**fields: Any) -> ExactPlannerScenario:
        return cases.t4(
            weights_override={"asset:a": R(1, 2), "asset:b": R(12, 25)},
            cash_entries=(pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=None, maximum=None, weight=R(1, 50)),),
            **fields,
        )

    assert _reb_scores(build)["D"] == ZERO
    assert _reb_scores(build, {cases.buy_decision("asset:b"): 195})["D"] == R(78_050)


def test_free_cash_moves_do_not_change_the_score() -> None:
    """P4: moving cash for free between two Brokers changes neither ``D`` nor ``C``, so ``J`` stays. T4 plus a second Broker
    and a free transfer lane: sending 100 EUR from ``broker:x`` to ``broker:y`` leaves the score as it was."""

    def build(**fields: Any) -> ExactPlannerScenario:
        base = cases.t4(**fields)
        broker_y = replace(base.brokers[0], broker_id="broker:y", name="broker:y")
        lane = pac_models.ExactTransferLane(source_broker_id=cases.BROKER, destination_broker_id="broker:y", currency="EUR")
        return replace(base, brokers=tuple(sorted((*base.brokers, broker_y), key=lambda item: item.broker_id)), transfer_lanes=(lane,))

    view = build_exact_policy_view(build())
    (transfer_id,) = [item.decision_id for item in view.decisions if item.family == "broker_transfer"]
    assert _reb_scores(build, {transfer_id: 10_000}) == _reb_scores(build)


def test_rebalancer_with_nothing_to_plan_reports_nonempty_instead_of_dividing_by_zero() -> None:
    """``J`` divides the distance by ``F``. A Rebalancer scenario worth nothing (no holding, no cash) has ``F`` = 0: the replay
    still answers, with the ``REBALANCER_NONEMPTY`` conflict, and never raises."""
    scenario = cases.scenario("empty", holdings={}, cash=ZERO, weights={"asset:a": R(1, 2), "asset:b": R(1, 2)})
    view, candidate = _reb_view_and_candidate(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert "REBALANCER_NONEMPTY" in evaluation.conflict_codes


def test_rebalancer_nonempty_needs_only_a_current_portfolio() -> None:
    """B1-11, specifica §15 n. 14: the Rebalancer needs something to rebalance, ``V⁰ > 0``, and nothing more. With a target on
    cash a plan may end with nothing invested: selling every unit is admitted by this rule."""
    scenario = _invest_and_sell_scenario()
    everything = {exact_decision_id("sell_quantum", "route:sell:a"): 8, exact_decision_id("sell_quantum", "route:sell:b"): 2}
    view = _sell_door(scenario, everything)

    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, everything))

    assert evaluation.accounting.final_invested == ZERO
    assert "REBALANCER_NONEMPTY" not in evaluation.conflict_codes
    fact = _by_id(evaluation.constraints, "ref_id", "constraint:rebalancer_nonempty:global")
    assert (fact.value, fact.satisfied) == (evaluation.accounting.current_invested, True)


def test_operation_count_counts_orders_conversions_transfers_and_deposits() -> None:
    """B2-1, specifica §6.4: the first tie-break counts every operation of the plan: orders, conversions, transfers between
    Brokers, deposits. T6 with its USD conversion and a free transfer lane: one unit bought, 100 EUR converted and 100 EUR
    moved is three operations; doing nothing is none."""

    def build(**fields: Any) -> ExactPlannerScenario:
        base = cases.t6(with_usd=True, target_fidelity=pac_models.ExactTargetFidelity(kind="weighted", distance_weight=R(4)), **fields)
        broker_y = replace(base.brokers[0], broker_id="broker:y", name="broker:y")
        lane = pac_models.ExactTransferLane(source_broker_id=cases.BROKER, destination_broker_id="broker:y", currency="EUR")
        return replace(base, brokers=tuple(sorted((*base.brokers, broker_y), key=lambda item: item.broker_id)), transfer_lanes=(lane,))

    scenario = build()
    view = build_exact_policy_view(scenario)
    (transfer_id,) = [item.decision_id for item in view.decisions if item.family == "broker_transfer"]
    for quanta, expected in (({}, ZERO), ({cases.buy_decision("asset:a"): 1, "fx:8:broker:x:EUR:USD": 10_000, transfer_id: 10_000}, R(3))):
        evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta))
        assert evaluation.feasible, evaluation.conflict_codes
        assert _objective_map(view, evaluation)["operation_count"] == expected
