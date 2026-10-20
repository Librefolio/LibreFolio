"""Histories of the lots analysis: performance, value, return and price of each lot over time, and the per-day snapshots they are built from."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Callable, Sequence

from backend.app.db.models import Transaction
from backend.app.schemas.portfolio import (
    LotPriceHistoryPoint,
    LotReturnHistoryPoint,
    LotValueHistoryPoint,
    MarketPriceHistoryPoint,
    PerformanceHistoryPoint,
)
from backend.app.services.financial_math.fifo.models import FifoEngineResult, FifoInputTransaction, FifoLot, FragmentInterval, LotClosure
from backend.app.services.financial_math.lots.conversions import ConvertedClosure, FxRateResolver, convert_closure
from backend.app.services.financial_math.lots.economic_events import NOTHING_WITHHELD, WithheldEconomics
from backend.app.services.financial_math.lots.prices import opening_reference_price
from backend.app.services.financial_math.lots.scope_boundary import BoundaryLeg
from backend.app.services.financial_math.lots.summary import lot_value, residual_cost
from backend.app.services.financial_math.price_marks import AssetPriceSeries
from backend.app.services.financial_math.returns import CashFlowInput, NAVSnapshot, calculate_simple_roi_series, calculate_twrr_series
from backend.app.services.financial_math.valuation import compute_holding_value


@dataclass(frozen=True, slots=True)
class PerformanceSourceContext:
    # The scope's rows, each transfer leg read at the scope's edge (``scope_boundary``) and named in ``boundary_legs``.
    transactions: Sequence[Transaction | FifoInputTransaction]
    engine_result: FifoEngineResult
    lots_by_id: dict[int, FifoLot]
    fragments_by_lot: dict[int, list[FragmentInterval]]
    closures_by_lot: dict[int, list[LotClosure]]
    tx_by_id: dict[int, Transaction | FifoInputTransaction]
    boundary_legs: Mapping[int, BoundaryLeg] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _LotValueBasis:
    """What a lot's value series needs, in the target currency."""

    original_cost: Decimal
    # A short's cumulative proceeds; 0 for a long, whose proceeds come from its closures.
    short_proceeds: Decimal
    last_date: date_type
    # Running sums by close date: a long lot's proceeds, a short lot's buy-back costs (each empty for the other).
    proceeds_by_day: dict[date_type, Decimal]
    buybacks_by_day: dict[date_type, Decimal]


