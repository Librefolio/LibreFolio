"""Stock splits linked to the transaction ledger: which ADJUSTMENT rows belong to a SPLIT asset event, and the ratio.

A split redistributes a position's existing cost over a new quantity: its ADJUSTMENT rows never add or remove cost or
capital. Every reader of the ledger that must recognise them — the portfolio engine, the lots analysis, Yield on Cost,
the average-cost replays of the WAC preview, the broker summary and the auto cost — loads them here, with one query,
and judges a ratio with one rule. The event store asks here which incoming adjustments of a SPLIT have no cost, before
it lets the SPLIT change type. A named point where the layer reads the database (rule 1 of
``financial-math.instructions.md``): the rows of the given transactions, or linked to the given events, nothing else.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from fractions import Fraction

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


@dataclass(frozen=True, slots=True)
class ImpliedSplitRatio:
    """The split a share change implies: ``numerator:denominator`` (3:1, 3:2), and how far the broker's number is from it."""

    numerator: int
    denominator: int
    # Decimal(numerator) / Decimal(denominator)
    ratio: Decimal
    # (held + added) / held, as the broker's numbers give it
    exact_ratio: Decimal
    # added − held × (numerator − denominator) / denominator: the broker's rounding (0 when the numbers are exact)
    rounding_gap: Decimal


def implied_split_ratio(held: Decimal, added: Decimal, *, max_denominator: int = 10) -> ImpliedSplitRatio | None:
    """The multiplicative split behind ``added`` new shares on ``held`` ones: the simple fraction nearest to
    ``(held + added) / held`` with a denominator up to ``max_denominator``, and the broker's rounding gap.

    A label for an import's «possible split» (W-B87): a broker that writes fractional shares rounds the shares it adds, so
    0.1643 added on 0.0822 held is a 3:1 split 0.0001 short. None when nothing is held or nothing is added, or when the
    nearest fraction is not above 1 (no multiplicative split).
    """
    if held <= 0 or added <= 0:
        return None
    exact_ratio = (held + added) / held
    fraction = Fraction(exact_ratio).limit_denominator(max_denominator)
    if fraction.numerator <= fraction.denominator:
        return None
    numerator, denominator = fraction.numerator, fraction.denominator
    rounding_gap = added - held * (numerator - denominator) / denominator
    return ImpliedSplitRatio(
        numerator=numerator,
        denominator=denominator,
        ratio=Decimal(numerator) / Decimal(denominator),
        exact_ratio=exact_ratio,
        rounding_gap=rounding_gap,
    )


def is_split_event_type(value: object) -> bool:
    """Whether ``value`` is the SPLIT asset event type: the member, or its text in any case, blanks around ignored.

    How code outside this module asks «is this event a split» without naming the member (the layer's rule d): the event
    store, checking the type of an event it is handed. Anything that is not text, ``None`` included, is not a split; it
    never raises.
    """
    return isinstance(value, str) and value.strip().upper() == AssetEventType.SPLIT


def split_event_condition():
    """SQL condition: the asset event is a SPLIT. How a query outside this module selects the splits without naming the member."""
    return AssetEvent.type == AssetEventType.SPLIT


def not_split_event_condition():
    """SQL condition: the asset event is not a SPLIT (a dividend, an interest, a price adjustment…)."""
    return AssetEvent.type != AssetEventType.SPLIT


async def split_linked_ids(db: AsyncSession, transactions: Sequence[Transaction]) -> set[int]:
    """The ids of the given transactions linked to a SPLIT asset event; an empty set without candidates.

    What an average-cost replay needs to mark a row as a split rescale: the rescale reads the row's own quantity,
    never the event's ratio, so no ratio is judged here.
    """
    return {link.transaction_id for link in await load_split_links(db, transactions)}


async def costless_incoming_split_adjustments(db: AsyncSession, event_ids: Collection[int]) -> dict[int, list[int]]:
    """The incoming ADJUSTMENTs without a cost linked to the SPLITs among ``event_ids``: event id → transaction ids, sorted.

    Linked to a SPLIT, such a row only rescales the position, so it needs no cost of its own (the Auto mode stores
    none). The same row with its event no longer a SPLIT would be an acquisition of unknown cost: the event store
    refuses that retype while one exists (P-10, decision 27). An outgoing row is not listed: without the SPLIT it is a
    reduction at average cost, which needs no cost; nor is an event that is not a SPLIT. {} without candidates.
    """
    if not event_ids:
        return {}
    stmt = (
        select(Transaction.asset_event_id, Transaction.id)
        .join(AssetEvent, Transaction.asset_event_id == AssetEvent.id)
        .where(AssetEvent.id.in_(list(event_ids)))
        .where(AssetEvent.type == AssetEventType.SPLIT)
        .where(Transaction.type == TransactionType.ADJUSTMENT)
        .where(Transaction.quantity > 0)
        .where(Transaction.cost_basis_override.is_(None))
    )
    costless: dict[int, list[int]] = {}
    for event_id, transaction_id in (await db.execute(stmt)).all():
        costless.setdefault(event_id, []).append(transaction_id)
    return {event_id: sorted(transaction_ids) for event_id, transaction_ids in costless.items()}
