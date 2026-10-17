"""Decision 47 for the lone giving legs already in a database (V-3, release 1.3).

Until 1.3 deleting a broker left the giving leg of each TRANSFER it had received units through as a TRANSFER without
its partner. Since 1.3 the deletion turns such a leg into an ADJUSTMENT-out at the Auto cost of its own broker
(``TransactionService.delete_by_broker``, ``_handover_cost``), at which the lots hand its units over. This module does
the same for the legs already in a database. The post-migration fix ``orphan_pair_halves`` cannot: it runs on a
synchronous ``sqlite3`` connection, and the Auto cost is the async average cost (``compute_wac_iterative``: conversions,
splits). So this step runs right after the fixes: at startup (``lone-transfer-legs`` in ``app_lifespan.STARTUP_STEPS``,
which never stops the server) and in ``python -m backend.app.db.post_migration``, whose ``--dry-run`` lists every leg
with the cost it would take and writes nothing.

Every cost is computed before any row changes. A leg whose cost needs a missing conversion stays as it is, a TRANSFER
without its partner: an ADJUSTMENT-out without a cost would read the units it moved as destroyed. So does a leg whose
cost raises — its broker's pool holds a row that cannot be read (``UnreadablePoolError``, W-B69), or any other error —,
answered with the reason, and the run goes on with the others (decision 1). Of several workers
starting together, the first converts and the next find nothing (``begin_writes`` takes the write lock first). Like the
fixes, the step never touches a damaged database: at startup, when there is something to convert, it runs ``PRAGMA
quick_check`` first; the offline script runs it only when the fixes' integrity check passed.
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
from backend.app.schemas.wac import WACPreviewResultItem
from backend.app.services.transactions.batch_edits import make_standalone
from backend.app.services.transactions.transaction_service import TransactionService

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
    """A giving TRANSFER leg without its partner, and the Auto cost it leaves with (``None``: it stays a TRANSFER)."""

    id: int
    broker_id: int
    date: date
    quantity: Decimal
    asset_id: Optional[int]
    cost: Optional[Decimal]
    cost_currency: Optional[str]
    reason: Optional[str] = None  # why its cost could not be computed, when it raised

    @property
    def converted(self) -> bool:
        """Whether the leg becomes (or became) an ADJUSTMENT-out: it has an Auto cost."""
        return self.cost is not None

    def describe(self, *, dry_run: bool) -> str:
        """One line for ``python -m backend.app.db.post_migration``."""
        head = f"Lone transfer leg {self.id} (broker {self.broker_id}, {self.date.isoformat()}, quantity {self.quantity}, asset {self.asset_id})"
        if not self.converted:
            why = f"its cost could not be computed: {self.reason}" if self.reason else "no Auto cost (missing conversion)"
            return f"{head}: stays a TRANSFER without its partner, {why}"
        return f"{head}: {'would become' if dry_run else 'became'} an ADJUSTMENT at {self.cost} {self.cost_currency} per unit"


async def convert_lone_giving_legs(session: AsyncSession, *, dry_run: bool = False) -> list[LoneLeg]:
    """Turn every lone giving TRANSFER leg into an ADJUSTMENT-out at its own broker's Auto cost; the legs found.

    Changes rows in ``session`` and commits nothing: the caller commits, or rolls back. With ``dry_run`` it computes the
    costs and changes nothing.
    """
    if not dry_run:
        await begin_writes(session, Transaction)
    rows = (await session.execute(_lone_giving_legs())).scalars().all()
    service = TransactionService(session)
    handovers: list[tuple[Transaction, Optional[WACPreviewResultItem], Optional[str]]] = []
    for row in rows:
        try:
            handovers.append((row, await service._handover_cost(row), None))
        except Exception as exc:  # noqa: BLE001 — UnreadablePoolError or another failure: this leg stays, the others go on
            handovers.append((row, None, str(exc) or type(exc).__name__))
    found: list[LoneLeg] = []
    for leg, handover, reason in handovers:
        wac = handover.wac if handover is not None else None
        found.append(LoneLeg(id=leg.id, broker_id=leg.broker_id, date=leg.date, quantity=leg.quantity, asset_id=leg.asset_id, cost=wac.amount if wac else None, cost_currency=wac.code if wac else None, reason=reason))
        if wac and not dry_run:
            make_standalone(leg, TransactionType.ADJUSTMENT)
            service._write_auto_cost(leg, handover)
    return found


def _log(legs: list[LoneLeg], *, dry_run: bool) -> None:
    """One line per leg: converted (or to be), or left without a cost."""
    for leg in legs:
        fields = {"transaction_id": leg.id, "broker_id": leg.broker_id, "date": leg.date.isoformat(), "quantity": str(leg.quantity), "asset_id": leg.asset_id}
        if leg.converted:
            message = "Lone transfer leg would become an ADJUSTMENT at its Auto cost" if dry_run else "Lone transfer leg converted at its Auto cost"
            logger.info(message, cost_basis=str(leg.cost), cost_basis_currency=leg.cost_currency, **fields)
        elif leg.reason:
            logger.warning("Lone transfer leg left as it is: its Auto cost could not be computed", error=leg.reason, **fields)
        else:
            logger.warning("Lone transfer leg left as it is: its Auto cost needs a missing conversion", **fields)


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