def build_performance_history(  # noqa: C901 — cash-flow collection loops with sequential guard filters
    *,
    scope_broker_ids: Sequence[int],
    history_dates: Sequence[date_type],
    market_prices: dict[date_type, Decimal | None],
    asset_currency: str,
    fx_resolver: FxRateResolver,
    context: PerformanceSourceContext,
    quote_base_quantity: int,
    at_cost_until: date_type | None,
) -> list[PerformanceHistoryPoint]:
    """ROI and TWRR of the asset's lots in the scope, day by day.

    A day with a mark values the open fragments at it. A day with no observation on or before it (``<= at_cost_until``)
    values them at cost, as the value history and the Dashboard do (J-17, J-33), and a transfer that day moves the cost
    of its units; any other day without a mark has no point.
    """
    scope_set = set(scope_broker_ids)
    scoped_fragments_by_lot = {lot_id: [fragment for fragment in fragments if _fragment_in_scope(fragment, scope_set)] for lot_id, fragments in context.fragments_by_lot.items()}

    def at_cost(day: date_type) -> bool:
        return at_cost_until is not None and day <= at_cost_until

    nav_snapshots: list[NAVSnapshot] = []
    for current_date in history_dates:
        market_price = market_prices.get(current_date)
        if market_price is not None:
            nav_amount: Decimal | None = sum((_open_value_on_date(fragments, market_price, current_date, quote_base_quantity) for fragments in scoped_fragments_by_lot.values() if fragments), Decimal("0"))
        elif at_cost(current_date):
            nav_amount = _nav_at_cost(scoped_fragments_by_lot, context.lots_by_id, fx_resolver, current_date)
        else:
            nav_amount = None
        if nav_amount is not None:
            nav_snapshots.append(NAVSnapshot(date=current_date, nav=nav_amount))

    cash_flows: list[CashFlowInput] = []
    invalid_external_flow_from: date_type | None = None

    for tx in sorted(context.transactions, key=lambda row: (row.date, row.id or 0)):
        if tx.broker_id not in scope_set:
            continue
        # A transfer leg read at the scope's edge moves its market value of the day across the scope, as the transfers
        # whose two legs this replay holds do (below): money in for a leg that arrives, out for one that leaves (J-10).
        boundary_leg = context.boundary_legs.get(tx.id) if tx.id is not None else None
        if boundary_leg is not None:
            leg_price = market_prices.get(tx.date)
            if leg_price is not None:
                leg_value: Decimal | None = compute_holding_value(abs(tx.quantity), leg_price, quote_base_quantity)
            elif at_cost(tx.date):
                # On a day valued at cost the leg moves the cost of its units (J-33): an arrival its own cost basis, a
                # departure, handed over at its own cost (J-10), the cost of the pieces it closes.
                leg_value = _boundary_leg_cost(tx, boundary_leg.direction, context, fx_resolver, asset_currency)
            else:
                leg_value = None
            if leg_value is None:
                invalid_external_flow_from = tx.date if invalid_external_flow_from is None else min(invalid_external_flow_from, tx.date)
            elif leg_value != Decimal("0"):
                cash_flows.append(CashFlowInput(date=tx.date, amount=-leg_value if boundary_leg.direction == "IN" else leg_value))
            continue
        tx_type = str(getattr(tx.type, "value", tx.type))
        if tx_type == "BUY":
            buy_amount = fx_resolver.convert(abs(tx.amount), tx.currency or asset_currency, tx.date)
            if buy_amount is None:
                invalid_external_flow_from = tx.date if invalid_external_flow_from is None else min(invalid_external_flow_from, tx.date)
            else:
                cash_flows.append(CashFlowInput(date=tx.date, amount=-buy_amount))
            continue
        # An ADJUSTMENT with a cost moves that cost across the scope: money brought in by an ADJUSTMENT-in, money taken
        # out by one that hands units over at cost (its signed cost is negative). An ADJUSTMENT-out without a cost basis
        # is a quantity correction and never a flow.
        if tx_type == "ADJUSTMENT" and (tx.quantity > 0 or tx.cost_basis_override not in (None, Decimal("0"))) and _adjustment_native_cost(tx, asset_currency) is not None:
            adjustment_cost = adjustment_cash_flow_cost(tx=tx, asset_currency=asset_currency, fx_resolver=fx_resolver)
            if adjustment_cost is None:
                invalid_external_flow_from = tx.date if invalid_external_flow_from is None else min(invalid_external_flow_from, tx.date)
            elif adjustment_cost != Decimal("0"):
                cash_flows.append(CashFlowInput(date=tx.date, amount=-adjustment_cost))

    for closure in sorted(context.engine_result.closures, key=lambda row: (row.close_date, row.transaction_id, row.lot_id)):
        if closure.close_reason != "SELL":
            continue
        lot = context.lots_by_id.get(closure.lot_id)
        tx = context.tx_by_id.get(closure.transaction_id)
        if lot is None or tx is None or lot.direction != "LONG" or tx.broker_id not in scope_set:
            continue
        proceeds = convert_closure(closure, lot, fx_resolver).proceeds
        if proceeds is None:
            invalid_external_flow_from = closure.close_date if invalid_external_flow_from is None else min(invalid_external_flow_from, closure.close_date)
            continue
        cash_flows.append(CashFlowInput(date=closure.close_date, amount=proceeds))

    seen_external_transfers: set[tuple[int, str]] = set()
    for event in context.engine_result.classified_events:
        if event.kind not in {"TRANSFER_DEPART", "TRANSFER_ARRIVE"}:
            continue
        pair_id = event.pair_id or event.transaction_id
        dedupe_key = (pair_id, event.kind)
        if dedupe_key in seen_external_transfers:
            continue
        seen_external_transfers.add(dedupe_key)
        source_in_scope = event.source_broker_id in scope_set
        destination_in_scope = event.destination_broker_id in scope_set
        if source_in_scope == destination_in_scope:
            continue
        if source_in_scope and event.kind != "TRANSFER_DEPART":
            continue
        if destination_in_scope and event.kind != "TRANSFER_ARRIVE":
            continue
        market_price = market_prices.get(event.date)
        if market_price is not None:
            amount: Decimal | None = compute_holding_value(event.quantity or Decimal("0"), market_price, quote_base_quantity)
        elif at_cost(event.date):
            amount = _moved_cost(pair_id, context, fx_resolver)  # J-33: the cost of the pieces moved, on a day at cost
        else:
            amount = None
        if amount is None:
            invalid_external_flow_from = event.date if invalid_external_flow_from is None else min(invalid_external_flow_from, event.date)
            continue
        cash_flows.append(CashFlowInput(date=event.date, amount=amount if source_in_scope else -amount))

    if invalid_external_flow_from is not None:
        nav_snapshots = [snapshot for snapshot in nav_snapshots if snapshot.date < invalid_external_flow_from]
        cash_flows = [flow for flow in cash_flows if flow.date < invalid_external_flow_from]

    if nav_snapshots:
        first_nav_date = nav_snapshots[0].date
        carried_cash_flow = sum((flow.amount for flow in cash_flows if flow.date < first_nav_date), Decimal("0"))
        cash_flows = [flow for flow in cash_flows if flow.date >= first_nav_date]
        if carried_cash_flow != Decimal("0"):
            cash_flows.insert(0, CashFlowInput(date=first_nav_date, amount=carried_cash_flow))

    first_cash_flow_date = min((flow.date for flow in cash_flows), default=None)
    roi_map: dict[date_type, Decimal] = {}
    twrr_map: dict[date_type, Decimal] = {}
    if first_cash_flow_date is not None and nav_snapshots:
        roi_map = {point.date: point.roi for point in calculate_simple_roi_series(nav_snapshots, cash_flows) if point.date >= first_cash_flow_date}
        twrr_map = {point.date: point.twrr for point in calculate_twrr_series(nav_snapshots, cash_flows) if point.date >= first_cash_flow_date}

    return [
        PerformanceHistoryPoint(
            date=current_date,
            roi=None if invalid_external_flow_from is not None and current_date >= invalid_external_flow_from else roi_map.get(current_date),
            twrr=None if invalid_external_flow_from is not None and current_date >= invalid_external_flow_from else twrr_map.get(current_date),
        )
        for current_date in history_dates
    ]


