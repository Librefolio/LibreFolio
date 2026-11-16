"""An asset held at several brokers, seen as one row: the Dashboard's «Globale» view of the positions (project 74).

The developer's rule (16/11/2026): **the group is the sum of its brokers, never a recomputation as if they were one
broker.** Each broker keeps its own cost, its own lots and its own sales; the group adds up their amounts and derives
every ratio from those sums — a ratio of sums, never an average of ratios. A sum with an unknown part is unknown: a
partial sum would understate in silence.

The facts of each ``(asset, broker)`` come from the callers that already compute the per-broker rows (the summary's
holdings, the period's contributions); every derived figure reuses the layer's one formula for it
(``returns``, ``contributions``, ``weights``). An internal transfer only ever links two brokers of the scope
(``InternalAssetTransfer``), so inside a group it moves units between members: its tract adjustments cancel in the sum,
and its moves are not units that left or entered the group.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal

from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio.yield_on_cost import YieldOnCostResult, YieldOnCostStatus
from backend.app.services.financial_math.portfolio.contributions import (
    annualized_period_return,
    closed_flight_too_short,
    closed_position_annualized,
    closed_position_base,
    period_return_on_start,
    window_start,
)
from backend.app.services.financial_math.returns import change_ratio, cumulative_to_annualized, gain_loss_ratio, net_holding_return

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_CENT = Decimal("0.01")

# From the most to the least reliable way a holding is valued: a group takes its least reliable member's, so the row
# keeps the warning one of its brokers carries.
_VALUATION_ORDER = ("MARKET_PRICE", "LAST_TRADE_PRICE", "ESTIMATED_AT_COST", "MISSING")


def _sum_known(values: Iterable[Decimal | None]) -> Decimal | None:
    """Σ of the values; None when any is None (a sum with an unknown part is unknown)."""
    total = _ZERO
    for value in values:
        if value is None:
            return None
        total += value
    return total


def _sum_present(values: Iterable[Decimal | None]) -> Decimal | None:
    """Σ of the values that are there, for the parts a row leaves None when it has none (realized, income, fees); None when
    no member has any, as a row says it."""
    present = [value for value in values if value]
    return sum(present, _ZERO) if present else None


def _earliest(days: Iterable[date_type | None]) -> date_type | None:
    known = [day for day in days if day is not None]
    return min(known) if known else None


def _latest(days: Iterable[date_type | None]) -> date_type | None:
    known = [day for day in days if day is not None]
    return max(known) if known else None


# ─────────────────────────────────────────────────────────────── Portfolio (the holdings at the valuation date)


@dataclass(frozen=True, slots=True)
class HoldingFacts:
    """One broker's open position in an asset, as the summary's holding row has it (report currency, owner's share)."""

    broker_id: int
    quantity: Decimal
    market_value: Decimal | None
    # The engine's cost of the open quantity; None when it is incomplete
    cost_basis: Decimal | None
    gain_loss: Decimal | None
    # The row's average price, in the unit the row shows it (per quote unit: per 100 nominal for a BTP)
    wac_per_unit: Decimal | None
    current_price: Decimal | None
    valuation_source: str
    change_1d: Decimal | None
    # The position's value on the day before, at the day before's price: the base of the day's change
    previous_value: Decimal | None
    # The position's income and fees and taxes over its life, for the net annualized return
    income: Decimal
    costs: Decimal
    first_transaction: date_type | None
    oldest_open_lot: date_type | None
    missing_fx_pair: str | None = None


@dataclass(frozen=True, slots=True)
class GroupedHolding:
    """An asset's holding summed over its brokers."""

    broker_ids: list[int]
    quantity: Decimal
    market_value: Decimal | None
    cost_basis: Decimal | None
    gain_loss: Decimal | None
    gain_loss_ratio: Decimal | None
    wac_per_unit: Decimal | None
    current_price: Decimal | None
    valuation_source: str
    change_1d: Decimal | None
    change_1d_percent: Decimal | None
    annualized_return: Decimal | None
    first_transaction: date_type | None
    oldest_open_lot: date_type | None
    missing_fx_pair: str | None


def group_holdings(members: Sequence[HoldingFacts], *, valuation_date: date_type) -> GroupedHolding:
    """One asset's open positions at several brokers as one holding.

    Quantity, value, cost, unrealized result and the day's change are summed. The result's ratio is Σ result ÷ Σ cost
    (:func:`returns.gain_loss_ratio`, as a row's); the day's change percent Σ change ÷ Σ value the day before
    (:func:`returns.change_ratio`, with a row's 0.01 floor on the base, in percent to 2 decimals); the average price
    Σ(price × quantity) ÷ Σ quantity, total cost over total quantity in the rows' own unit; the net annualized return
    :func:`returns.net_holding_return` on the sums, from the first transaction of the first broker. The price is the
    asset's when the brokers agree, unknown otherwise; the valuation source the least reliable of the members'.
    """
    if not members:
        raise ValueError("a group needs at least one holding")
    quantity = sum((member.quantity for member in members), _ZERO)
    market_value = _sum_known(member.market_value for member in members)
    cost_basis = _sum_known(member.cost_basis for member in members)
    gain_loss = _sum_known(member.gain_loss for member in members)

    wac_parts = _sum_known(None if member.wac_per_unit is None else member.wac_per_unit * member.quantity for member in members)
    wac_per_unit = wac_parts / quantity if wac_parts is not None and quantity != 0 else None

    prices = {member.current_price for member in members}
    current_price = prices.pop() if len(prices) == 1 else None
    sources = [member.valuation_source for member in members]
    valuation_source = max(sources, key=lambda source: _VALUATION_ORDER.index(source) if source in _VALUATION_ORDER else len(_VALUATION_ORDER))

    change_1d = _sum_known(member.change_1d for member in members)
    previous_value = _sum_known(member.previous_value for member in members)
    change_1d_percent = None
    if change_1d is not None and previous_value is not None and abs(previous_value) > _CENT:
        ratio = change_ratio(change_1d, previous_value)
        change_1d_percent = (ratio * _HUNDRED).quantize(_CENT) if ratio is not None else None

    first_transaction = _earliest(member.first_transaction for member in members)
    annualized = None
    if cost_basis and first_transaction is not None:
        income = sum((member.income for member in members), _ZERO)
        costs = sum((member.costs for member in members), _ZERO)
        annualized = cumulative_to_annualized(net_holding_return(gain_loss, income, costs, cost_basis), (valuation_date - first_transaction).days)

    return GroupedHolding(
        broker_ids=[member.broker_id for member in members],
        quantity=quantity,
        market_value=market_value,
        cost_basis=cost_basis,
        gain_loss=gain_loss,
        gain_loss_ratio=gain_loss_ratio(gain_loss, cost_basis, positive_base=False),
        wac_per_unit=wac_per_unit,
        current_price=current_price,
        valuation_source=valuation_source,
        change_1d=change_1d,
        change_1d_percent=change_1d_percent,
        annualized_return=annualized,
        first_transaction=first_transaction,
        oldest_open_lot=_earliest(member.oldest_open_lot for member in members),
        missing_fx_pair=next((member.missing_fx_pair for member in members if member.missing_fx_pair), None),
    )


def group_yield_on_cost(members: Sequence[tuple[YieldOnCostResult, Decimal, Decimal | None]]) -> YieldOnCostResult:
    """The Yield on Cost of a group: the brokers' income over the group's total cost (developer, Q1, 16/11/2026).

    ``members`` are ``(result, quantity, average price)`` for each broker, the average price in the report currency as the
    result's denominator. Value = Σ(gross income per eligible unit × quantity) ÷ Σ(average price × quantity) — each
    broker's own YOC weighted by its cost, never an asset-wide replay. Any broker unavailable makes the group
    unavailable, with that broker's reason and provenance; no income anywhere is ``no_income``; a broker without income
    counts its cost and no income.
    """
    if not members:
        raise ValueError("a group needs at least one Yield on Cost")
    for result, _quantity, _wac in members:
        if result.status == YieldOnCostStatus.UNAVAILABLE:
            return result
    if all(result.status == YieldOnCostStatus.NO_INCOME for result, _quantity, _wac in members):
        return members[0][0]

    income = _ZERO
    cost = _ZERO
    quantity = _ZERO
    for result, member_quantity, wac in members:
        per_unit = result.provenance.gross_income_per_unit
        income += (per_unit.amount if per_unit is not None else _ZERO) * member_quantity
        cost += (wac or _ZERO) * member_quantity
        quantity += member_quantity
    first = members[0][0]
    value = income / cost if cost > 0 else None
    if value is None:
        # No positive cost to divide by: the group cannot say more than its first broker's reason would.
        return next((result for result, _quantity, _wac in members if result.status != YieldOnCostStatus.AVAILABLE), first)
    available = [result for result, _quantity, _wac in members if result.status == YieldOnCostStatus.AVAILABLE]
    provenance = first.provenance.model_copy(
        update={
            "first_pair_transaction_date": _earliest(result.provenance.first_pair_transaction_date for result, _quantity, _wac in members),
            "gross_income_transaction_count": sum(result.provenance.gross_income_transaction_count for result in available),
            "gross_income_per_unit": Currency(code=(available[0].provenance.gross_income_per_unit or first.provenance.gross_income_per_unit).code, amount=income / quantity if quantity else _ZERO),
            "net_zero": value == 0,
            "fx": [fx for result, _quantity, _wac in members for fx in result.provenance.fx],
            "issue_date": None,
            "issue_pair": None,
        }
    )
    return YieldOnCostResult(status=YieldOnCostStatus.AVAILABLE, value=value, reason=None, provenance=provenance)


# ─────────────────────────────────────────────────────────────── Period (the Performance table's rows)


@dataclass(frozen=True, slots=True)
class ContributionFacts:
    """One broker's figures for an asset over a period, as its Performance row computes them (report currency)."""

    broker_id: int
    held_at_start: bool
    held_at_end: bool
    start_value: Decimal | None
    end_value: Decimal | None
    # The cost of the quantity held at the end; None when incomplete or not held
    end_cost: Decimal | None
    unrealized_delta: Decimal | None
    realized: Decimal | None
    income: Decimal | None
    fees: Decimal | None
    period_pnl: Decimal | None
    # The cost the period's sales gave up, and how many there were
    cost_sold: Decimal
    sales: int
    # Every time units left the position in the period, and how many of those were counted internal transfers
    exits: int
    moved_out_count: int
    is_fully_sold: bool
    # The position's flight time (``holding_window.closed_position_window``)
    opened: date_type | None
    closed: date_type | None
    oldest_open_lot: date_type | None
    closed_by: str | None = None
    closed_to_broker_id: int | None = None


@dataclass(frozen=True, slots=True)
class GroupedContribution:
    """An asset's Performance row summed over its brokers."""

    broker_ids: list[int]
    start_value: Decimal | None
    end_value: Decimal | None
    end_cost: Decimal | None
    unrealized_delta: Decimal | None
    realized: Decimal | None
    income: Decimal | None
    fees: Decimal | None
    period_pnl: Decimal | None
    period_pnl_percent: Decimal | None
    unrealized_delta_percent: Decimal | None
    realized_percent: Decimal | None
    income_percent: Decimal | None
    fees_percent: Decimal | None
    annualized_return: Decimal | None
    is_fully_sold: bool
    closed_by: str | None
    closed_to_broker_id: int | None
    oldest_open_lot: date_type | None


def group_contributions(members: Sequence[ContributionFacts], *, date_from: date_type | None, end: date_type) -> GroupedContribution:
    """One asset's Performance rows at several brokers as one row.

    Values at the boundaries, the unrealized change, realized result, income, fees and the period's P&L are summed; an
    internal transfer between two members splits its result between their rows (P22), and the split cancels in the sum.
    The return and its components are on the summed start value (:func:`contributions.period_return_on_start`). The
    group is closed only when every member is; then its annualized return is on the cost of the units that left the
    group — its sales, never a move between its members (:func:`contributions.closed_position_base`) — over its flight
    time, the first opening to the last close. An open group annualizes on its summed start value, or its end cost,
    from its oldest open lot (:func:`contributions.annualized_period_return`); a move between members brings no new
    capital in, so no ``moved_in``.
    """
    if not members:
        raise ValueError("a group needs at least one contribution")
    start_value = _sum_known(member.start_value for member in members)
    end_value = _sum_known(member.end_value for member in members)
    unrealized_delta = _sum_known(member.unrealized_delta for member in members)
    period_pnl = _sum_known(member.period_pnl for member in members)
    realized = _sum_present(member.realized for member in members)
    income = _sum_present(member.income for member in members)
    fees = _sum_present(member.fees for member in members)
    held_at_end = [member for member in members if member.held_at_end]
    end_cost = _sum_known(member.end_cost for member in held_at_end) if held_at_end else None
    is_fully_sold = all(member.is_fully_sold for member in members)

    # The general rule, as a row's: on the start value (or the end cost), from the oldest lot still open
    oldest = _earliest(member.oldest_open_lot for member in held_at_end)
    annualized = annualized_period_return(period_pnl, start_value, end_cost, window_from=window_start(date_from, oldest), end=end)
    closed_by: str | None = None
    closed_to: int | None = None
    if is_fully_sold:
        last = max(members, key=lambda member: member.closed or date_type.min)
        closed_by, closed_to = last.closed_by, last.closed_to_broker_id
        sales = sum(member.sales for member in members)
        exits = sum(member.exits - member.moved_out_count for member in members)
        base = closed_position_base(sum((member.cost_sold for member in members), _ZERO), sales, None, exits)
        opened = _earliest(member.opened for member in members)
        closed = _latest(member.closed for member in members)
        closed_annualized = closed_position_annualized(period_pnl, base, opened, closed, date_from)
        if closed_annualized is not None:
            annualized = closed_annualized
        elif closed_flight_too_short(opened, closed, date_from):
            # MF-A3, as a row's: held too few days to annualize, «—», never the general rule over the period
            annualized = None

    return GroupedContribution(
        broker_ids=[member.broker_id for member in members],
        start_value=start_value,
        end_value=end_value,
        end_cost=end_cost,
        unrealized_delta=unrealized_delta,
        realized=realized,
        income=income,
        fees=fees,
        period_pnl=period_pnl,
        period_pnl_percent=period_return_on_start(period_pnl, start_value),
        unrealized_delta_percent=period_return_on_start(unrealized_delta, start_value),
        realized_percent=period_return_on_start(realized, start_value),
        income_percent=period_return_on_start(income, start_value),
        fees_percent=period_return_on_start(fees, start_value),
        annualized_return=annualized,
        is_fully_sold=is_fully_sold,
        closed_by=closed_by,
        closed_to_broker_id=closed_to,
        oldest_open_lot=_earliest(member.oldest_open_lot for member in members),
    )


# ─────────────────────────────────────────────────────────────── Other effects of the period


def merge_by_kind[K: Hashable](rows: Iterable[tuple[K, int | None, Decimal]]) -> list[tuple[K, list[int], Decimal]]:
    """Rows of the same kind summed into one (developer, Q2, 16/11/2026: «Globale is global»).

    ``rows`` are ``(kind, broker_id or None, amount)``; the result is ``(kind, broker ids in first-seen order, Σ amount)``
    in the order each kind first appears. A row with no broker adds no id.
    """
    order: list[K] = []
    brokers: dict[K, list[int]] = {}
    totals: dict[K, Decimal] = {}
    for kind, broker_id, amount in rows:
        if kind not in totals:
            order.append(kind)
            brokers[kind] = []
            totals[kind] = _ZERO
        totals[kind] += amount
        if broker_id is not None and broker_id not in brokers[kind]:
            brokers[kind].append(broker_id)
    return [(kind, brokers[kind], totals[kind]) for kind in order]


def group_by_asset[T](items: Iterable[T], asset_of: Callable[[T], int]) -> dict[int, list[T]]:
    """The items of each asset, the assets in first-seen order and the items in the order given."""
    groups: dict[int, list[T]] = {}
    for item in items:
        groups.setdefault(asset_of(item), []).append(item)
    return groups
