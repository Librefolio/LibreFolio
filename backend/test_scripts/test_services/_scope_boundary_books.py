"""J-10 (decision N76) books: a TRANSFER pair across two brokers, written straight into a test's session.

Shared by the lots-analysis tests of the scope boundary (``test_financial/test_lots_transfer_scope_boundary.py``) and
the AI Export test of ``broker.fifo_summary`` (``test_ai_export_broker_fifo_summary_scope_boundary.py``). Rows are added
to the caller's session and flushed, never committed: the caller's ``session`` fixture rolls them back, so nothing
outlives the test. Every name carries a uuid4, so each test owns its users, brokers and asset whatever runs beside it.
No FX: everything is in EUR.

LEDGER L1 — an EUR asset (quote_base_quantity 1) quoted 100 EUR on 10 Jan 2025, 120 on 11 Jan, 130 on 12 and 13 Jan,
140 on 14 Jan and 150 on 15 Jan:

- broker A: BUY 10 on 10 Jan for 1000 EUR; TRANSFER −10 on 12 Jan (amount 0);
- broker B: TRANSFER +10 on 13 Jan carrying a cost basis of 100 EUR a unit — the Auto cost a receiving leg must carry;
  SELL 4 on 15 Jan for 600 EUR (150 a unit);
- the two TRANSFER legs point at each other; the owner U is OWNER of A and B (share 1). Read on 16 Jan.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole

CURRENCY = "EUR"
L1_BUY_DAY = date(2025, 1, 10)
L1_DEPARTURE_DAY = date(2025, 1, 12)  # A's leg leaves; the market says 130
L1_ARRIVAL_DAY = date(2025, 1, 13)  # B's leg arrives at its cost basis, 100 a unit
L1_SALE_DAY = date(2025, 1, 15)  # B sells 4 at 150
L1_DATE_TO = date(2025, 1, 16)  # the reading day: 150, carried from 15 Jan
L1_PRICES: Mapping[date, str] = {
    date(2025, 1, 10): "100",
    date(2025, 1, 11): "120",
    date(2025, 1, 12): "130",
    date(2025, 1, 13): "130",
    date(2025, 1, 14): "140",
    date(2025, 1, 15): "150",
}


def _tag() -> str:
    """A fragment no other test can draw: time alone collides between workers, a uuid4 does not."""
    return uuid4().hex[:16]


async def new_user(session: AsyncSession, label: str) -> User:
    tag = _tag()
    user = User(username=f"j10_{label}_{tag}", email=f"j10_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    session.add(user)
    await session.flush()
    return user


async def grant_owner(session: AsyncSession, broker: Broker, user: User) -> None:
    """``user`` becomes an OWNER of ``broker``, share 1: the lots analysis reads the access, never the share."""
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    await session.flush()


async def new_broker(session: AsyncSession, label: str, *owners: User) -> Broker:
    broker = Broker(name=f"J10 {label} {_tag()}")
    session.add(broker)
    await session.flush()
    for owner in owners:
        await grant_owner(session, broker, owner)
    return broker


async def new_asset(session: AsyncSession, label: str) -> Asset:
    tag = _tag()
    asset = Asset(display_name=f"J10 {label} {tag}", identifier_ticker=f"J10{tag[:8].upper()}", currency=CURRENCY, asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    return asset


def add_prices(session: AsyncSession, asset: Asset, prices: Mapping[date, str]) -> None:
    """The asset's closes, in EUR; the asset is the test's own, so no neighbour shares these rows."""
    session.add_all([PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=CURRENCY, source_plugin_key="TEST") for day, close in prices.items()])


def asset_row(
    broker: Broker,
    asset: Asset,
    tx_type: TransactionType,
    day: date,
    quantity: str,
    *,
    amount: str = "0",
    currency: str | None = CURRENCY,
    cost: str | None = None,
) -> Transaction:
    """A transaction of the asset; ``cost`` is a per-unit cost basis in EUR, written with its currency (both or neither)."""
    return Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=tx_type,
        date=day,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=currency,
        cost_basis_override=None if cost is None else Decimal(cost),
        cost_basis_currency=None if cost is None else CURRENCY,
    )


async def link(session: AsyncSession, first: Transaction, second: Transaction, *, both_ways: bool = True) -> None:
    """Point ``first`` at ``second`` and, unless ``both_ways`` is False, ``second`` back at ``first`` — after a flush gave them ids."""
    first.related_transaction_id = second.id
    if both_ways:
        second.related_transaction_id = first.id
    await session.flush()


@dataclass(frozen=True)
class LedgerL1:
    owner: User
    asset: Asset
    broker_a: Broker
    broker_b: Broker
    buy: Transaction
    out_leg: Transaction
    in_leg: Transaction
    sell: Transaction


async def seed_l1(session: AsyncSession, *, in_leg_cost: str | None = "100") -> LedgerL1:
    """Ledger L1 (module docstring). ``in_leg_cost=None`` writes B's leg without a cost basis, as legacy data has it."""
    owner = await new_user(session, "owner")
    broker_a = await new_broker(session, "A", owner)
    broker_b = await new_broker(session, "B", owner)
    asset = await new_asset(session, "L1")
    add_prices(session, asset, L1_PRICES)
    buy = asset_row(broker_a, asset, TransactionType.BUY, L1_BUY_DAY, "10", amount="-1000")
    out_leg = asset_row(broker_a, asset, TransactionType.TRANSFER, L1_DEPARTURE_DAY, "-10")
    in_leg = asset_row(broker_b, asset, TransactionType.TRANSFER, L1_ARRIVAL_DAY, "10", cost=in_leg_cost)
    sell = asset_row(broker_b, asset, TransactionType.SELL, L1_SALE_DAY, "-4", amount="600")
    session.add_all([buy, out_leg, in_leg, sell])
    await session.flush()
    await link(session, out_leg, in_leg)
    return LedgerL1(owner=owner, asset=asset, broker_a=broker_a, broker_b=broker_b, buy=buy, out_leg=out_leg, in_leg=in_leg, sell=sell)