def _cost_at_opening(lot: FifoLot | None, quantity: Decimal, fx_resolver: FxRateResolver) -> Decimal | None:
    """What ``quantity`` units of a LONG ``lot`` are worth on a day valued at cost: their share of the lot's cost,
    converted at its opening date. None for a SHORT or unknown lot, a lot of no quantity, or a cost with no rate."""
    if lot is None or lot.direction != "LONG" or lot.original_quantity == Decimal("0"):
        return None
    return residual_cost(fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date), quantity, lot.original_quantity)


def _nav_at_cost(scoped_fragments_by_lot: Mapping[int, Sequence[FragmentInterval]], lots_by_id: Mapping[int, FifoLot], fx_resolver: FxRateResolver, current_date: date_type) -> Decimal | None:
    """The in-scope open fragments on ``current_date`` at cost (``_cost_at_opening``); None when one of them cannot be
    valued that way, so the day has no point rather than a partial one."""
    nav = Decimal("0")
    for lot_id, fragments in scoped_fragments_by_lot.items():
        open_quantity = _open_quantity_on_date(fragments, current_date)
        if open_quantity == Decimal("0"):
            continue
        cost = _cost_at_opening(lots_by_id.get(lot_id), open_quantity, fx_resolver)
        if cost is None:
            return None
        nav += cost
    return nav


def _boundary_leg_cost(tx: Transaction | FifoInputTransaction, direction: str, context: PerformanceSourceContext, fx_resolver: FxRateResolver, asset_currency: str) -> Decimal | None:
    """The money a transfer leg read at the scope's edge moves on a day valued at cost; None when it is unknown.

    An arrival brings its own cost basis, as any ADJUSTMENT-in (none: no money, its lot counts 0 at cost). A departure is
    handed over at its own cost (J-10): the cost of the pieces it closes, exactly what the NAV at cost loses.
    """
    if direction == "IN":
        if _adjustment_native_cost(tx, asset_currency) is None:
            return Decimal("0")
        return adjustment_cash_flow_cost(tx=tx, asset_currency=asset_currency, fx_resolver=fx_resolver)
    total = Decimal("0")
    for closure in context.engine_result.closures:
        if closure.transaction_id != tx.id:
            continue
        cost = _cost_at_opening(context.lots_by_id.get(closure.lot_id), closure.quantity, fx_resolver)
        if cost is None:
            return None
        total += cost
    return total


