"""Which funding sources can reach a buy, the currency pools the buys draw on, and the one list of FX decisions.

``fx_decision_specs`` is the single place that says which FX decisions a scenario has. The policy view, the decision bounds,
the tie-break rows, the replay, its facts and constraint refs, and the SCIP model all read it; none derives an FX decision or
its key on its own (A2, project 67). The half-quantum margin of ``bounds._total_resource_bound`` is the one exception on
purpose: it keeps counting per buy route and pool currency, so that decision boxes and the oracle's domains stay as they were.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from backend.app.services.pac_allocator.evaluation.keys import broker_transfer_key, entity_refs, exact_decision_id, fx_debit_key, fx_pair_key
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


def _can_reach_buy_over_lanes(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    *,
    broker_id: str,
    currency: str,
    checkpoint: Checkpoint | None,
) -> bool:
    """Cash of ``currency`` at ``broker_id`` reaches a buy there, or on a Broker one transfer lane away (B3, project 67).

    One hop is enough: the Rebalancer's lanes join every pair of its Brokers (specification §15 n. 2), and a lane has no cap,
    so cash that reaches a buy through one lane reaches it whole. A PAC scenario has no lanes and reads as before.
    """
    if _can_reach_buy(scenario, index, broker_id=broker_id, currency=currency, checkpoint=checkpoint):
        return True
    for lane in scenario.transfer_lanes:
        check_budget(checkpoint)
        if lane.source_broker_id == broker_id and lane.currency == currency and _can_reach_buy(scenario, index, broker_id=lane.destination_broker_id, currency=currency, checkpoint=checkpoint):
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
    if source_broker_id is not None and _can_reach_buy_over_lanes(
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
        if not _can_reach_buy_over_lanes(scenario, index, broker_id=route.broker_id, currency=route.currency, checkpoint=checkpoint):
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
    Broker: existing cash, funding-route destinations, transfer lanes into
    it (B3, project 67), and other SELL routes' proceeds at the same Broker. Only currencies with a known direct
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
    for lane in scenario.transfer_lanes:
        check_budget(checkpoint)
        if lane.destination_broker_id == broker_id:
            candidates.add(lane.currency)
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
    """

    decision_id: str
    key: str
    broker_id: str
    source_currency: str
    destination_currency: str
    entity_refs: tuple[EntityRef, ...]
    scope: str
    tie_break: tuple[str, ...]


def fx_decision_specs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[FxDecisionSpec, ...]:
    """Every FX decision of ``scenario``: one per Broker and ordered currency pair, sorted by (Broker, source, destination).

    A pair exists where a buy route of the Broker is quoted in the destination currency and the source is one of that buy's pool
    currencies (``buy_pool_currencies``: other currencies with cash possible on the Broker and a direct pair to the quote). Two buy
    routes on the same pair share the decision.

    The Rebalancer also converts into a cash cell that has a target or a minimum, with or without a purchase there (lot CR of
    project 67): its cash rule never lets converted money travel to another Broker (``transfer_relay_groups``), so a cell's
    money in another currency can only come from a conversion on that Broker. The sources are the cell's pool currencies, as for
    a buy quoted in the cell's currency.
    """
    pairs: set[tuple[str, str, str]] = set()
    destinations: list[tuple[str, str]] = []
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        destinations.append((route.broker_id, index.assets[route.asset_id].quote.price.currency))
    if scenario.product == "rebalancer":
        destinations += [(entry.broker_id, entry.currency) for entry in scenario.cash_entries if entry.weight > _EXACT_ZERO or entry.minimum is not None]
    for broker_id, quote_currency in destinations:
        check_budget(checkpoint)
        for currency in buy_pool_currencies(
            scenario,
            index,
            broker_id=broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            pairs.add((broker_id, currency, quote_currency))
    specs: list[FxDecisionSpec] = []
    for broker_id, source_currency, destination_currency in sorted(pairs):
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
            )
        )
    return tuple(specs)


