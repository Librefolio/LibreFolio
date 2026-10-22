"""Decision 47 for the lone giving legs already in a database (V-3, release 1.3).

Until 1.3 deleting a broker left the giving leg of each TRANSFER it had received units through as a TRANSFER without
its partner. Since 1.3 the deletion turns such a leg into an ADJUSTMENT-out (``TransactionService.delete_by_broker``),
and an ADJUSTMENT-out has no value: its units only leave the quantity (decision 47 as the developer changed it, N78-1,
21/10/2026; it used to leave at its broker's Auto cost). This module does the same for the legs already in a database,
after the post-migration fixes: at startup (``lone-transfer-legs`` in ``app_lifespan.STARTUP_STEPS``, which never stops
the server) and in ``python -m backend.app.db.post_migration``, whose ``--dry-run`` lists every leg and writes nothing.

No cost is needed any more, so every lone giving leg is converted. Of several workers starting together, the first
converts and the next find nothing (``begin_writes`` takes the write lock first). Like the fixes, the step never
touches a damaged database: at startup, when there is something to convert, it runs ``PRAGMA quick_check`` first; the
offline script runs it only when the fixes' integrity check passed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy import Select, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import aliased
from sqlalchemy.pool import NullPool

from backend.app.db.models import Transaction, TransactionType
from backend.app.db.session import begin_writes, get_async_engine
from backend.app.logging_config import get_logger
from backend.app.services.transactions.batch_edits import make_standalone

logger = get_logger(__name__)


def _lone_giving_legs() -> Select:
    """The lone giving TRANSFER legs: no link, or a link to a row that no longer exists (the fix clears those before this
    step; a dry run sees them). The sign is read by SQLite, so a quantity it cannot read as a number is never loaded."""
    partner = aliased(Transaction)
    lone = or_(Transaction.related_transaction_id.is_(None), ~select(partner.id).where(partner.id == Transaction.related_transaction_id).exists())
    return select(Transaction).where(Transaction.type == TransactionType.TRANSFER, Transaction.quantity < 0, lone).order_by(Transaction.id)


async def _database_is_sound(session: AsyncSession) -> bool:
    """``PRAGMA quick_check`` answers ``ok``: a damaged database is never touched, as the post-migration fixes leave it."""
    return (await session.execute(text("PRAGMA quick_check"))).scalars().all() == ["ok"]


@dataclass(frozen=True)
class LoneLeg:
    """A giving TRANSFER leg without its partner: it becomes an ADJUSTMENT-out without a value."""

    id: int
    broker_id: int
    date: date
    quantity: Decimal
    asset_id: Optional[int]

    def describe(self, *, dry_run: bool) -> str:
        """One line for ``python -m backend.app.db.post_migration``."""
        head = f"Lone transfer leg {self.id} (broker {self.broker_id}, {self.date.isoformat()}, quantity {self.quantity}, asset {self.asset_id})"
        return f"{head}: {'would become' if dry_run else 'became'} an ADJUSTMENT-out without a value"


async def convert_lone_giving_legs(session: AsyncSession, *, dry_run: bool = False) -> list[LoneLeg]:
    """Turn every lone giving TRANSFER leg into an ADJUSTMENT-out without a value; the legs found.

    Changes rows in ``session`` and commits nothing: the caller commits, or rolls back. With ``dry_run`` it changes
    nothing.
    """
    if not dry_run:
        await begin_writes(session, Transaction)
    rows = (await session.execute(_lone_giving_legs())).scalars().all()
    found = [LoneLeg(id=row.id, broker_id=row.broker_id, date=row.date, quantity=row.quantity, asset_id=row.asset_id) for row in rows]
    if not dry_run:
        for row in rows:
            make_standalone(row, TransactionType.ADJUSTMENT)
            row.cost_basis_override = None
            row.cost_basis_currency = None
    return found


def _log(legs: list[LoneLeg], *, dry_run: bool) -> None:
    """One line per leg converted (or to be)."""
    for leg in legs:
        fields = {"transaction_id": leg.id, "broker_id": leg.broker_id, "date": leg.date.isoformat(), "quantity": str(leg.quantity), "asset_id": leg.asset_id}
        logger.info("Lone transfer leg would become an ADJUSTMENT-out without a value" if dry_run else "Lone transfer leg converted to an ADJUSTMENT-out without a value", **fields)


async def convert_lone_giving_legs_at_startup() -> None:
    """The ``lone-transfer-legs`` startup step: never raises; a failure leaves every row as it was and the server starts.

    Nothing to convert, nothing checked: the common case costs one query. Otherwise the database must pass ``PRAGMA
    quick_check`` first, since the step runs whatever the fixes found and they never touch a damaged database.
    """
    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            if (await session.execute(_lone_giving_legs().limit(1))).first() is None:
                return
            if not await _database_is_sound(session):
                logger.warning("Lone transfer legs left as they are: the database failed its quick check")
                return
            legs = await convert_lone_giving_legs(session)
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — startup never blocks on a repair
        logger.warning("Lone transfer legs could not be converted; starting normally", error=str(exc))
        return
    _log(legs, dry_run=False)


async def run_lone_giving_legs(db_path: Path, *, dry_run: bool) -> list[LoneLeg]:
    """The same step on the SQLite file ``db_path``, for ``python -m backend.app.db.post_migration`` (server stopped)."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            legs = await convert_lone_giving_legs(session, dry_run=dry_run)
            if dry_run:
                await session.rollback()
            else:
                await session.commit()
    finally:
        await engine.dispose()
    _log(legs, dry_run=dry_run)
    return legs
