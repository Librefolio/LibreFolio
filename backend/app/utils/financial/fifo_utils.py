"""
FIFO Lot Calculation Utilities — pure math, no I/O.

Computes open and closed lots for a sequence of BUY/SELL transactions
using the First-In, First-Out (FIFO) matching method.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NamedTuple


class FIFOTransactionInput(NamedTuple):
    """Input transaction for FIFO calculation.

    Only BUY and SELL types are processed. The caller is responsible
    for filtering out other transaction types before calling calculate_fifo_lots().
    """

    id: int
    type: str       # "BUY" | "SELL"
    quantity: Decimal
    price: Decimal
    date: date


@dataclass(frozen=True)
class OpenLot:
    """A buy lot that has not been fully sold yet."""

    buy_transaction_id: int
    buy_date: date
    buy_price: Decimal
    original_quantity: Decimal
    remaining_quantity: Decimal


@dataclass(frozen=True)
class ClosedLot:
    """A fully or partially matched buy-sell pair."""

    buy_transaction_id: int
    sell_transaction_id: int
    buy_date: date
    sell_date: date
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal       # matched quantity
    realized_pnl: Decimal   # (sell_price - buy_price) * quantity


@dataclass(frozen=True)
class FIFOResult:
    """Result of FIFO lot calculation."""

    open_lots: list[OpenLot]
    closed_lots: list[ClosedLot]
    total_realized_pnl: Decimal
    total_unrealized_quantity: Decimal


def calculate_fifo_lots(transactions: list[FIFOTransactionInput]) -> FIFOResult:
    """Compute FIFO open and closed lots from a list of BUY/SELL transactions.

    Algorithm:
    1. Sort transactions by date ascending (then by id for determinism).
    2. BUY → push onto deque (FIFO queue).
    3. SELL → consume from front of deque:
       - If the front lot has enough remaining qty → partial match, lot stays in queue.
       - If the front lot is exhausted → remove it, continue to next.
    4. Remaining deque entries = open_lots.

    Args:
        transactions: List of BUY/SELL transactions. Other types are ignored.

    Returns:
        FIFOResult with open_lots, closed_lots, realized P&L, and unrealized qty.

    Raises:
        ValueError: If cumulative sell quantity exceeds cumulative buy quantity
            (possible unrecognized stock split or data issue).
    """
    sorted_txs = sorted(
        [t for t in transactions if t.type in ("BUY", "SELL")],
        key=lambda t: (t.date, t.id),
    )

    # Deque of (buy_tx, remaining_qty) mutable pairs represented as lists
    buy_queue: deque[list] = deque()  # [FIFOTransactionInput, remaining_qty]
    closed_lots: list[ClosedLot] = []
    total_realized_pnl = Decimal("0")

    for tx in sorted_txs:
        if tx.type == "BUY":
            buy_queue.append([tx, tx.quantity])
        elif tx.type == "SELL":
            sell_qty_remaining = tx.quantity
            while sell_qty_remaining > Decimal("0"):
                if not buy_queue:
                    raise ValueError(
                        f"SELL transaction {tx.id} on {tx.date} exceeds available bought quantity. "
                        "Possible unrecognized stock split or missing BUY transactions."
                    )
                buy_tx, buy_remaining = buy_queue[0]

                matched_qty = min(sell_qty_remaining, buy_remaining)
                realized_pnl = (tx.price - buy_tx.price) * matched_qty
                total_realized_pnl += realized_pnl

                closed_lots.append(ClosedLot(
                    buy_transaction_id=buy_tx.id,
                    sell_transaction_id=tx.id,
                    buy_date=buy_tx.date,
                    sell_date=tx.date,
                    buy_price=buy_tx.price,
                    sell_price=tx.price,
                    quantity=matched_qty,
                    realized_pnl=realized_pnl,
                ))

                buy_queue[0][1] -= matched_qty
                sell_qty_remaining -= matched_qty

                if buy_queue[0][1] == Decimal("0"):
                    buy_queue.popleft()

    open_lots = [
        OpenLot(
            buy_transaction_id=entry[0].id,
            buy_date=entry[0].date,
            buy_price=entry[0].price,
            original_quantity=entry[0].quantity,
            remaining_quantity=entry[1],
        )
        for entry in buy_queue
    ]

    total_unrealized_quantity = sum(
        (lot.remaining_quantity for lot in open_lots), Decimal("0")
    )

    return FIFOResult(
        open_lots=open_lots,
        closed_lots=closed_lots,
        total_realized_pnl=total_realized_pnl,
        total_unrealized_quantity=total_unrealized_quantity,
    )
