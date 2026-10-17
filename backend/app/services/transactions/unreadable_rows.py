"""Transactions holding a stored value that is no number: one count for the readers that must not sum or average past them.

Since W-B58 ``RealDecimal`` reads a stored value that is no number — a text, or a REAL ±inf that an older version or
another tool left — as ``None`` instead of raising (``db/real_decimal.py``). A sum or an average that met such a row skipped
it, or counted it as zero, and answered a wrong number. These readers count them first and refuse instead: the Auto cost's
pool (``auto_cost.TransactionAutoCostMixin._unreadable_pool_rows``, W-B69) and a broker's balances (``balances.py``: the
replay that guards a batch and the gap-fix's end of day, W-B74).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction


async def count_unreadable_rows(session: AsyncSession, *where: Any, with_cost_basis: bool = False) -> int:
    """How many transactions matching ``where`` hold a stored value that is no number: a quantity or an amount read None
    (both NOT NULL columns, so a None is never a missing value), and with ``with_cost_basis`` a cost basis stored (not NULL
    in SQL) but read None — a NULL cost basis is a row without one, such as a ``BUY``."""
    columns: list[Any] = [Transaction.quantity, Transaction.amount]
    if with_cost_basis:
        columns += [Transaction.cost_basis_override, Transaction.cost_basis_override.is_(None)]
    rows = (await session.execute(select(*columns).where(*where))).all()
    return sum(1 for row in rows if row[0] is None or row[1] is None or (with_cost_basis and row[2] is None and not row[3]))


class UnreadableLedgerError(Exception):
    """A broker's balances that cannot be computed: ``count`` of its transactions hold a value that is no number (W-B74).

    Raised by ``get_balances_at_end_of`` (the gap-fix's end of day); the replay of a batch turns the same count into the
    issue ``ledgerUnreadable``. The broker is the caller's own (its editor), so its id is told; the rows are not.
    """

    def __init__(self, broker_id: int, count: int) -> None:
        self.broker_id = broker_id
        self.count = count
        super().__init__(f"The balances of broker {broker_id} cannot be computed: {count} of its transactions hold a value that is not a number")
