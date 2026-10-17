"""Holding windows: how long a position has been held, read from its quantity stream at one broker.

The window an annualized return of a position runs over starts at the opening date of its oldest lot still open (an
open position) or at its first opening, and ends at the date the last lot closed (a closed one). Lots are first in,
first out on quantity alone, each at its own broker: an incoming TRANSFER or ADJUSTMENT opens a lot dated at its arrival
there (D-MF2), an outgoing one consumes the oldest lots.

A stock split is neither: its ADJUSTMENT rescales every open lot by the same factor and keeps their dates, so a split
never makes a position look younger (T-B4) — the same rule the average cost applies to the pool
(``average_cost.CostEffect.SPLIT_RESCALE``).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from typing import Any

from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class QuantityMove:
    """One signed quantity change of a position at one broker; ``split`` marks a stock split's ADJUSTMENT."""

    date: date_type
    order: int
    quantity: Decimal
    split: bool = False


def quantity_moves(transactions: Iterable[Any], split_linked_ids: Collection[int]) -> list[QuantityMove]:
    """The quantity stream of a position's transactions, in replay order (date, then id).

    ``split_linked_ids`` are the transactions linked to a SPLIT asset event (``splits.split_linked_ids``).
    """
    moves = [QuantityMove(date=tx.date, order=tx.id or 0, quantity=tx.quantity or _ZERO, split=tx.id is not None and tx.id in split_linked_ids) for tx in transactions]
    return sorted(moves, key=lambda move: (move.date, move.order))


def oldest_open_lot_date(moves: Sequence[QuantityMove], dust: Decimal = QUANTITY_DUST_THRESHOLD) -> date_type | None:
    """Opening date of the oldest lot still open, or None when nothing is open.

    A positive move opens a lot, a negative one consumes the oldest lots first, and a split rescales the open lots
    (``moves`` in replay order, as :func:`quantity_moves` gives them). This is the FIFO opening date, later than the
    first ever once sales have consumed the first lots.

    MF-A7: the oldest lots that together hold ``dust`` or less — the residual a sale leaves — are set aside, as
    :func:`closed_position_window` counts such a residual as closed: the date is that of the first lot past which more
    than ``dust`` is open, and None when the whole position holds ``dust`` or less.
    """
    held = _ZERO
    for day, quantity in _open_lots(moves):
        held += quantity
        if held > dust:
            return day
    return None


def _open_lots(moves: Sequence[QuantityMove]) -> deque[list]:
    """The FIFO lots still open after ``moves``, oldest first, as ``[opening date, remaining quantity]``."""
    open_lots: deque[list] = deque()
    for move in moves:
        if move.split:
            held = sum((quantity for _day, quantity in open_lots), _ZERO)
            if held <= 0:
                continue
            after = held + move.quantity
            if after <= 0:
                open_lots.clear()
                continue
            factor = after / held
            for lot in open_lots:
                lot[1] *= factor
        elif move.quantity > 0:
            open_lots.append([move.date, move.quantity])
        elif move.quantity < 0:
            remaining = -move.quantity
            while remaining > 0 and open_lots:
                lot = open_lots[0]
                if lot[1] > remaining:
                    lot[1] -= remaining
                    remaining = _ZERO
                else:
                    remaining -= lot[1]
                    open_lots.popleft()
    return open_lots


def closed_position_window(moves: Sequence[QuantityMove], dust: Decimal = QUANTITY_DUST_THRESHOLD) -> tuple[date_type | None, date_type | None]:
    """The flight time of a position: ``(first opening, last close)``.

    The last close is the date the running quantity last fell to ``dust`` or below — a residual the platform leaves
    after redemptions in tranches counts as closed. ``(opening, None)`` while it never closes, ``(None, None)`` when it
    never opens. A split moves the quantity but never opens nor closes a position.
    """
    open_date: date_type | None = None
    last_close: date_type | None = None
    running = _ZERO
    for move in moves:
        previous = running
        running += move.quantity
        if move.split:
            continue
        if move.quantity > 0 and open_date is None:
            open_date = move.date
        if move.quantity < 0 and previous > dust and running <= dust:
            last_close = move.date
    return open_date, last_close


def exits_in(moves: Sequence[QuantityMove], date_from: date_type | None, end: date_type) -> int:
    """How many times units left the position in ``(date_from, end]``: its outgoing quantity moves, a split's aside
    (MF-A5: a closed position's base must cover every one of them)."""
    return sum(1 for move in moves if move.quantity < 0 and not move.split and (date_from is None or move.date > date_from) and move.date <= end)
