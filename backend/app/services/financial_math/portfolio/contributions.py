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
from dataclasses import dataclass
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


def transfer_tracts_moved_in(transfers: Iterable[InternalAssetTransfer], date_from: date_type | None, end: date_type) -> dict[tuple[int, int], Decimal]:
    """For each receiver ``(broker_id, asset_id)``, what its counted tracts' units gained before they arrived: Σ(value on
    arrival − cost moved), the amount its row's result leaves out (MF-A8)."""
    moved_in: dict[tuple[int, int], Decimal] = {}
    for transfer in transfers:
        if counted_tract(transfer, date_from, end):
            key = (transfer.receiver_broker_id, transfer.asset_id)
            moved_in[key] = moved_in.get(key, _ZERO) + (transfer.value_at_arrival - transfer.cost_moved)
    return moved_in


def closed_position_base(cost_sold: Decimal, sales: int, moved_out: tuple[Decimal, int] | None, exits: int, moved_in: Decimal | None = None) -> Decimal | None:
    """The base of a closed position's annualized return: the cost of every unit that left it in the period (MF-A5).

    The row's result carries what the units it sold realized and what the units it moved to another broker of the scope
    did while there (the tract adjustment), so the base is the cost of both: ``cost_sold`` over its ``sales`` disposals
    counted in Realized, plus the cost its counted tracts moved out. When a unit left any other way — ``exits``, the
    position's outgoing quantity moves of the period, outnumber those disposals and tracts: a transfer outside the scope
    or still in transit at the end, a tract or a sale whose value or cost is unknown —
    the row's result is not covered by a base, and None leaves the general rule standing.

    ``moved_in``, the mirror (MF-A8): the units the row received by counted tracts enter its result at their value on
    arrival (the tract adjustment takes back what they gained before), while its sales' and moves' costs are their
    historical cost; adding what they gained before arriving puts them in the base at that value too. A unit bought
    for 500, moved when worth 600, sold for 660: +60 on 600, not on 500. None for a base that is not positive.
    """
    moved_cost, moved_count = moved_out or (_ZERO, 0)
    if exits != sales + moved_count:
        return None
    base = cost_sold + moved_cost + (moved_in or _ZERO)
    return base if base > 0 else None


@dataclass(frozen=True, slots=True)
class PositionPeriodPnl:
    """A position's P&L over a period: the change of its unrealized result, and the whole (unrealized + realized + income
    - fees); None where a part is unknown."""

    unrealized_delta: Decimal | None
    period_pnl: Decimal | None


def position_period_pnl(
    *,
    held_at_start: bool,
    held_at_end: bool,
    unrealized_start: Decimal | None,
    unrealized_end: Decimal | None,
    transfer_adjustment: Decimal | None,
    realized: Decimal | None,
    income: Decimal | None,
    fees: Decimal | None,
) -> PositionPeriodPnl:
    """A position's period P&L from its boundaries and the period's realized result, income and fees (R4).

    Not held at a boundary counts as zero; held there with an unknown unrealized result (no rate, incomplete cost) makes
    the change unknown — never a figure that hides the missing part. ``transfer_adjustment`` is the internal-transfer
    tract adjustment of the position (``transfer_tract_adjustments``). The P&L adds the parts that are known, fees
    subtracted; None when none is.
    """
    unknown_boundary = (held_at_start and unrealized_start is None) or (held_at_end and unrealized_end is None)
    unrealized_delta = None
    if not unknown_boundary and (unrealized_end is not None or unrealized_start is not None or transfer_adjustment is not None):
        unrealized_delta = (unrealized_end or _ZERO) - (unrealized_start or _ZERO) + (transfer_adjustment or _ZERO)
    parts = [unrealized_delta, realized, income, _ZERO - fees if fees else None]
    known = [part for part in parts if part is not None]
    return PositionPeriodPnl(unrealized_delta=unrealized_delta, period_pnl=sum(known, _ZERO) if known else None)


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
    moved_in: Decimal | None = None,
) -> Decimal | None:
    """The period's return annualized over the position's window (``window_from`` → ``end``).

    The base is the size of the start value; a position opened inside the period (no start value) falls back to its
    cost at the end. None without a base, a window, or the days :func:`returns.cumulative_to_annualized` needs.

    ``moved_in`` (MF-A9), for a position opened inside the period that received units by counted tracts and from which
    no unit left in the period: what they gained before arriving (:func:`transfer_tracts_moved_in`). Its result counts
    them from their value on arrival, its end cost at their historical cost; the fallback base adds the same amount, as a
    closed position's does (MF-A8), and must then be positive. Not passed when units left the position in the period —
    before the arrival or after it: a transfer carries no quantity, so the part of the tract that left with them cannot
    be told apart, and the end cost stays the base.
    """
    ratio = period_return_on_start(period_pnl, start_value)
    if ratio is None and period_pnl is not None and end_cost is not None:
        if moved_in is None:
            base = end_cost if end_cost != 0 else None
        else:
            base = end_cost + moved_in
            base = base if base > 0 else None
        if base is not None:
            ratio = (period_pnl / base).quantize(_RATIO_QUANTUM)
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
