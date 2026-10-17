"""Economic events of the lots analysis: income and costs as FIFO engine inputs, their allocation to lots, and what is withheld when a rate is missing."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date as date_type
from decimal import Decimal
from typing import Sequence

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.portfolio import (
    EconomicAllocationGroupSchema,
    EconomicLotAllocationSchema,
    LotIncomeEventKind,
    LotIncomeEventSchema,
    TargetOperationAllocationSchema,
)
from backend.app.services.financial_math.fifo.models import EconomicAllocationGroup, EconomicEvent, FifoEngineResult, FifoInputTransaction
from backend.app.services.financial_math.lots.conversions import FxRateResolver

# FEE/TAX pools weighted by the controvalue of their trades: their split depends on the trades' rates.
_TRADE_WEIGHTED_RULES = frozenset({"SAME_DAY_TRADES", "SAME_DAY_MIXED_TRADES", "PREVIOUS_DAY_TRADES"})


_ECONOMIC_KIND = {"DIVIDEND": "income", "INTEREST": "income", "FEE": "fees", "TAX": "taxes"}


@dataclass(frozen=True, slots=True)
class WithheldEconomics:
    """The economic pools a missing rate leaves unknown, and what they withhold.

    A pool is degraded by its amount (one of its events has no rate) or by its split (a pool weighted
    by trades in different currencies, one of them without a rate). Every lot it reaches has that
    income, fee or tax unknown from the pool's date; an orphan pool leaves the asset's orphan total
    of its kind unknown. Pools are indexes into the engine's ``economic_allocation_groups``.
    """

    income_from: dict[int, date_type] = field(default_factory=dict)
    fees_from: dict[int, date_type] = field(default_factory=dict)
    taxes_from: dict[int, date_type] = field(default_factory=dict)
    amount_degraded: frozenset[int] = frozenset()
    split_degraded: frozenset[int] = frozenset()
    unconvertible_event_ids: frozenset[int] = frozenset()
    orphan_unknown: frozenset[str] = frozenset()

    def reaches(self, lot_id: int) -> bool:
        return lot_id in self.income_from or lot_id in self.fees_from or lot_id in self.taxes_from


NOTHING_WITHHELD = WithheldEconomics()


def build_income_economic_events(
    *,
    income_transactions: Sequence[Transaction],
    fx_resolver: FxRateResolver,
    asset_currency: str,
    target_currency: str,
) -> list[EconomicEvent]:
    """Build target-value-aware DIVIDEND/INTEREST events for the engine economic stage.

    FX is resolved here (the service owns FX I/O): each event carries the native amount and the
    amount converted to ``target_currency`` at the transaction date. Eligibility, pooling and
    pro-rata allocation are performed by the engine from the replayed fragments (D-1 semantics,
    broker scoped, transfer aware).
    """
    events: list[EconomicEvent] = []
    for tx in income_transactions:
        if tx.id is None or tx.asset_id is None:
            continue
        native_currency = tx.currency or asset_currency
        target_amount = _engine_target_amount(tx.amount, native_currency, tx.date, fx_resolver)
        events.append(
            EconomicEvent(
                transaction_id=tx.id,
                broker_id=tx.broker_id,
                asset_id=tx.asset_id,
                date=tx.date,
                economic_type="DIVIDEND" if tx.type == TransactionType.DIVIDEND else "INTEREST",
                native_amount=tx.amount,
                native_currency=native_currency,
                target_amount=target_amount,
                target_currency=target_currency,
            )
        )
    return events


def build_cost_economic_events(
    *,
    cost_transactions: Sequence[Transaction],
    fx_resolver: FxRateResolver,
    asset_currency: str,
    target_currency: str,
) -> list[EconomicEvent]:
    """Build target-value-aware FEE/TAX events for the engine economic stage.

    FX is resolved here (the service owns FX I/O): each event carries the native (negative)
    amount and the amount converted to ``target_currency`` at the transaction date. Pooling,
    matching (same-day/previous-day trades or income, holdings fallback) and orphan detection are
    performed by the engine.
    """
    events: list[EconomicEvent] = []
    for tx in cost_transactions:
        if tx.id is None or tx.asset_id is None or tx.amount is None:
            continue
        native_currency = tx.currency or asset_currency
        target_amount = _engine_target_amount(tx.amount, native_currency, tx.date, fx_resolver)
        events.append(
            EconomicEvent(
                transaction_id=tx.id,
                broker_id=tx.broker_id,
                asset_id=tx.asset_id,
                date=tx.date,
                economic_type="FEE" if tx.type == TransactionType.FEE else "TAX",
                native_amount=tx.amount,
                native_currency=native_currency,
                target_amount=target_amount,
                target_currency=target_currency,
            )
        )
    return events


def build_engine_transactions(
    transactions: Sequence[Transaction | FifoInputTransaction],
    fx_resolver: FxRateResolver,
    asset_currency: str,
    target_currency: str,
) -> list[FifoInputTransaction]:
    """Normalize transactions for the engine, attaching each trade's target controvalue.

    Only BUY/SELL carry ``target_amount`` (the FEE/TAX pooling weight, §3.5); other kinds keep it
    ``None``. The quantitative replay is unchanged — only the economic stage reads the target.
    """
    engine_transactions: list[FifoInputTransaction] = []
    for tx in transactions:
        base = FifoInputTransaction.from_transaction(tx)
        if tx.type in (TransactionType.BUY, TransactionType.SELL) and tx.amount is not None:
            native_currency = tx.currency or asset_currency
            target_amount = _engine_target_amount(tx.amount, native_currency, tx.date, fx_resolver)
            base = replace(base, target_amount=target_amount, target_currency=target_currency)
        engine_transactions.append(base)
    return engine_transactions


def extract_income_outputs(
    engine_result: FifoEngineResult,
    income_events: Sequence[EconomicEvent],
    withheld: WithheldEconomics = NOTHING_WITHHELD,
) -> tuple[dict[int, Decimal], dict[int, dict[date_type, Decimal]], list[LotIncomeEventSchema]]:
    """Derive the service-facing income views from the engine economic output.

    Returns ``(income_by_lot, income_prefix_by_lot, income_events_payload)``: cumulative income
    per lot (from the engine accumulators); a per-lot cumulative-by-date map for histories (from
    the audit groups, the shape of the closures' map in ``histories._closure_prefix``); and one
    ``LotIncomeEventSchema`` per income transaction carrying the shared eligible lot ids (plan
    v3 §11 chart markers), its amount None when it has no rate.
    """
    income_by_lot: dict[int, Decimal] = {lot_id: accumulator.gross_income for lot_id, accumulator in engine_result.economic_accumulators_by_lot.items() if accumulator.gross_income != Decimal("0")}

    per_lot_dated: dict[int, list[tuple[date_type, Decimal]]] = defaultdict(list)
    pool_lot_ids: dict[tuple[int, date_type, str, str | None, str], list[int]] = {}
    for group in engine_result.economic_allocation_groups:
        if group.economic_type not in ("DIVIDEND", "INTEREST"):
            continue
        eligible_ids: list[int] = []
        for operation in group.operation_allocations:
            for allocation in operation.lot_allocations:
                per_lot_dated[allocation.lot_id].append((group.date, allocation.target_amount))
                eligible_ids.append(allocation.lot_id)
        pool_lot_ids[(group.broker_id, group.date, group.economic_type, group.native_currency, group.target_currency)] = eligible_ids

    income_prefix_by_lot: dict[int, dict[date_type, Decimal]] = {}
    for lot_id, dated in per_lot_dated.items():
        running = Decimal("0")
        prefix: dict[date_type, Decimal] = {}
        for event_date, amount in sorted(dated, key=lambda item: item[0]):
            running += amount
            prefix[event_date] = running
        income_prefix_by_lot[lot_id] = prefix

    income_events_payload: list[LotIncomeEventSchema] = []
    for event in sorted(income_events, key=lambda item: (item.date, item.transaction_id)):
        eligible_ids = pool_lot_ids.get((event.broker_id, event.date, event.economic_type, event.native_currency, event.target_currency), [])
        income_events_payload.append(
            LotIncomeEventSchema(
                type=LotIncomeEventKind.DIVIDEND if event.economic_type == "DIVIDEND" else LotIncomeEventKind.INTEREST,
                date=event.date,
                broker_id=event.broker_id,
                transaction_id=event.transaction_id,
                amount=None if event.transaction_id in withheld.unconvertible_event_ids else event.target_amount,
                lot_ids=list(eligible_ids),
            )
        )
    return income_by_lot, income_prefix_by_lot, income_events_payload


def extract_cost_outputs(
    engine_result: FifoEngineResult,
) -> tuple[dict[int, Decimal], dict[int, Decimal], dict[int, dict[date_type, Decimal]], dict[int, dict[date_type, Decimal]]]:
    """Derive the service-facing FEE/TAX views from the engine economic output.

    Returns ``(fees_by_lot, taxes_by_lot, fees_prefix_by_lot, taxes_prefix_by_lot)``: cumulative
    allocated FEE/TAX per lot (from the engine accumulators, positive magnitude) plus per-lot
    cumulative-by-date maps for the net history series (from the audit groups, same shape as
    ``income_prefix_by_lot``).
    """
    fees_by_lot: dict[int, Decimal] = {lot_id: accumulator.allocated_fees for lot_id, accumulator in engine_result.economic_accumulators_by_lot.items() if accumulator.allocated_fees != Decimal("0")}
    taxes_by_lot: dict[int, Decimal] = {lot_id: accumulator.allocated_taxes for lot_id, accumulator in engine_result.economic_accumulators_by_lot.items() if accumulator.allocated_taxes != Decimal("0")}

    fees_dated: dict[int, list[tuple[date_type, Decimal]]] = defaultdict(list)
    taxes_dated: dict[int, list[tuple[date_type, Decimal]]] = defaultdict(list)
    for group in engine_result.economic_allocation_groups:
        if group.economic_type == "FEE":
            sink = fees_dated
        elif group.economic_type == "TAX":
            sink = taxes_dated
        else:
            continue
        for operation in group.operation_allocations:
            for allocation in operation.lot_allocations:
                sink[allocation.lot_id].append((group.date, allocation.target_amount))

    def _prefix(dated: dict[int, list[tuple[date_type, Decimal]]]) -> dict[int, dict[date_type, Decimal]]:
        out: dict[int, dict[date_type, Decimal]] = {}
        for lot_id, entries in dated.items():
            running = Decimal("0")
            prefix: dict[date_type, Decimal] = {}
            for event_date, amount in sorted(entries, key=lambda item: item[0]):
                running += amount
                prefix[event_date] = running
            out[lot_id] = prefix
        return out

    return fees_by_lot, taxes_by_lot, _prefix(fees_dated), _prefix(taxes_dated)


def map_economic_groups(groups: Sequence[EconomicAllocationGroup], withheld: WithheldEconomics = NOTHING_WITHHELD) -> list[EconomicAllocationGroupSchema]:
    """Map engine economic audit dataclasses to their inline-response Pydantic mirrors.

    A pool with an event without a rate has no target figure; a pool split by trades in different
    currencies, one without a rate, has no operation weight and no per-lot amount. Native totals stay.
    """
    mapped: list[EconomicAllocationGroupSchema] = []
    for index, group in enumerate(groups):
        amount_unknown = index in withheld.amount_degraded
        split_unknown = index in withheld.split_degraded
        mapped.append(
            EconomicAllocationGroupSchema(
                economic_type=group.economic_type,
                asset_id=group.asset_id,
                broker_id=group.broker_id,
                date=group.date,
                native_currency=group.native_currency,
                target_currency=group.target_currency,
                rule=group.rule,
                source_transaction_ids=list(group.source_transaction_ids),
                native_pool_total=group.native_pool_total,
                target_pool_total=None if amount_unknown else group.target_pool_total,
                native_orphan=group.native_orphan,
                target_orphan=None if amount_unknown else group.target_orphan,
                operation_allocations=[
                    TargetOperationAllocationSchema(
                        context=operation.context,
                        operation_transaction_id=operation.operation_transaction_id,
                        weight=None if split_unknown else operation.weight,
                        lot_allocations=[
                            EconomicLotAllocationSchema(
                                lot_id=allocation.lot_id,
                                weight=allocation.weight,
                                native_amount=None if split_unknown else allocation.native_amount,
                                target_amount=None if amount_unknown or split_unknown else allocation.target_amount,
                            )
                            for allocation in operation.lot_allocations
                        ],
                    )
                    for operation in group.operation_allocations
                ],
            )
        )
    return mapped


def _engine_target_amount(
    amount: Decimal,
    currency: str,
    as_of_date: date_type,
    fx_resolver: FxRateResolver,
) -> Decimal:
    """The target amount handed to the FIFO engine for an economic event or a trade weight.

    Without a rate the native amount is handed over only as a placeholder, so the engine can place
    the event: every figure of the pools it reaches is withheld (``withheld_economics``), and the
    missing rate is recorded by the resolver and reported.
    """
    return fx_resolver.convert(amount, currency, as_of_date) or amount


def withheld_economics(
    groups: Sequence[EconomicAllocationGroup],
    *,
    unconvertible_event_ids: set[int],
    unconvertible_trade_ids: set[int],
    trade_currency_by_id: dict[int, str | None],
) -> WithheldEconomics:
    """Find the pools a missing rate degrades, and the lots they leave unknown from their date."""
    unknown_from: dict[str, dict[int, date_type]] = {"income": {}, "fees": {}, "taxes": {}}
    amount_degraded: set[int] = set()
    split_degraded: set[int] = set()
    orphan_unknown: set[str] = set()
    for index, group in enumerate(groups):
        if unconvertible_event_ids.intersection(group.source_transaction_ids):
            amount_degraded.add(index)
        weighting_trades = {operation.operation_transaction_id for operation in group.operation_allocations if operation.operation_transaction_id is not None}
        if group.rule in _TRADE_WEIGHTED_RULES and weighting_trades & unconvertible_trade_ids and len({trade_currency_by_id.get(trade_id) for trade_id in weighting_trades}) > 1:
            split_degraded.add(index)
        if index not in amount_degraded and index not in split_degraded:
            continue
        kind = _ECONOMIC_KIND[group.economic_type]
        if not group.operation_allocations:
            orphan_unknown.add(kind)
        for operation in group.operation_allocations:
            for allocation in operation.lot_allocations:
                previous = unknown_from[kind].get(allocation.lot_id)
                unknown_from[kind][allocation.lot_id] = group.date if previous is None else min(previous, group.date)
    return WithheldEconomics(
        income_from=unknown_from["income"],
        fees_from=unknown_from["fees"],
        taxes_from=unknown_from["taxes"],
        amount_degraded=frozenset(amount_degraded),
        split_degraded=frozenset(split_degraded),
        unconvertible_event_ids=frozenset(unconvertible_event_ids),
        orphan_unknown=frozenset(orphan_unknown),
    )