def _moved_cost(pair_id: int, context: PerformanceSourceContext, fx_resolver: FxRateResolver) -> Decimal | None:
    """The cost of the pieces a transfer pair moved, valued at cost (``_cost_at_opening``); None when unknown.

    Each lot moves one piece, whose first fragment (``lot:{lot}/transfer:{pair}/transit`` or ``.../to:{broker}``) holds
    its quantity.
    """
    marker = f"/transfer:{pair_id}/"
    first_piece: dict[int, FragmentInterval] = {}
    for fragment in context.engine_result.fragment_intervals:
        if marker in fragment.fragment_id and (fragment.lot_id not in first_piece or fragment.start_date < first_piece[fragment.lot_id].start_date):
            first_piece[fragment.lot_id] = fragment
    if not first_piece:
        return None
    total = Decimal("0")
    for lot_id, fragment in first_piece.items():
        cost = _cost_at_opening(context.lots_by_id.get(lot_id), fragment.quantity, fx_resolver)
        if cost is None:
            return None
        total += cost
    return total


def known_realized_pnl(lot: FifoLot, closures: Sequence[LotClosure], fx_resolver: FxRateResolver) -> Decimal | None:
    """Realized P&L in the target currency, each closure's legs at their own dates; None when one has no rate."""
    total = Decimal("0")
    for closure in closures:
        realized = convert_closure(closure, lot, fx_resolver).realized_pnl
        if realized is None:
            return None
        total += realized
    return total


def known_cumulative_proceeds(lot: FifoLot, closures: Sequence[LotClosure], fx_resolver: FxRateResolver) -> Decimal | None:
    """Cumulative proceeds in the target currency; None when they, or one closure's, have no rate.

    A long lot's are its closures', each in its own currency at its date; a short lot's are its opening sale's.
    """
    if lot.direction == "SHORT":
        return fx_resolver.convert(lot.cumulative_proceeds, lot.currency, lot.opening_date)
    total = Decimal("0")
    for closure in closures:
        converted = convert_closure(closure, lot, fx_resolver).proceeds
        if converted is None:
            return None
        total += converted
    return total


def known_buyback_cost(lot: FifoLot, closures: Sequence[LotClosure], fx_resolver: FxRateResolver) -> Decimal | None:
    """What a short lot's closing purchases cost in the target currency, each at its date; 0 for a long lot.

    None when one of them has no rate. A short lot's P&L is its opening proceeds minus these minus its open value.
    """
    if lot.direction != "SHORT":
        return Decimal("0")
    total = Decimal("0")
    for closure in closures:
        cost = convert_closure(closure, lot, fx_resolver).cost
        if cost is None:
            return None
        total += cost
    return total


