"""Second post-migration fix: the half of a pair whose partner is gone becomes a standalone row (V-3, decision D-J4).

Until 1.3 deleting a broker kept the other half of every pair it had with another broker as a TRANSFER,
CASH_TRANSFER or FX_CONVERSION without its partner (``related_transaction_id`` NULL). The lots cannot
read such a row (TRANSFER_PAIR_MISSING) and the Dashboard values it at market on its date. Since 1.3 the
deletion converts that half (``TransactionService.delete_by_broker``); this fix converts the halves already
in a database, as a split of the pair leaves them (``TransactionService.SPLIT_TYPE_MAP``):

- a received TRANSFER becomes an ADJUSTMENT with the same quantity, asset, cost basis and currencies. Its
  sender is gone, so a leg without a cost basis stays without one: the lots and the Dashboard report
  MISSING_COST_BASIS and the user enters it. (The 1.3 deletion, with the sender still there, writes its
  Auto cost instead.);
- the giving leg of a TRANSFER is counted, not changed, here: it becomes an ADJUSTMENT-out at the Auto cost of its
  own broker (decision 47 of release 1.3), which a ``sqlite3`` connection cannot compute. The step that runs right
  after the fixes converts it (``backend.app.services.transactions.lone_transfer_legs``: ``lone-transfer-legs`` at
  startup, and this package's ``__main__``, whose dry run shows the cost each leg would take);
- a CASH_TRANSFER or an FX_CONVERSION becomes a WITHDRAWAL when its amount is negative, a DEPOSIT otherwise,
  without an asset;
- the link goes, every other column stays, and ``updated_at`` moves to now: what is cached on it is
  computed again.

A row whose partner exists is never touched. A row the fix does not convert — a giving TRANSFER leg, a row
whose sign cannot be read, or a row of any other type (an ADJUSTMENT can carry a link) — keeps its type; if its
link names a row that no longer exists, only that link goes, as the deletion does for a link no split knows, so
that the foreign key check of the run can pass.
The detection logs, as a warning, the rows it would convert, grouped by conversion, those that would stay
without a cost basis, those it only unlinks and those it leaves as they are, so a dry run
(``python -m backend.app.db.post_migration --dry-run``, server stopped) shows them before anything is
written; after the commit each row it changed gets its own log line. Decision point 46 of release 1.3.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from backend.app.db.post_migration.base import FixContext, PostMigrationError, PostMigrationFix
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

# What the lone half of each linked type becomes: (the side giving, the side receiving). The giving side of
# a TRANSFER is the one whose quantity is negative; of a cash pair, the one whose amount is negative.
STANDALONE_TYPES: dict[str, tuple[str, str]] = {
    "TRANSFER": ("ADJUSTMENT", "ADJUSTMENT"),
    "CASH_TRANSFER": ("WITHDRAWAL", "DEPOSIT"),
    "FX_CONVERSION": ("WITHDRAWAL", "DEPOSIT"),
}

_LINKED = tuple(STANDALONE_TYPES)
_ORPHANS_SQL = f"""
    SELECT t.id, t.broker_id, t.type, t.date, t.quantity, t.amount, t.currency, t.asset_id,
           t.cost_basis_override, t.cost_basis_currency, t.related_transaction_id
    FROM transactions AS t
    WHERE (t.type IN ({", ".join("?" for _ in _LINKED)}) AND t.related_transaction_id IS NULL)
       OR (t.related_transaction_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM transactions AS p WHERE p.id = t.related_transaction_id))
    ORDER BY t.id
"""


@dataclass(frozen=True)
class _Half:
    """One row of a linked type without its partner."""

    id: int
    broker_id: int
    type: str
    date: str
    quantity: Any
    amount: Any
    currency: Optional[str]
    asset_id: Optional[int]
    cost_basis: Any
    cost_basis_currency: Optional[str]
    link: Optional[int]
    gives: Optional[bool]  # the giving side (negative quantity for a TRANSFER, negative amount otherwise); None: unreadable

    @property
    def new_type(self) -> Optional[str]:
        """What the row becomes, or ``None`` when it keeps its type: another type, its sign unreadable, or a TRANSFER's giving leg."""
        if self.type not in STANDALONE_TYPES or self.gives is None or (self.type == "TRANSFER" and self.gives):
            return None
        giving_type, receiving_type = STANDALONE_TYPES[self.type]
        return giving_type if self.gives else receiving_type

    @property
    def action(self) -> Optional[str]:
        """``convert``, ``unlink`` (a half it does not convert, whose link names a missing row) or ``None``."""
        if self.new_type is not None:
            return "convert"
        return "unlink" if self.link is not None else None

    @property
    def without_cost_basis(self) -> bool:
        """A received TRANSFER that becomes an ADJUSTMENT-in with no cost: MISSING_COST_BASIS until the user enters it."""
        return self.new_type == "ADJUSTMENT" and self.cost_basis is None


