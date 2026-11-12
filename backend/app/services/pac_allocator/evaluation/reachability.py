"""Which funding sources can reach a buy, the currency pools the buys draw on, and the one list of FX decisions.

``fx_decision_specs`` is the single place that says which FX decisions a scenario has. The policy view, the decision bounds,
the tie-break rows, the replay, its facts and constraint refs, and the SCIP model all read it; none derives an FX decision or
its key on its own (A2, project 67). The half-quantum margin of ``bounds._total_resource_bound`` is the one exception on
purpose: it keeps counting per buy route and pool currency, so that decision boxes and the oracle's domains stay as they were.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from backend.app.services.pac_allocator.evaluation.keys import entity_refs, exact_decision_id, fx_debit_key, fx_pair_key
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex
from backend.app.services.pac_allocator.models import (
    Checkpoint,
    EntityRef,
    ExactPlannerScenario,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
)

_EXACT_ZERO = ExactRatio(0)


def _can_reach_buy(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
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
        if route.side != "buy" or route.broker_id != broker_id or route.asset_id not in positive_targets or (route.cap is not None and route.cap.value <= _EXACT_ZERO):
            continue
        quote_currency = index.assets[route.asset_id].quote.price.currency
        if currency == quote_currency or fx_pair_key(currency, quote_currency) in index.fx_rate_by_pair:
            return True
    return False


def source_reachability(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
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


def buy_pool_currencies(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
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
    return tuple(sorted(currency for currency in candidates if fx_pair_key(currency, quote_currency) in index.fx_rate_by_pair))


@dataclass(frozen=True, slots=True)
class FxDecisionSpec:
    """One FX decision of a scenario and everything its consumers need to name it.

    ``key`` keys the decision's constraint refs and facts and suffixes its ledger postings (``fx-debit:<key>``);
    ``scope`` and ``entity_refs`` describe it in the refs; ``tie_break`` is its row among the tie-break keys;
    ``representative_route_id`` is the buy route the published FX action names (contract ``1.0.0``).
    """

    decision_id: str
    key: str
    broker_id: str
    source_currency: str
    destination_currency: str
    entity_refs: tuple[EntityRef, ...]
    scope: str
    tie_break: tuple[str, ...]
    representative_route_id: str


def fx_decision_specs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[FxDecisionSpec, ...]:
    """Every FX decision of ``scenario``: one per Broker and ordered currency pair, sorted by (Broker, source, destination).

    A pair exists where a buy route of the Broker is quoted in the destination currency and the source is one of that buy's pool
    currencies (``buy_pool_currencies``: other currencies with cash possible on the Broker and a direct pair to the quote). Two buy
    routes on the same pair share the decision. Its representative route, the one the published FX action names under contract
    ``1.0.0``, is the first such buy route of the Broker in canonical (route id) order.
    """
    routes_by_pair: dict[tuple[str, str, str], list[str]] = {}
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
            routes_by_pair.setdefault((route.broker_id, currency, quote_currency), []).append(route.route_id)
    specs: list[FxDecisionSpec] = []
    for (broker_id, source_currency, destination_currency), route_ids in sorted(routes_by_pair.items()):
        key = fx_debit_key(broker_id, source_currency, destination_currency)
        decision_id = exact_decision_id("fx_debit", key)
        specs.append(
            FxDecisionSpec(
                decision_id=decision_id,
                key=key,
                broker_id=broker_id,
                source_currency=source_currency,
                destination_currency=destination_currency,
                entity_refs=entity_refs(("broker", broker_id), ("source_currency", source_currency), ("destination_currency", destination_currency)),
                scope="broker",
                tie_break=("", broker_id, source_currency, "fx", destination_currency, "", decision_id),
                representative_route_id=min(route_ids),
            )
        )
    return tuple(specs)