def build_value_history(
    *,
    selected_ids: Sequence[int],
    lots_by_id: dict[int, FifoLot],
    fragments_by_lot: dict[int, list[FragmentInterval]],
    closures_by_lot: dict[int, list[LotClosure]],
    market_prices: dict[date_type, Decimal | None],
    history_dates: Sequence[date_type],
    fx_resolver: FxRateResolver,
    income_prefix_by_lot: dict[int, dict[date_type, Decimal]],
    fees_prefix_by_lot: dict[int, dict[date_type, Decimal]],
    taxes_prefix_by_lot: dict[int, dict[date_type, Decimal]],
    at_cost_until: date_type | None,
    quote_base_quantity: int,
    withheld: WithheldEconomics = NOTHING_WITHHELD,
) -> list[LotValueHistoryPoint]:
    points: list[LotValueHistoryPoint] = []
    for lot_id in selected_ids:
        lot = lots_by_id[lot_id]
        basis = _lot_value_basis(lot, closures_by_lot.get(lot_id, []), history_dates[-1], fx_resolver)
        if basis is None:
            continue
        income_prefix = income_prefix_by_lot.get(lot_id, {})
        fees_prefix = fees_prefix_by_lot.get(lot_id, {})
        taxes_prefix = taxes_prefix_by_lot.get(lot_id, {})
        fragments = fragments_by_lot.get(lot_id, [])
        for current_date in history_dates:
            if current_date < lot.opening_date or current_date > basis.last_date:
                continue
            snapshot = _lot_snapshot_on_date(
                lot=lot,
                fragments=fragments,
                basis=basis,
                market_price=market_prices.get(current_date),
                current_date=current_date,
                at_cost=at_cost_until is not None and current_date <= at_cost_until,
                quote_base_quantity=quote_base_quantity,
            )
            if snapshot is None:
                continue
            open_value, proceeds, total_value, pnl = snapshot
            income, allocated_fees, allocated_taxes = _economics_on_date(lot_id, current_date, income_prefix, fees_prefix, taxes_prefix, withheld)
            points.append(
                LotValueHistoryPoint(
                    lot_id=lot_id,
                    date=current_date,
                    open_value=open_value,
                    proceeds=proceeds,
                    total_value=total_value,
                    original_cost=basis.original_cost,
                    pnl=pnl,
                    income=income,
                    allocated_fees=allocated_fees,
                    allocated_taxes=allocated_taxes,
                    net_pnl=pnl - allocated_fees - allocated_taxes if allocated_fees is not None and allocated_taxes is not None else None,
                )
            )
    return points


def build_return_history(
    *,
    selected_ids: Sequence[int],
    lots_by_id: dict[int, FifoLot],
    fragments_by_lot: dict[int, list[FragmentInterval]],
    market_prices: dict[date_type, Decimal | None],
    price_series: AssetPriceSeries,
    fx_resolver: FxRateResolver,
    history_dates: Sequence[date_type],
    closures_by_lot: dict[int, list[LotClosure]],
    income_prefix_by_lot: dict[int, dict[date_type, Decimal]],
    fees_prefix_by_lot: dict[int, dict[date_type, Decimal]],
    taxes_prefix_by_lot: dict[int, dict[date_type, Decimal]],
    at_cost_until: date_type | None,
    quote_base_quantity: int,
    withheld: WithheldEconomics = NOTHING_WITHHELD,
) -> list[LotReturnHistoryPoint]:
    points: list[LotReturnHistoryPoint] = []
    for lot_id in selected_ids:
        lot = lots_by_id[lot_id]
        raw_reference_price, raw_reference_currency, reference_date, reference_price_source = opening_reference_price(lot, price_series, quote_base_quantity)
        converted_reference = fx_resolver.convert(raw_reference_price, raw_reference_currency, reference_date)
        basis = _lot_value_basis(lot, closures_by_lot.get(lot_id, []), history_dates[-1], fx_resolver)
        if basis is None:
            continue
        income_prefix = income_prefix_by_lot.get(lot_id, {})
        fees_prefix = fees_prefix_by_lot.get(lot_id, {})
        taxes_prefix = taxes_prefix_by_lot.get(lot_id, {})
        fragments = fragments_by_lot.get(lot_id, [])
        for current_date in history_dates:
            if current_date < lot.opening_date or current_date > basis.last_date:
                continue
            market_price = market_prices.get(current_date)
            snapshot = _lot_snapshot_on_date(
                lot=lot,
                fragments=fragments,
                basis=basis,
                market_price=market_price,
                current_date=current_date,
                at_cost=at_cost_until is not None and current_date <= at_cost_until,
                quote_base_quantity=quote_base_quantity,
            )
            if snapshot is None:
                continue
            _open_value, _proceeds, total_value, _pnl = snapshot
            relative_return = None
            if market_price is not None and converted_reference not in (None, Decimal("0")):
                relative_return = (market_price / converted_reference) - Decimal("1")
            income, allocated_fees, allocated_taxes = _economics_on_date(lot_id, current_date, income_prefix, fees_prefix, taxes_prefix, withheld)
            # A short's total value is its P&L: it is read against the notional sold, as the lot summary reads
            # total P&L / opening value, so a short at break-even returns 0, not −100%.
            value_for_return = total_value if lot.direction == "LONG" else basis.original_cost + total_value
            total_return, net_total_return = _lot_returns(basis.original_cost, value_for_return, income, allocated_fees, allocated_taxes)
            points.append(
                LotReturnHistoryPoint(
                    lot_id=lot_id,
                    date=current_date,
                    total_return=total_return,
                    relative_return=relative_return,
                    reference_price_source=reference_price_source if relative_return is not None else None,
                    income=income,
                    net_total_return=net_total_return,
                )
            )
    return points


