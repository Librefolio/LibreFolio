"""A position's figures in the Dashboard's Performance table, from its values at the period's boundaries (R4, MF-A).

The boundary values themselves are the engine's (``DailyPositionState`` at the end of the period's start day and at its
end): the same valuation as the portfolio — trade marks, split adjustment, estimate at cost, the boundary day's rate —
so the rows' unrealized changes add up to the period's ``ugl_delta``. This module holds the rules that turn them into a
row: the return on the start value, the annualized return over the position's window, the annualized return of a
position closed in the period, and how an internal transfer splits the result between the two brokers (P22).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date as date_type
from decimal import Decimal

from backend.app.services.financial_math.portfolio.models import InternalAssetTransfer
from backend.app.services.financial_math.returns import cumulative_to_annualized

_RATIO_QUANTUM = Decimal("0.0001")
_ZERO = Decimal("0")


def counted_tract(transfer: InternalAssetTransfer, date_from: date_type | None, end: date_type) -> bool:
    """Whether the period's rows split ``transfer``'s result between its two brokers (P22): it leaves after the period's
    start and arrives by its end, its value on arrival and the cost moved both known. The one rule of the tract
    adjustments and of the moved cost a closed position's base counts (MF-A5)."""
    return (date_from is None or transfer.departure > date_from) and transfer.arrival <= end and transfer.value_at_arrival is not None and transfer.cost_moved is not None


def transfer_tract_adjustments(transfers: Iterable[InternalAssetTransfer], date_from: date_type | None, end: date_type) -> dict[tuple[int, int], Decimal]:
    """What each ``(broker_id, asset_id)`` row adds to its unrealized change for the internal transfers of the period.

    P22, «each broker answers for its own tract; the total is unchanged»: a transfer that both leaves and arrives
    inside the period closes the sender's tract at the moved units' value on arrival (V) and opens the receiver's at
    the same V. The sender's row gains V − C, the receiver's loses it (C, the cost moved): what the units did while at
    the sender — and in transit, which stays the sender's — is the sender's. A transfer already in transit at the
    period's start, still in transit at its end, or with V or C unknown keeps the plain boundary values.
    """
    adjustments: dict[tuple[int, int], Decimal] = defaultdict(lambda: _ZERO)
    for transfer in transfers:
        if not counted_tract(transfer, date_from, end):
            continue
        tract = transfer.value_at_arrival - transfer.cost_moved
        adjustments[(transfer.sender_broker_id, transfer.asset_id)] += tract
        adjustments[(transfer.receiver_broker_id, transfer.asset_id)] -= tract
    return dict(adjustments)


def transfer_costs_moved_out(transfers: Iterable[InternalAssetTransfer], date_from: date_type | None, end: date_type) -> dict[tuple[int, int], tuple[Decimal, int]]:
    """For each sender ``(broker_id, asset_id)``, the cost its counted tracts moved out of it and how many (MF-A5)."""
    moved: dict[tuple[int, int], tuple[Decimal, int]] = {}
    for transfer in transfers:
        if counted_tract(transfer, date_from, end):
            key = (transfer.sender_broker_id, transfer.asset_id)
            cost, count = moved.get(key, (_ZERO, 0))
            moved[key] = (cost + transfer.cost_moved, count + 1)
    return moved


def closed_position_base(cost_sold: Decimal, sales: int, moved_out: tuple[Decimal, int] | None, exits: int) -> Decimal | None:
    """The base of a closed position's annualized return: the cost of every unit that left it in the period (MF-A5).

    The row's result carries what the units it sold realized and what the units it moved to another broker of the scope
    did while there (the tract adjustment), so the base is the cost of both: ``cost_sold`` over its ``sales`` disposals
    counted in Realized, plus the cost its counted tracts moved out. When a unit left any other way — ``exits``, the
    position's outgoing quantity moves of the period, outnumber those disposals and tracts: a transfer outside the scope
    or still in transit at the end, a tract or a sale whose value or cost is unknown, an ADJUSTMENT without a cost —
    the row's result is not covered by a base, and None leaves the general rule standing. None without a base too.
    """
    moved_cost, moved_count = moved_out or (_ZERO, 0)
    if exits != sales + moved_count:
        return None
    base = cost_sold + moved_cost
    return base if base else None


def period_return_on_start(period_pnl: Decimal | None, start_value: Decimal | None) -> Decimal | None:
    """The period's P&L — or one of its components — as a fraction of the size of the start value, to 4 decimals; None without a start value."""
    if period_pnl is None or start_value is None or start_value == 0:
        return None
    return (period_pnl / abs(start_value)).quantize(_RATIO_QUANTUM)


def window_start(date_from: date_type | None, oldest_open_lot: date_type | None) -> date_type | None:
    """Where a position's annualization window starts: the later of the period's start and its oldest open lot."""
    if oldest_open_lot is not None and (date_from is None or oldest_open_lot > date_from):
        return oldest_open_lot
    return date_from


def annualized_period_return(
    period_pnl: Decimal | None,
    start_value: Decimal | None,
    end_cost: Decimal | None,
    *,
    window_from: date_type | None,
    end: date_type,
) -> Decimal | None:
    """The period's return annualized over the position's window (``window_from`` → ``end``).

    The base is the size of the start value; a position opened inside the period (no start value) falls back to its
    cost at the end. None without a base, a window, or the days :func:`returns.cumulative_to_annualized` needs.
    """
    ratio = period_return_on_start(period_pnl, start_value)
    if ratio is None and period_pnl is not None and end_cost is not None and end_cost != 0:
        ratio = (period_pnl / end_cost).quantize(_RATIO_QUANTUM)
    if ratio is None or window_from is None:
        return None
    return cumulative_to_annualized(ratio, (end - window_from).days)


def closed_position_annualized(
    period_pnl: Decimal | None,
    deployed_cost: Decimal | None,
    opened: date_type | None,
    closed: date_type | None,
    date_from: date_type | None,
) -> Decimal | None:
    """The annualized return of a position closed in the period, over its flight time inside it.

    Base: the cost of the units that left it, sold or moved to another broker of the scope
    (:func:`closed_position_base`). Window: from its first opening, clamped to the period's start, to the day its last
    lot closed (``holding_window.closed_position_window``). None without a base, either date, or enough days.
    """
    if period_pnl is None or not deployed_cost or opened is None or closed is None:
        return None
    start = opened if date_from is None or opened > date_from else date_from
    return cumulative_to_annualized((period_pnl / deployed_cost).quantize(_RATIO_QUANTUM), (closed - start).days)
