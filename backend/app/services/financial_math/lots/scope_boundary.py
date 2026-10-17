"""Transfers read at the edge of a broker scope (J-10, night decision N76).

A lots analysis replays the brokers of its scope only. A TRANSFER leg whose partner sits at a broker outside the scope
cannot pair inside it, and the engine would fail the whole asset (TRANSFER_PAIR_MISSING). Such a leg is read the way the
scope sees it, as the broker-scope Dashboard reads it (lot 41, D2 and D5):

* a leg that brings units in is an ADJUSTMENT-in at its own cost basis, the Auto cost a receiving leg carries (without
  one, on old data, a costless ADJUSTMENT-in: MISSING_COST_BASIS, as for any such row);
* a leg that sends units out is an ADJUSTMENT-out at the market value of its date: the scope realizes what the units
  gained while in it. A day with no observation on or before it values units at their cost (J-17), so there each
  fragment leaves at its own FIFO cost (``FifoInputTransaction.hands_over_at_own_cost``).

The partner is read for its pairing only (id, broker, asset, type, quantity and link), never for an amount or a cost,
so nothing of the other broker enters the figures. A pair that is really missing, or does not pair back, is left as it
is: the engine reports it. A reading is a detached copy; the scope's rows are never changed. Every reader of the
analysis takes the same list, and the performance history moves a read leg's market value across the scope, as it does
for a transfer whose two legs it replays (``histories.build_performance_history``).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from backend.app.services.financial_math.fifo.models import FifoInputTransaction, TransactionLike
from backend.app.services.financial_math.price_marks import AssetPriceSeries
from backend.app.services.financial_math.valuation import compute_holding_value

BoundaryDirection = Literal["IN", "OUT"]

_TRANSFER = "TRANSFER"
_ONE_UNIT = Decimal("1")


@dataclass(frozen=True, slots=True)
class TransferPartner:
    """The pairing fields of a partner leg outside the scope; never its amounts or costs."""

    id: int
    broker_id: int
    asset_id: int | None
    type: str
    quantity: Decimal | None
    related_transaction_id: int | None


@dataclass(frozen=True, slots=True)
class BoundaryLeg:
    """A transfer leg of the scope read at its edge: ``IN`` brings units in, ``OUT`` sends them out."""

    transaction_id: int
    direction: BoundaryDirection


@dataclass(frozen=True, slots=True)
class ScopeBoundaryReading:
    """The scope's rows in their order, each boundary leg replaced by its reading, and those legs by id."""

    transactions: list[TransactionLike | FifoInputTransaction]
    legs: dict[int, BoundaryLeg]


def partner_ids_to_load(transactions: Sequence[TransactionLike]) -> set[int]:
    """The partners the scope's TRANSFER legs name and the scope does not hold."""
    held = {tx.id for tx in transactions}
    return {tx.related_transaction_id for tx in transactions if _type_of(tx) == _TRANSFER and tx.related_transaction_id is not None and tx.related_transaction_id not in held}


def read_transfers_at_scope_boundary(
    transactions: Sequence[TransactionLike],
    *,
    partners: Mapping[int, TransferPartner],
    scope_broker_ids: Collection[int],
    price_series: AssetPriceSeries,
    quote_base_quantity: int,
) -> ScopeBoundaryReading:
    """Read every TRANSFER leg whose partner pairs back from a broker outside ``scope_broker_ids``; keep the others.

    ``partners`` holds the legs ``partner_ids_to_load`` names, as the database has them. ``price_series`` is the
    analysis' price resolver, ``quote_base_quantity`` the asset's quote scale.
    """
    scope = set(scope_broker_ids)
    read: list[TransactionLike | FifoInputTransaction] = []
    legs: dict[int, BoundaryLeg] = {}
    for tx in transactions:
        partner = partners.get(tx.related_transaction_id) if _type_of(tx) == _TRANSFER and tx.related_transaction_id is not None else None
        if tx.id is None or tx.asset_id is None or partner is None or not _pairs_across(tx, partner, scope):
            read.append(tx)
            continue
        if tx.quantity > 0:
            read.append(_read(tx, tx.id, tx.asset_id, cost_basis_override=tx.cost_basis_override, cost_basis_currency=tx.cost_basis_currency))
            legs[tx.id] = BoundaryLeg(transaction_id=tx.id, direction="IN")
            continue
        mark = price_series.resolve(tx.date)
        if mark.is_missing:
            read.append(_read(tx, tx.id, tx.asset_id, cost_basis_override=None, cost_basis_currency=None, hands_over_at_own_cost=True))
        else:
            read.append(_read(tx, tx.id, tx.asset_id, cost_basis_override=compute_holding_value(_ONE_UNIT, mark.unit_price, quote_base_quantity), cost_basis_currency=mark.currency))
        legs[tx.id] = BoundaryLeg(transaction_id=tx.id, direction="OUT")
    return ScopeBoundaryReading(transactions=read, legs=legs)


def _type_of(row: TransactionLike | TransferPartner) -> str:
    return str(getattr(row.type, "value", row.type))


def _pairs_across(tx: TransactionLike, partner: TransferPartner, scope: set[int]) -> bool:
    """Whether ``partner`` is ``tx``'s pair, at a broker outside the scope: the checks of the engine's own pairing."""
    if partner.broker_id in scope or _type_of(partner) != _TRANSFER or partner.related_transaction_id != tx.id or partner.asset_id != tx.asset_id:
        return False
    if not tx.quantity or not partner.quantity:
        return False
    return (tx.quantity > 0) != (partner.quantity > 0) and abs(tx.quantity) == abs(partner.quantity)


def _read(tx: TransactionLike, tx_id: int, asset_id: int, *, cost_basis_override: Decimal | None, cost_basis_currency: str | None, hands_over_at_own_cost: bool = False) -> FifoInputTransaction:
    """``tx`` as a standalone ADJUSTMENT of the same quantity, date and broker: a detached copy."""
    return FifoInputTransaction(
        id=tx_id,
        broker_id=tx.broker_id,
        asset_id=asset_id,
        date=tx.date,
        type="ADJUSTMENT",
        quantity=tx.quantity,
        amount=Decimal("0"),
        currency=tx.currency,
        cost_basis_override=cost_basis_override,
        cost_basis_currency=cost_basis_currency,
        related_transaction_id=None,
        hands_over_at_own_cost=hands_over_at_own_cost,
    )