def _value_snapshot_on_date(
    *,
    lot: FifoLot,
    fragments: Sequence[FragmentInterval],
    proceeds_by_day: dict[date_type, Decimal],
    buybacks_by_day: dict[date_type, Decimal],
    market_price: Decimal,
    current_date: date_type,
    converted_original_cost: Decimal,
    converted_short_proceeds: Decimal,
    quote_base_quantity: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    open_value = _open_value_on_date(fragments, market_price, current_date, quote_base_quantity)
    if lot.direction == "LONG":
        proceeds = _prefix_value_on_date(proceeds_by_day, current_date)
        total_value, pnl = lot_value(lot.direction, open_value, proceeds, Decimal("0"), converted_original_cost)
    else:
        proceeds = converted_short_proceeds
        total_value, pnl = lot_value(lot.direction, open_value, proceeds, _prefix_value_on_date(buybacks_by_day, current_date), converted_original_cost)
    return open_value, proceeds, total_value, pnl


def build_price_history(
    *,
    selected_ids: Sequence[int],
    lots_by_id: dict[int, FifoLot],
    estimated_market_prices: dict[date_type, tuple[Decimal, bool]],
    history_dates: Sequence[date_type],
    target_currency: str,
    closures_by_lot: dict[int, list[LotClosure]],
) -> list[LotPriceHistoryPoint]:
    points: list[LotPriceHistoryPoint] = []
    for lot_id in selected_ids:
        lot = lots_by_id[lot_id]
        last_date = lot_history_end_date(lot, closures_by_lot.get(lot_id, []), history_dates[-1])
        for current_date in history_dates:
            if current_date < lot.opening_date or current_date > last_date:
                continue
            entry = estimated_market_prices.get(current_date)
            if entry is None:
                continue
            market_price, is_estimated = entry
            points.append(LotPriceHistoryPoint(lot_id=lot_id, date=current_date, market_price=market_price, currency=target_currency, estimated=is_estimated))
    return points


def build_market_price_history(
    *,
    estimated_market_prices: dict[date_type, tuple[Decimal, bool]],
    history_dates: Sequence[date_type],
    target_currency: str,
) -> list[MarketPriceHistoryPoint]:
    """The asset's market price on each history date that has a converted mark, whatever lots are open (Y-30).

    The same marks as ``build_price_history``, once a day instead of once per lot alive that day: the chart's price line
    keeps its days without a lot, and a FAILED replay, which withholds every lot, keeps the line. A date without a mark
    (no observation on or before it, or no rate to the target currency) has no point.
    """
    points: list[MarketPriceHistoryPoint] = []
    for current_date in history_dates:
        entry = estimated_market_prices.get(current_date)
        if entry is None:
            continue
        market_price, is_estimated = entry
        points.append(MarketPriceHistoryPoint(date=current_date, market_price=market_price, currency=target_currency, estimated=is_estimated))
    return points


def group_fragments(fragments: Sequence[FragmentInterval]) -> dict[int, list[FragmentInterval]]:
    grouped: dict[int, list[FragmentInterval]] = defaultdict(list)
    for fragment in fragments:
        grouped[fragment.lot_id].append(fragment)
    return grouped


def group_closures(closures: Sequence[LotClosure]) -> dict[int, list[LotClosure]]:
    grouped: dict[int, list[LotClosure]] = defaultdict(list)
    for closure in closures:
        grouped[closure.lot_id].append(closure)
    return grouped


def lot_history_end_date(
    lot: FifoLot,
    closures: Sequence[LotClosure],
    fallback_end: date_type,
    *,
    extend_closed: bool = False,
) -> date_type:
    if extend_closed or lot.open_quantity > 0:
        return fallback_end
    if not closures:
        return lot.opening_date
    return max(closure.close_date for closure in closures)


def _lot_value_basis(lot: FifoLot, closures: Sequence[LotClosure], history_end: date_type, fx_resolver: FxRateResolver) -> _LotValueBasis | None:
    """The converted cost, proceeds and last date of a lot's value series; None when the cost has no rate.

    Without its cost (or, for a short, its proceeds) in the target currency the lot gets no point: its P&L
    would mix currencies. The series stops the day before the first closure whose proceeds (a long lot) or
    buy-back cost (a short lot) has no rate. Same rule as the average-cost lines: a point that cannot be
    computed is omitted.
    """
    original_cost = fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date)
    short_proceeds = fx_resolver.convert(lot.cumulative_proceeds, lot.currency, lot.opening_date) if lot.direction == "SHORT" else Decimal("0")
    if original_cost is None or short_proceeds is None:
        return None
    last_date = lot_history_end_date(lot, closures, history_end, extend_closed=True)
    proceeds_by_day: dict[date_type, Decimal] = {}
    buybacks_by_day: dict[date_type, Decimal] = {}
    if lot.direction == "LONG":
        proceeds_by_day, unknown_from = _closure_prefix(lot, closures, fx_resolver, lambda converted: converted.proceeds)
    else:
        buybacks_by_day, unknown_from = _closure_prefix(lot, closures, fx_resolver, lambda converted: converted.cost)
    if unknown_from is not None:
        last_date = min(last_date, unknown_from - timedelta(days=1))
    return _LotValueBasis(original_cost=original_cost, short_proceeds=short_proceeds, last_date=last_date, proceeds_by_day=proceeds_by_day, buybacks_by_day=buybacks_by_day)


