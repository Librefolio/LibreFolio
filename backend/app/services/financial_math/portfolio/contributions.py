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
        if date_from is not None and transfer.departure <= date_from:
            continue
        if transfer.arrival > end or transfer.value_at_arrival is None or transfer.cost_moved is None:
            continue
        tract = transfer.value_at_arrival - transfer.cost_moved
        adjustments[(transfer.sender_broker_id, transfer.asset_id)] += tract
        adjustments[(transfer.receiver_broker_id, transfer.asset_id)] -= tract
    return dict(adjustments)


def period_return_on_start(period_pnl: Decimal | None, start_value: Decimal | None) -> Decimal | None:
    """The period's P&L as a fraction of the size of the start value, to 4 decimals; None without a start value."""
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

    Base: the cost of the units it sold (the capital actually deployed). Window: from its first opening, clamped to
    the period's start, to the day its last lot closed (``holding_window.closed_position_window``). None without a
    base, either date, or enough days.
    """
    if period_pnl is None or not deployed_cost or opened is None or closed is None:
        return None
    start = opened if date_from is None or opened > date_from else date_from
    return cumulative_to_annualized((period_pnl / deployed_cost).quantize(_RATIO_QUANTUM), (closed - start).days)