@dataclass(frozen=True, slots=True)
class FxRelayGroup:
    """A currency of a Broker that both receives a conversion and gives one (V7).

    ``receiving`` are the decisions that convert into ``currency`` at the Broker, ``giving`` those that convert out of it.
    A plan may use one side at most: a conversion that lands in a currency and a second that leaves it again is a relay, which
    only burns cash (EUR to USD, then USD to CHF, then CHF to EUR). The engine never pays a buy through a chain
    (``buy_pool_currencies``), so no optimum needs one. ``key`` is ``len(broker):broker:CURRENCY``.
    """

    key: str
    broker_id: str
    currency: str
    receiving: tuple[FxDecisionSpec, ...]
    giving: tuple[FxDecisionSpec, ...]


def fx_relay_groups(specs: tuple[FxDecisionSpec, ...]) -> tuple[FxRelayGroup, ...]:
    """The relay groups of ``specs`` (``fx_decision_specs``), in canonical (Broker, currency) order."""
    receiving: dict[tuple[str, str], list[FxDecisionSpec]] = {}
    giving: dict[tuple[str, str], list[FxDecisionSpec]] = {}
    for spec in specs:
        receiving.setdefault((spec.broker_id, spec.destination_currency), []).append(spec)
        giving.setdefault((spec.broker_id, spec.source_currency), []).append(spec)
    return tuple(FxRelayGroup(key=f"{len(broker_id)}:{broker_id}:{currency}", broker_id=broker_id, currency=currency, receiving=tuple(receiving[(broker_id, currency)]), giving=tuple(giving[(broker_id, currency)])) for broker_id, currency in sorted(receiving.keys() & giving.keys()))


@dataclass(frozen=True, slots=True)
class TransferRelayGroup:
    """A Rebalancer cash cell (Broker × currency) that transfer lanes reach: the cash rule of lot CR, project 67.

    ``receiving`` are the decisions that bring money into the cell: the transfers in from other Brokers and the conversions into
    the currency on this Broker. ``giving`` are the transfers out. A plan uses one side at most:
    - R1, a cell that receives a conversion sends nothing to another Broker;
    - a cell does not both send and receive in one currency (the model keeps one signed balance per cell);
    - so a cell that sends receives nothing, and with its final balance never negative it sends only its own money (R2:
      converted money never travels).

    Every plan that keeps it can be carried out in a fixed order: transfers, conversions, purchases (specification §16).
    ``key`` is ``len(broker):broker:CURRENCY``, as ``FxRelayGroup``'s.
    """

    key: str
    broker_id: str
    currency: str
    receiving: tuple[str, ...]
    giving: tuple[str, ...]


def transfer_relay_groups(scenario: ExactPlannerScenario, specs: tuple[FxDecisionSpec, ...]) -> tuple[TransferRelayGroup, ...]:
    """The cash rule's groups, one per cell a lane leaves, in canonical (Broker, currency) order. The Rebalancer only: a PAC
    scenario has no cash rule, even with a lane a test sets by hand (D4 a)."""
    if scenario.product != "rebalancer":
        return ()
    receiving: dict[tuple[str, str], list[str]] = {}
    giving: dict[tuple[str, str], list[str]] = {}
    for lane in scenario.transfer_lanes:
        decision_id = exact_decision_id("broker_transfer", broker_transfer_key(lane.source_broker_id, lane.destination_broker_id, lane.currency))
        giving.setdefault((lane.source_broker_id, lane.currency), []).append(decision_id)
        receiving.setdefault((lane.destination_broker_id, lane.currency), []).append(decision_id)
    for spec in specs:
        if (spec.broker_id, spec.destination_currency) in giving:
            receiving.setdefault((spec.broker_id, spec.destination_currency), []).append(spec.decision_id)
    return tuple(
        TransferRelayGroup(
            key=f"{len(broker_id)}:{broker_id}:{currency}",
            broker_id=broker_id,
            currency=currency,
            receiving=tuple(sorted(receiving.get((broker_id, currency), ()))),
            giving=tuple(sorted(giving[(broker_id, currency)])),
        )
        for broker_id, currency in sorted(giving)
    )