def _lot_snapshot_on_date(
    *,
    lot: FifoLot,
    fragments: Sequence[FragmentInterval],
    basis: _LotValueBasis,
    market_price: Decimal | None,
    current_date: date_type,
    at_cost: bool,
    quote_base_quantity: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
    """(open value, proceeds, total value, P&L) of a lot on a day; None when that day cannot be valued.

    With a market price, the open quantity at that price. Without one, a fully closed lot is worth its
    proceeds and a LONG lot on a day with no observation on or before it (``at_cost``) is estimated at cost,
    as the Dashboard values a holding (J-17); any other day — a price without a rate — is not valued.
    """
    if market_price is not None:
        return _value_snapshot_on_date(
            lot=lot,
            fragments=fragments,
            proceeds_by_day=basis.proceeds_by_day,
            buybacks_by_day=basis.buybacks_by_day,
            market_price=market_price,
            current_date=current_date,
            converted_original_cost=basis.original_cost,
            converted_short_proceeds=basis.short_proceeds,
            quote_base_quantity=quote_base_quantity,
        )
    open_quantity = _open_quantity_on_date(fragments, current_date)
    if open_quantity == Decimal("0"):
        open_value = Decimal("0")
        if lot.direction == "LONG":
            proceeds = _prefix_value_on_date(basis.proceeds_by_day, current_date)
            total_value, pnl = lot_value(lot.direction, open_value, proceeds, Decimal("0"), basis.original_cost)
            return open_value, proceeds, total_value, pnl
        total_value, pnl = lot_value(lot.direction, open_value, basis.short_proceeds, _prefix_value_on_date(basis.buybacks_by_day, current_date), basis.original_cost)
        return open_value, basis.short_proceeds, total_value, pnl
    if at_cost and lot.direction == "LONG" and lot.original_quantity != Decimal("0"):
        open_value = residual_cost(basis.original_cost, open_quantity, lot.original_quantity)
        proceeds = _prefix_value_on_date(basis.proceeds_by_day, current_date)
        total_value, pnl = lot_value(lot.direction, open_value, proceeds, Decimal("0"), basis.original_cost)
        return open_value, proceeds, total_value, pnl
    return None


def _closure_prefix(
    lot: FifoLot,
    closures: Sequence[LotClosure],
    fx_resolver: FxRateResolver,
    leg: Callable[[ConvertedClosure], Decimal | None],
) -> tuple[dict[date_type, Decimal], date_type | None]:
    """The running sum of one converted leg of the closures by close date, and the first close date it has no rate.

    From that date the lot's value is unknown: the prefix stops there instead of adding unconverted money.
    """
    running = Decimal("0")
    out: dict[date_type, Decimal] = {}
    for closure in sorted(closures, key=lambda item: (item.close_date, item.transaction_id, item.lot_id)):
        converted = leg(convert_closure(closure, lot, fx_resolver))
        if converted is None:
            return out, closure.close_date
        running += converted
        out[closure.close_date] = running
    return out, None


def _prefix_value_on_date(values_by_date: dict[date_type, Decimal], query_date: date_type) -> Decimal:
    if not values_by_date:
        return Decimal("0")
    eligible_dates = [current_date for current_date in values_by_date if current_date <= query_date]
    if not eligible_dates:
        return Decimal("0")
    return values_by_date[max(eligible_dates)]


def _open_value_on_date(fragments: Sequence[FragmentInterval], market_price: Decimal, query_date: date_type, quote_base_quantity: int) -> Decimal:
    return compute_holding_value(_open_quantity_on_date(fragments, query_date), market_price, quote_base_quantity)


def _open_quantity_on_date(fragments: Sequence[FragmentInterval], query_date: date_type) -> Decimal:
    return sum((fragment.quantity for fragment in fragments if fragment_active_on_date(fragment, query_date)), Decimal("0"))


def _fragment_in_scope(fragment: FragmentInterval, scope_broker_ids: set[int]) -> bool:
    if fragment.custody_type == "BROKER":
        return fragment.broker_id in scope_broker_ids
    return fragment.source_broker_id in scope_broker_ids and fragment.destination_broker_id in scope_broker_ids


def _economics_on_date(
    lot_id: int,
    current_date: date_type,
    income_prefix: dict[date_type, Decimal],
    fees_prefix: dict[date_type, Decimal],
    taxes_prefix: dict[date_type, Decimal],
    withheld: WithheldEconomics,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Cumulative income, fees and taxes of a lot on a date; each None from the date its pool became unknown."""
    return (
        _known_prefix_on_date(income_prefix, withheld.income_from.get(lot_id), current_date),
        _known_prefix_on_date(fees_prefix, withheld.fees_from.get(lot_id), current_date),
        _known_prefix_on_date(taxes_prefix, withheld.taxes_from.get(lot_id), current_date),
    )


def _lot_returns(
    original_cost: Decimal,
    total_value: Decimal,
    income: Decimal | None,
    allocated_fees: Decimal | None,
    allocated_taxes: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    """Total return (income included) and net total return on the lot's cost; None when a part is unknown."""
    if original_cost == Decimal("0") or income is None:
        return None, None
    total_return = ((total_value + income) / original_cost) - Decimal("1")
    if allocated_fees is None or allocated_taxes is None:
        return total_return, None
    return total_return, ((total_value + income - allocated_fees - allocated_taxes) / original_cost) - Decimal("1")


def _known_prefix_on_date(values_by_date: dict[date_type, Decimal], unknown_from: date_type | None, query_date: date_type) -> Decimal | None:
    """A cumulative income, fee or tax on a date; None from the date its pool became unknown."""
    if unknown_from is not None and query_date >= unknown_from:
        return None
    return _prefix_value_on_date(values_by_date, query_date)


def _adjustment_native_cost(tx: Transaction | FifoInputTransaction, asset_currency: str) -> tuple[Decimal, str] | None:
    """The money an ADJUSTMENT moves, in its own currency; None for a quantity-only correction.

    With a cost basis, the quantity times the per-unit cost: negative for an ADJUSTMENT-out, which hands its units
    over at that cost. Otherwise the absolute amount it carries.
    """
    if tx.cost_basis_override not in (None, Decimal("0")):
        return tx.quantity * tx.cost_basis_override, tx.cost_basis_currency or asset_currency
    if tx.amount != Decimal("0"):
        return abs(tx.amount), tx.currency or asset_currency
    return None


def adjustment_cash_flow_cost(
    *,
    tx: Transaction | FifoInputTransaction,
    asset_currency: str,
    fx_resolver: FxRateResolver,
) -> Decimal | None:
    """That money in the target currency.

    None when there is no money, or when its rate is missing: callers tell the two apart with
    ``_adjustment_native_cost``.
    """
    native_cost = _adjustment_native_cost(tx, asset_currency)
    if native_cost is None:
        return None
    amount, currency = native_cost
    return fx_resolver.convert(amount, currency, tx.date)


def fragment_active_on_date(fragment: FragmentInterval, query_date: date_type) -> bool:
    return fragment.start_date <= query_date and (fragment.end_date is None or query_date < fragment.end_date)
