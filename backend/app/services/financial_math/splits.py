"""Stock splits linked to the transaction ledger: which ADJUSTMENT rows belong to a SPLIT asset event, and the ratio.

A split redistributes a position's existing cost over a new quantity: its ADJUSTMENT rows never add or remove cost or
capital. Every reader of the ledger that must recognise them — the portfolio engine, the lots analysis, Yield on Cost,
the average-cost replays of the WAC preview, the broker summary and the auto cost — loads them here, with one query,
and judges a ratio with one rule. A named point where the layer reads the database (rule 1 of
``financial-math.instructions.md``): the rows of the given transactions, nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AssetEvent, AssetEventType, Transaction, TransactionType


@dataclass(frozen=True, slots=True)
class SplitLink:
    """A transaction linked to a SPLIT asset event, with the event's asset, date and ratio, as stored."""

    transaction_id: int
    event_id: int
    transaction_asset_id: int | None
    event_asset_id: int
    broker_id: int
    transaction_type: TransactionType
    transaction_quantity: Decimal | None
    transaction_date: date_type
    event_date: date_type
    ratio: Decimal | None


async def load_split_links(db: AsyncSession, transactions: Sequence[Transaction]) -> list[SplitLink]:
    """Every given transaction linked to a SPLIT asset event, ordered by transaction id; [] without candidates.

    The rows come back as stored: no validation here, each caller decides what an inconsistent row means for it.
    """
    linked_ids = [transaction.id for transaction in transactions if transaction.id is not None and transaction.asset_event_id is not None]
    if not linked_ids:
        return []
    stmt = (
        select(
            Transaction.id,
            AssetEvent.id,
            Transaction.asset_id,
            AssetEvent.asset_id,
            Transaction.broker_id,
            Transaction.type,
            Transaction.quantity,
            Transaction.date,
            AssetEvent.date,
            AssetEvent.value,
        )
        .join(AssetEvent, Transaction.asset_event_id == AssetEvent.id)
        .where(Transaction.id.in_(linked_ids))
        .where(AssetEvent.type == AssetEventType.SPLIT)
        .order_by(Transaction.id)
    )
    return [
        SplitLink(
            transaction_id=transaction_id,
            event_id=event_id,
            transaction_asset_id=transaction_asset_id,
            event_asset_id=event_asset_id,
            broker_id=broker_id,
            transaction_type=transaction_type,
            transaction_quantity=transaction_quantity,
            transaction_date=transaction_date,
            event_date=event_date,
            ratio=ratio,
        )
        for (
            transaction_id,
            event_id,
            transaction_asset_id,
            event_asset_id,
            broker_id,
            transaction_type,
            transaction_quantity,
            transaction_date,
            event_date,
            ratio,
        ) in (await db.execute(stmt)).all()
    ]


def is_valid_split_ratio(ratio: Decimal | None) -> bool:
    """A split ratio the layer can use: present, finite and positive."""
    return ratio is not None and ratio.is_finite() and ratio > 0


async def split_linked_ids(db: AsyncSession, transactions: Sequence[Transaction]) -> set[int]:
    """The ids of the given transactions linked to a SPLIT asset event; an empty set without candidates.

    What an average-cost replay needs to mark a row as a split rescale: the rescale reads the row's own quantity,
    never the event's ratio, so no ratio is judged here.
    """
    return {link.transaction_id for link in await load_split_links(db, transactions)}