def _signed(value: Any) -> Optional[Decimal]:
    """A stored quantity or amount as a Decimal, or ``None`` when it is not a number."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _gives(row_type: str, quantity: Any, amount: Any) -> Optional[bool]:
    sign = _signed(quantity if row_type == "TRANSFER" else amount)
    return None if sign is None else sign < 0


def _orphans(conn: sqlite3.Connection) -> list[_Half]:
    rows = conn.execute(_ORPHANS_SQL, _LINKED).fetchall()
    return [_Half(*row, gives=_gives(row[2], row[4], row[5])) for row in rows]


class OrphanPairHalfFix(PostMigrationFix):
    fix_id = "orphan_pair_halves"

    def detect(self, conn: sqlite3.Connection, ctx: FixContext) -> Optional[list[_Half]]:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'transactions'").fetchone() is None:
            return None
        halves = _orphans(conn)
        if not halves:
            return None
        pending = [half for half in halves if half.action is not None]
        conversions: dict[str, list[int]] = {}
        for half in pending:
            if half.action == "convert":
                conversions.setdefault(f"{half.type}->{half.new_type}", []).append(half.id)
        # Giving TRANSFER legs are counted here and converted by the step after the fixes (lone_transfer_legs).
        logger.warning(
            (
                "Transactions found without their pair: each becomes the standalone row a split of the pair leaves"
                if any(half.action == "convert" for half in pending)
                else "Transactions without their pair left as they are, but for a link to a missing row: transfer legs whose receiving broker was deleted, rows whose sign cannot be read, links no split knows"
            ),
            count=len(halves),
            conversions=conversions,
            without_cost_basis=[half.id for half in pending if half.without_cost_basis],
            unlinked_only=[half.id for half in pending if half.action == "unlink"],
            left_giving_transfer_legs=[half.id for half in halves if half.gives and half.type == "TRANSFER"],
            left_unreadable_sign=[half.id for half in halves if half.type in STANDALONE_TYPES and half.gives is None],
        )
        return pending or None

    def apply(self, conn: sqlite3.Connection, anomaly: list[_Half], ctx: FixContext) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
        for half in anomaly:
            if half.action == "convert":
                keeps_asset = half.new_type == "ADJUSTMENT"
                cursor = conn.execute(
                    "UPDATE transactions SET type = ?, related_transaction_id = NULL, asset_id = CASE WHEN ? THEN asset_id ELSE NULL END, updated_at = ? WHERE id = ? AND type = ?",
                    (half.new_type, keeps_asset, now, half.id, half.type),
                )
            else:
                cursor = conn.execute("UPDATE transactions SET related_transaction_id = NULL, updated_at = ? WHERE id = ? AND type = ?", (now, half.id, half.type))
            if cursor.rowcount != 1:
                raise PostMigrationError(f"transaction {half.id}: changed while being converted; left as it is")
        ctx.state[self.fix_id] = anomaly

    def verify(self, conn: sqlite3.Connection, anomaly: list[_Half], ctx: FixContext) -> list[str]:
        problems = [f"transaction {half.id}: still a {half.type} without its pair" for half in _orphans(conn) if half.new_type is not None]
        for half in anomaly:
            expected = (half.new_type if half.action == "convert" else half.type, None)
            row = conn.execute("SELECT type, related_transaction_id FROM transactions WHERE id = ?", (half.id,)).fetchone()
            if row != expected:
                problems.append(f"transaction {half.id}: {row} after the fix, {expected[0]} unlinked expected")
        return problems

    def finish(self, ctx: FixContext, *, success: bool) -> None:
        if not success:
            return
        for half in ctx.state.get(self.fix_id, []):
            logger.info(
                "Transaction without its pair converted" if half.action == "convert" else "Transaction without its pair unlinked",
                transaction_id=half.id,
                broker_id=half.broker_id,
                date=half.date,
                from_type=half.type,
                to_type=half.new_type or half.type,
                quantity=str(half.quantity),
                amount=str(half.amount),
                currency=half.currency,
                asset_id=half.asset_id if (half.new_type or half.type) in ("ADJUSTMENT", "TRANSFER") else None,
                cost_basis=None if half.cost_basis is None else str(half.cost_basis),
                cost_basis_currency=half.cost_basis_currency,
                missing_cost_basis=half.without_cost_basis,
                former_partner_id=half.link,
            )
