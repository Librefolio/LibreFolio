"""
W-B69, MF's half (release 1.3; it blocks the release) — an Auto cost must never be computed over a pool that holds a row
it cannot read.

A regression of W-B58. ``RealDecimal`` (``backend/app/db/real_decimal.py``) reads a stored value that is no number — a
text such as 'n/a', a REAL ±inf — as None instead of raising. ``compute_wac_iterative`` (``portfolio_service.py``) still
selects such a row (in SQLite 'n/a' is not NULL and differs from 0), and ``cost_movement_from_transaction``
(``financial_math/average_cost.py``) skips it when its quantity reads None, takes a BUY whose amount reads None as a free
acquisition, and a row whose stored cost basis reads None as an acquisition of unknown cost, entering at zero. The Auto
cost comes out without the row, or lower, and is saved for good.

The cure's core, MF's (the coordinator's assignment, 17/10): ``TransactionAutoCostMixin._auto_cost``
(``backend/app/services/transactions/auto_cost.py``) raises ``UnreadablePoolError(count)`` when a row of its pool reads
None in its quantity, its amount, or a cost basis it stores (``cost_basis_override`` not NULL in SQL; a BUY's NULL cost
basis is legitimate). The pool is the facade's filters — broker, asset, date up to the pool's date, quantity not NULL and
not 0 — minus the rows left out; ``count`` is the number of such rows, a row unreadable in two columns counting once. Every
caller of ``_auto_cost`` meets it: ``_handover_cost``, the batch, ``TransactionService.delete_by_broker`` — reached from
``BrokerService.delete_bulk`` with force, which turns an exception into that broker's failed result — and the lone legs
(``lone_transfer_legs.py``, pinned in ``test_lone_transfer_legs.py``).

What this file pins:

- ``TestAutoCostRefusesAnUnreadablePool``, RED until the cure: ``_auto_cost`` over the pool of a receiving TRANSFER leg
  raises ``UnreadablePoolError`` — ``count`` 1 for one row unreadable in its quantity, its amount or its stored cost basis
  (an ADJUSTMENT +10 or a receiving TRANSFER +10), or in two of them; ``count`` 2 for two rows. Today it answers an
  average: 100 EUR without the row, or 50 EUR with a free or unknown-cost acquisition.
- ``TestAutoCostOverItsPoolAlone``, guards, green before the cure and after it: over a readable pool ``_auto_cost`` raises
  nothing and gives 200 EUR; an unreadable row outside the pool — of another asset, dated past the pool's date, or left out
  of it — raises nothing, and the average is the ``world``'s BUY alone, 100 EUR.
- ``TestBrokerDeletionOverAnUnreadablePool`` (case (c)): RED until the cure, a deletion with force whose surviving
  TRANSFER leg needs a cost over such a pool fails, with a message, and deletes nothing; guards, green before and after, a
  readable pool gives the survivor 200 EUR, and a deletion that computes no cost takes the unreadable row with its broker.

W's half — the issue ``autoCostUnreadable`` on a batch's Auto row and on the split of a TRANSFER pair, the code
``TXValidationCode.AUTO_COST_UNREADABLE`` and its messages — stays in ``test_transaction_cost_basis_rule.py``.

``UnreadablePoolError`` does not exist before the cure, so nothing here imports it: a test catches any exception and
matches it by its class name and its count (an attribute ``count``, or its first argument). The module that defines it is
the cure's to choose, and the file collects before and after.

The pool. The ``world`` fixture gives ``source`` 10 units for 1 000 EUR (a BUY on 6 Jan 2025), and each test stores a
TRANSFER pair source → dest of 4 units on 3 Feb (``_store``): the receiving leg's Auto cost averages ``source`` up to 3 Feb,
without the pair's two legs (``_auto_cost_source``). ``_plant`` adds a second acquisition on 13 Jan, 10 units worth 3 000
EUR: a BUY, or an incoming row that takes a cost basis — an ADJUSTMENT +10, or a receiving TRANSFER +10 whose giving leg is
on a third broker of the test's — stored at 300 EUR a unit. Readable, the pool averages (1 000 + 3 000) / 20 = 200 EUR.
``_make_unreadable`` overwrites columns of a row with 'n/a' by raw SQL, in the same session, and checks what the case rests
on: SQLite keeps the text, the facade's quantity filters still select the row, and it loads with None in those columns.

Ownership. Every test builds its own asset and brokers under a unique marker, in a session rolled back at the end;
``delete_bulk`` works inside that session's transaction (a savepoint per broker), so nothing reaches the lane's database.

Self-contained: it imports from ``backend.app`` only, and its fixtures and helpers are its own, copied from
``test_transaction_cost_basis_rule.py`` (W-B69, 17/10). Register it in ``scripts/test_runner/_backend_services.py`` like its
neighbours.
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT, set_test_mode

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that opens the database: test mode, so the app opens the lane's test database (the runner exports
# LIBREFOLIO_TEST_DATA_DIR), never the production one.
set_test_mode(True)

from sqlalchemy import bindparam, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import BRBulkDeleteResponse, BRDeleteItem
from backend.app.schemas.common import Currency
from backend.app.schemas.wac import WACPreviewResultItem
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow

EUR = "EUR"
BUY_DAY = date(2025, 1, 6)
MOVE_DAY = date(2025, 2, 3)
BUY_QUANTITY = Decimal("10")
# The world's BUY pays 1 000 EUR for 10 units: 100 EUR is source's average before anything is planted.
UNIT_COST = Decimal("100")
TRANSFER_QUANTITY = Decimal("4")
# A cost basis a receiving leg was saved with, distinct from every average here.
STORED_COST = Currency(code=EUR, amount=Decimal("42"))
STORED_TAGS = "wb69-mf-stored"
# The planted acquisition: a week after the world's BUY, before the move; 10 units for 3 000 EUR.
LATER_BUY_DAY = BUY_DAY + timedelta(days=7)
LATER_BUY_PAID = Decimal("-3000")

# The columns a plant may overwrite with 'n/a': RealDecimal reads each as None since W-B58.
PLANTABLE_COLUMNS = ("quantity", "amount", "cost_basis_override")
# The incoming rows that take a cost basis, and the per-unit cost they are stored with: the 3 000 EUR the planted BUY pays
# for its 10 units, so that every readable plant averages the same.
INCOMING_KINDS = ("adjustment", "receiving-transfer")
PLANT_KINDS = ("buy", *INCOMING_KINDS)
PLANTED_COST = -LATER_BUY_PAID / BUY_QUANTITY
PLANT_LABELS = {
    "buy": f"BUY +{BUY_QUANTITY} for {-LATER_BUY_PAID} EUR",
    "adjustment": f"ADJUSTMENT +{BUY_QUANTITY} stored at {PLANTED_COST} EUR a unit",
    "receiving-transfer": f"receiving TRANSFER +{BUY_QUANTITY} stored at {PLANTED_COST} EUR a unit",
}
# source's pool with the planted row readable: (1 000 + 3 000) / 20.
READABLE_POOL_COST = (BUY_QUANTITY * UNIT_COST - LATER_BUY_PAID) / (2 * BUY_QUANTITY)
# What today's average makes of that pool with one column of the planted row unreadable: the defect, for the red messages.
TODAY_OVER_AN_UNREADABLE = {
    "quantity": "the average skips the row whose quantity reads None: 1 000 / 10 = 100, where the readable pool gives 200",
    "amount": "the average takes the BUY whose amount reads None as a free acquisition: 1 000 / 20 = 50, where the readable pool gives 200",
    "cost_basis_override": "the average takes the row whose cost basis reads None as an acquisition of unknown cost, entering at zero: 1 000 / 20 = 50, where the readable pool gives 200",
}
# Case (c): the broker a deletion takes, and the leg of the pair that survives it.
DELETIONS = {
    "receiver": "dest, the receiver — the giving leg on source survives, handed over at source's Auto cost (_handover_cost)",
    "sender": "source, the sender — the receiving leg on dest, stored without a cost basis, survives with source's Auto cost (_auto_cost)",
}
# What _raw_rows reads of a row: its raw values, and the storage class of the three columns a plant may overwrite.
_RAW_KINDS = ", ".join(f"typeof({column}) AS {column}_kind" for column in PLANTABLE_COLUMNS)
_RAW_COLUMNS = f"id, type, date, quantity, amount, currency, related_transaction_id, cost_basis_override, cost_basis_currency, description, tags, {_RAW_KINDS}"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """The app's async engine, on this lane's test database."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """One session per test, rolled back at the end: nothing here commits."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@dataclass
class World:
    """One test's own data: an asset, the broker that holds it, the broker that receives it."""

    session: AsyncSession
    marker: str
    asset: Asset
    source: Broker
    dest: Broker


@pytest_asyncio.fixture
async def world(session) -> World:
    """An asset and two brokers of this test alone, and the BUY that gives ``source`` 10 units at 100 EUR.

    Both brokers allow a cash overdraft (the BUY spends cash no DEPOSIT brought) and refuse shorting, as a broker does by
    default.
    """
    marker = f"W-B69-MF {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    source = Broker(name=f"{marker} source", description="W-B69 MF: the broker units leave", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    dest = Broker(name=f"{marker} dest", description="W-B69 MF: the broker units reach", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([asset, source, dest])
    await session.flush()
    session.add(
        Transaction(
            broker_id=source.id,
            asset_id=asset.id,
            type=TransactionType.BUY,
            date=BUY_DAY,
            quantity=BUY_QUANTITY,
            amount=-(BUY_QUANTITY * UNIT_COST),
            currency=EUR,
            description=f"{marker} buy",
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    return World(session=session, marker=marker, asset=asset, source=source, dest=dest)


# ============================================================================
# HELPERS
# ============================================================================


def _stored_row(world: World, *, broker: Broker, quantity: Decimal, cost: Currency | None = None) -> Transaction:
    """A TRANSFER leg on ``MOVE_DAY`` as the database holds it, written without the batch and its checks: amount 0, no
    currency, the cost basis ``cost`` or none. Both legs of a pair carry the same description and tags."""
    now = utcnow()
    return Transaction(
        broker_id=broker.id,
        asset_id=world.asset.id,
        type=TransactionType.TRANSFER,
        date=MOVE_DAY,
        quantity=quantity,
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=cost.amount if cost is not None else None,
        cost_basis_currency=cost.code if cost is not None else None,
        asset_event_id=None,
        description=f"{world.marker} stored",
        tags=STORED_TAGS,
        created_at=now,
        updated_at=now,
    )


@dataclass
class Stored:
    """A stored TRANSFER pair: ``subject`` is its receiving leg, ``rows`` the giving leg and the receiving one."""

    subject: Transaction
    rows: list[Transaction]


async def _store(world: World, shape: str, *, cost: Currency | None) -> Stored:
    """Store the pair ``transfer_in`` names: a TRANSFER of 4 units source → dest, linked both ways, the receiving leg with
    the cost basis ``cost`` or none."""
    if shape != "transfer_in":
        raise ValueError(f"unknown shape {shape!r}")
    session = world.session
    giving = _stored_row(world, broker=world.source, quantity=-TRANSFER_QUANTITY)
    receiving = _stored_row(world, broker=world.dest, quantity=TRANSFER_QUANTITY, cost=cost)
    session.add_all([giving, receiving])
    await session.flush()
    # A pair points both ways, and the ids exist only after the first flush.
    giving.related_transaction_id = receiving.id
    receiving.related_transaction_id = giving.id
    await session.flush()
    return Stored(subject=receiving, rows=[giving, receiving])


async def _plant(world: World, *, kind: str = "buy", unreadable: tuple[str, ...] = (), day: date = LATER_BUY_DAY, asset_id: int | None = None) -> int:
    """A row of 10 units on ``source`` on ``day`` — of the ``world``'s asset, or ``asset_id`` — stored like any row, then
    each column of ``unreadable`` overwritten with 'n/a' (``_make_unreadable``); its id.

    ``kind``: ``buy``, a BUY paying 3 000 EUR, its cost basis NULL as a BUY's is; or an incoming row that takes a cost
    basis, stored at 300 EUR a unit (``PLANTED_COST``): ``adjustment``, an ADJUSTMENT +10, or ``receiving-transfer``, a
    TRANSFER +10 linked both ways to its giving leg on a third broker of the test's own. Readable, any of them is the second
    acquisition of ``source``'s pool, worth 3 000 EUR.
    """
    session = world.session
    now = utcnow()
    description = f"{world.marker} W-B69 planted {kind}"
    common = {"broker_id": world.source.id, "asset_id": asset_id or world.asset.id, "date": day, "quantity": BUY_QUANTITY, "description": description, "created_at": now, "updated_at": now}
    if kind == "buy":
        row = Transaction(type=TransactionType.BUY, amount=LATER_BUY_PAID, currency=EUR, **common)
    elif kind in INCOMING_KINDS:
        incoming_type = TransactionType.ADJUSTMENT if kind == "adjustment" else TransactionType.TRANSFER
        row = Transaction(type=incoming_type, amount=Decimal("0"), currency=None, cost_basis_override=PLANTED_COST, cost_basis_currency=EUR, **common)
    else:
        raise ValueError(f"unknown plant kind {kind!r}")
    session.add(row)
    await session.flush()
    row_id = row.id
    if kind == "receiving-transfer":
        # Its giving leg's broker allows shorting: it holds none of the units it gave, and nothing here replays it.
        sender = Broker(name=f"{world.marker} W-B69 sender", description="W-B69: the broker the planted TRANSFER came from", allow_cash_overdraft=True, allow_asset_shorting=True, created_at=now, updated_at=now)
        session.add(sender)
        await session.flush()
        giving = Transaction(broker_id=sender.id, asset_id=row.asset_id, type=TransactionType.TRANSFER, date=day, quantity=-BUY_QUANTITY, amount=Decimal("0"), description=description, created_at=now, updated_at=now)
        session.add(giving)
        await session.flush()
        giving.related_transaction_id, row.related_transaction_id = row_id, giving.id
        await session.flush()
    if unreadable:
        await _make_unreadable(world, row, unreadable)
    return row_id


async def _make_unreadable(world: World, row: Transaction, columns: tuple[str, ...]) -> None:
    """Overwrite each column of ``columns`` of ``row`` with 'n/a', by raw SQL through the same session, and check what the
    case rests on, so no test refuses or accepts a row it only assumes unreadable: SQLite keeps the text (``typeof``
    'text', so not NULL: how the cure tells a stored cost basis from none); the facade's quantity filters —
    ``compute_wac_iterative``: quantity not NULL and not 0 — still select the row; and its ORM copy, expired so that every
    later load re-reads it, loads with None in each overwritten column (``RealDecimal``, W-B58)."""
    session = world.session
    row_id = row.id
    for column in columns:
        assert column in PLANTABLE_COLUMNS, f"scaffold: a plant overwrites {PLANTABLE_COLUMNS}, not {column!r}"
        await session.execute(text(f"UPDATE transactions SET {column} = 'n/a' WHERE id = :id"), {"id": row_id})
    kinds = (await session.execute(text(f"SELECT {', '.join(f'typeof({column}) AS {column}' for column in PLANTABLE_COLUMNS)} FROM transactions WHERE id = :id"), {"id": row_id})).one()._asdict()
    assert {column: kinds[column] for column in columns} == dict.fromkeys(columns, "text"), f"setup: row id={row_id} must hold 'n/a' as text in {columns}; typeof = {kinds}"
    selected = (await session.execute(select(func.count()).select_from(Transaction).where(Transaction.id == row_id, Transaction.quantity.is_not(None), Transaction.quantity != 0))).scalar_one()
    assert selected == 1, f"setup: the facade's filters (quantity IS NOT NULL, quantity != 0) must still select row id={row_id}, or no pool holds it"
    session.expire(row)
    loaded = (await session.execute(select(Transaction).where(Transaction.id == row_id).execution_options(populate_existing=True))).scalar_one()
    read = {column: getattr(loaded, column) for column in PLANTABLE_COLUMNS}
    assert {column: read[column] for column in columns} == dict.fromkeys(columns), f"setup: RealDecimal must read the 'n/a' of id={row_id} as None (W-B58); the row loads {read}"


async def _other_asset(world: World) -> int:
    """A second asset of the test's own, in EUR: its rows lie outside every pool of the ``world``'s asset."""
    now = utcnow()
    other = Asset(display_name=f"{world.marker} other asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    world.session.add(other)
    await world.session.flush()
    return other.id


async def _auto_cost_of(world: World, row: Transaction) -> tuple[WACPreviewResultItem | None, Exception | None]:
    """``_auto_cost`` of ``row`` over the pool ``_auto_cost_source`` names — what the batch computes for an Auto row, and
    ``delete_by_broker`` for a receiving leg without a cost basis: ``(answered, None)``, or ``(None, raised)``. Any exception
    is caught, since ``UnreadablePoolError`` does not exist before the cure."""
    service = TransactionService(world.session)
    pool = await service._auto_cost_source(row)
    try:
        return await service._auto_cost(row, pool), None
    except Exception as error:  # the cure's exception, matched by its name in _assert_raises_unreadable
        return None, error


def _show(cost: tuple[Decimal | None, str | None]) -> str:
    """A cost, for a failure message."""
    amount, code = cost
    return "no cost" if (amount, code) == (None, None) else f"{amount} {code}"


def _answer(answered: WACPreviewResultItem | None) -> str:
    """What ``_auto_cost`` answered, for a failure message."""
    wac = answered.wac if answered is not None else None
    return _show((wac.amount, wac.code) if wac is not None else (None, None))


def _assert_raises_unreadable(answered: WACPreviewResultItem | None, raised: Exception | None, *, count: int, pool: str, today: str) -> None:
    """``_auto_cost`` raised ``UnreadablePoolError`` with ``count``; ``pool`` says what the pool holds, ``today`` what
    today's average makes of it."""
    assert raised is not None, f"W-B69: _auto_cost over a pool with {pool} must raise UnreadablePoolError({count}); today it answers {_answer(answered)} — {today}"
    found = getattr(raised, "count", raised.args[0] if raised.args else None)
    assert (type(raised).__name__, found) == ("UnreadablePoolError", count), f"W-B69: _auto_cost must raise UnreadablePoolError with count {count}; it raised {type(raised).__name__}: {raised!r}"


def _assert_gives(answered: WACPreviewResultItem | None, raised: Exception | None, *, cost: Decimal, what: str) -> None:
    """``_auto_cost`` raised nothing and answered ``cost`` EUR."""
    assert raised is None, f"{what}: _auto_cost must raise nothing; it raised {type(raised).__name__}: {raised!r}"
    wac = answered.wac if answered is not None else None
    got = (wac.amount, wac.code) if wac is not None else None
    assert got == (cost, EUR), f"{what}: _auto_cost must give {cost} {EUR}; it answered {_answer(answered)}"


async def _delete_with_force(world: World, broker_id: int) -> BRBulkDeleteResponse:
    """``BrokerService.delete_bulk`` with force, as ``DELETE /brokers?force=true`` runs it for a superuser
    (``as_user_id`` "all": the ``world``'s brokers have no access rows, and the OWNER check is not under test). Each broker
    in a savepoint of its own (W-B20): a failure takes back that broker's writes and lands in its result, never raised."""
    return await BrokerService(world.session).delete_bulk([BRDeleteItem(id=broker_id, force=True)], user_id=0, as_user_id="all")


async def _raw_rows(world: World, broker_ids: list[int]) -> dict[int, dict]:
    """Every row of ``broker_ids`` as SQLite holds it in the session's transaction, by id: raw values, and the storage class
    of the three columns a plant may overwrite — what the user finds once the request is over, the 'n/a' included."""
    statement = text(f"SELECT {_RAW_COLUMNS} FROM transactions WHERE broker_id IN :brokers ORDER BY id").bindparams(bindparam("brokers", expanding=True))
    return {row.id: row._asdict() for row in (await world.session.execute(statement, {"brokers": broker_ids})).all()}


def _changed(before: dict[int, dict], after: dict[int, dict]) -> dict[int, tuple]:
    """The rows two ``_raw_rows`` reads disagree on, by id: ``(before, after)``, None for a row absent on one side."""
    return {tx_id: (before.get(tx_id), after.get(tx_id)) for tx_id in sorted(set(before) | set(after)) if before.get(tx_id) != after.get(tx_id)}


async def _rows_by_id(world: World, ids: list[int]) -> dict[int, tuple]:
    """``(type, quantity, related_transaction_id, cost_basis_override, cost_basis_currency)`` of each row of ``ids`` the
    database still holds, re-read (``populate_existing``): a deleted row is absent."""
    statement = select(Transaction).where(Transaction.id.in_(ids)).execution_options(populate_existing=True)
    return {row.id: (row.type, row.quantity, row.related_transaction_id, row.cost_basis_override, row.cost_basis_currency) for row in (await world.session.execute(statement)).scalars()}


async def _brokers_now(world: World, broker_ids: list[int]) -> list[int]:
    """Which of ``broker_ids`` the database still holds, sorted."""
    return sorted((await world.session.execute(select(Broker.id).where(Broker.id.in_(broker_ids)))).scalars())


def _leg_shown(raw: dict | None) -> str:
    """A row as ``_raw_rows`` reads it, for a failure message."""
    if raw is None:
        return "gone"
    return f"{raw['type']} {raw['quantity']} with cost {raw['cost_basis_override']} {raw['cost_basis_currency']}, linked to {raw['related_transaction_id']}"


# ============================================================================
# RED — _auto_cost REFUSES A POOL WITH AN UNREADABLE ROW
# ============================================================================


class TestAutoCostRefusesAnUnreadablePool:
    """RED until W-B69's cure: ``_auto_cost`` over a pool that holds an unreadable row raises ``UnreadablePoolError``,
    ``count`` the number of such rows.

    The pool is a receiving TRANSFER leg's, stored without a cost basis (``_store``): ``source`` up to the move, without the
    pair's two legs — the ``world``'s BUY and the planted row. Today ``_auto_cost`` answers the average of what reads.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("kind", "column"),
        [("buy", "quantity"), ("buy", "amount"), ("adjustment", "cost_basis_override"), ("receiving-transfer", "cost_basis_override")],
        ids=["buy-quantity", "buy-amount", "adjustment-cost-basis", "receiving-transfer-cost-basis"],
    )
    async def test_auto_cost_over_a_pool_with_an_unreadable_row_raises(self, world, kind, column):
        """RED: ``UnreadablePoolError`` with ``count`` 1 — a BUY whose quantity or amount is 'n/a', or an incoming row whose
        stored cost basis is 'n/a' (the contract's addition of 17/10: stored, so not NULL in SQL, yet read None). Today it
        answers 100 EUR (the row skipped) or 50 EUR (a free acquisition, or one of unknown cost entering at zero)."""
        await _plant(world, kind=kind, unreadable=(column,))
        stored = await _store(world, "transfer_in", cost=None)

        answered, raised = await _auto_cost_of(world, stored.subject)

        _assert_raises_unreadable(answered, raised, count=1, pool=f"an unreadable row (a {PLANT_LABELS[kind]} of source whose {column} is 'n/a')", today=TODAY_OVER_AN_UNREADABLE[column])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("plants", "count", "today"),
        [
            pytest.param((("buy", ("quantity",)), ("buy", ("amount",))), 2, "the average skips the first row and takes the second as a free acquisition: 1 000 / 20 = 50", id="two-rows"),
            pytest.param((("adjustment", ("quantity", "cost_basis_override")),), 1, "the average skips the row: 1 000 / 10 = 100", id="one-row-quantity-and-cost-basis"),
        ],
    )
    async def test_count_is_the_number_of_unreadable_rows(self, world, plants, count, today):
        """RED: ``count`` counts rows, not values. Two rows unreadable — a BUY by its quantity, the next day's BUY by its
        amount — give ``count`` 2; one row unreadable in two columns — an ADJUSTMENT +10 by its quantity and its stored cost
        basis — gives ``count`` 1. Today ``_auto_cost`` answers 50 EUR for the two rows (the first skipped, the second free:
        1 000 / 20) and 100 for the one (skipped: 1 000 / 10)."""
        for offset, (kind, columns) in enumerate(plants):
            await _plant(world, kind=kind, unreadable=columns, day=LATER_BUY_DAY + timedelta(days=offset))
        stored = await _store(world, "transfer_in", cost=None)

        answered, raised = await _auto_cost_of(world, stored.subject)

        shape = " and ".join(f"a {PLANT_LABELS[kind]} whose {' and '.join(columns)} read 'n/a'" for kind, columns in plants)
        _assert_raises_unreadable(answered, raised, count=count, pool=f"{len(plants)} unreadable row(s) — {shape}", today=today)


# ============================================================================
# GUARDS — _auto_cost REFUSES FOR THE ROWS OF ITS POOL ALONE
# ============================================================================


class TestAutoCostOverItsPoolAlone:
    """Guards, green before W-B69's cure and after it: ``_auto_cost`` refuses for the rows of its pool alone."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", PLANT_KINDS)
    async def test_auto_cost_over_a_readable_pool_gives_its_average(self, world, kind):
        """Guard: the planted row readable — a BUY paying 3 000 EUR, its cost basis NULL as a BUY's is, or an ADJUSTMENT +10
        or a receiving TRANSFER +10 stored at 300 EUR a unit: ``_auto_cost`` raises nothing and gives (1 000 + 3 000) / 20 =
        200 EUR. A cure that counted every stored cost basis, rather than one stored and read None, turns the last two red."""
        await _plant(world, kind=kind)
        stored = await _store(world, "transfer_in", cost=None)

        answered, raised = await _auto_cost_of(world, stored.subject)

        _assert_gives(answered, raised, cost=READABLE_POOL_COST, what=f"A readable pool ({PLANT_LABELS[kind]} beside the world's BUY)")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("where", ["another-asset", "after-the-move", "left-out"])
    async def test_an_unreadable_row_outside_the_pool_raises_nothing(self, world, where):
        """Guard: a row of quantity 'n/a' that the pool does not hold raises nothing, and ``_auto_cost`` gives the
        ``world``'s BUY alone, 100 EUR:

        - ``another-asset``: a BUY of another asset on ``source`` (the facade's asset filter);
        - ``after-the-move``: a BUY on ``source`` dated a week after the move, past the pool's date (its date filter);
        - ``left-out``: the pair's own giving leg — on ``source``, on the move's day, selected by the facade's filters — which
          the pool leaves out (``_auto_cost_source``: without the pair's two legs): the contract's «minus the excluded rows».
        """
        if where == "another-asset":
            await _plant(world, unreadable=("quantity",), asset_id=await _other_asset(world))
        elif where == "after-the-move":
            await _plant(world, unreadable=("quantity",), day=MOVE_DAY + timedelta(days=7))
        stored = await _store(world, "transfer_in", cost=None)
        if where == "left-out":
            giving, _receiving = stored.rows
            await _make_unreadable(world, giving, ("quantity",))

        answered, raised = await _auto_cost_of(world, stored.subject)

        _assert_gives(answered, raised, cost=UNIT_COST, what=f"An unreadable row outside the pool ({where})")


# ============================================================================
# RED AND GUARDS — CASE (c): A BROKER DELETION OVER AN UNREADABLE POOL
# ============================================================================


class TestBrokerDeletionOverAnUnreadablePool:
    """Case (c): ``BrokerService.delete_bulk`` with force turns the surviving leg of a cross-broker TRANSFER into an
    ADJUSTMENT, with a cost computed before any row changes (``TransactionService.delete_by_broker``): the giving leg's
    handover cost, or the Auto cost of a receiving leg stored without one — both over ``source``'s pool up to the move. Each
    broker goes in a savepoint of its own, and an exception becomes that broker's failed result (W-B20)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deleted", tuple(DELETIONS))
    async def test_deletion_whose_survivor_needs_an_unreadable_pool_fails_and_deletes_nothing(self, world, deleted):
        """RED until W-B69 (c): the deletion fails — ``success`` False and a message, its text not pinned — and deletes
        nothing: both brokers stay, and every row of theirs as it was, the survivor a TRANSFER still linked, without the cost
        it would have taken. Today the deletion succeeds and writes on the survivor the average of what reads, 100 EUR."""
        await _plant(world, unreadable=("quantity",))
        stored = await _store(world, "transfer_in", cost=STORED_COST if deleted == "receiver" else None)
        giving, receiving = stored.rows
        brokers = [world.source.id, world.dest.id]
        deleted_id, survivor_id = (world.dest.id, giving.id) if deleted == "receiver" else (world.source.id, receiving.id)
        before = await _raw_rows(world, brokers)

        response = await _delete_with_force(world, deleted_id)

        after = await _raw_rows(world, brokers)
        brokers_now = await _brokers_now(world, brokers)
        assert [(result.id, result.success) for result in response.results] == [(deleted_id, False)], (
            f"W-B69: deleting {DELETIONS[deleted]}; that cost averages a pool holding a BUY of quantity 'n/a', so the deletion must fail and delete nothing; today delete_bulk answers "
            f"{[(result.id, result.success, result.message) for result in response.results]}, the brokers left are {brokers_now} of {sorted(brokers)}, and the survivor reads {_leg_shown(after.get(survivor_id))}"
        )
        assert (response.results[0].message or "").strip(), f"W-B69: the failed deletion of broker {deleted_id} must say why in its result; message {response.results[0].message!r}"
        changed = _changed(before, after)
        assert (brokers_now, changed) == (sorted(brokers), {}), f"W-B69: the failed deletion must leave both brokers and every row as they were; brokers {brokers_now}, changed rows (before, after): {changed}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deleted", tuple(DELETIONS))
    async def test_deletion_over_a_readable_pool_writes_its_average_on_the_survivor(self, world, deleted):
        """Guard, green today and after W-B69: with the planted BUY readable the deletion succeeds, the broker goes, and the
        survivor becomes an ADJUSTMENT, unlinked, at ``source``'s average, (1 000 + 3 000) / 20 = 200 EUR: the giving leg
        −4 (handover), or the receiving leg +4 (its missing cost)."""
        await _plant(world)
        stored = await _store(world, "transfer_in", cost=STORED_COST if deleted == "receiver" else None)
        giving_id, receiving_id = stored.rows[0].id, stored.rows[1].id
        source_id, dest_id = world.source.id, world.dest.id
        if deleted == "receiver":
            deleted_id, kept_id, survivor_id, quantity = dest_id, source_id, giving_id, -TRANSFER_QUANTITY
        else:
            deleted_id, kept_id, survivor_id, quantity = source_id, dest_id, receiving_id, TRANSFER_QUANTITY

        response = await _delete_with_force(world, deleted_id)

        assert [(result.id, result.success, result.message) for result in response.results] == [(deleted_id, True, None)], f"Deleting {DELETIONS[deleted]}, over a readable pool, failed: {response.results}"
        assert await _brokers_now(world, [source_id, dest_id]) == [kept_id]
        assert await _rows_by_id(world, [giving_id, receiving_id]) == {survivor_id: (TransactionType.ADJUSTMENT, quantity, None, READABLE_POOL_COST, EUR)}

    @pytest.mark.asyncio
    async def test_deletion_that_computes_no_cost_takes_the_unreadable_row_with_its_broker(self, world):
        """Guard, green today and after W-B69, DERIVED from (c) — the refusal is for a cost computed over the unreadable
        pool, not for an unreadable row anywhere: deleting the sender while the receiving leg carries its own cost, 42 EUR,
        computes no cost. The deletion succeeds; ``source`` goes with every row of its own, the planted BUY of quantity
        'n/a' included (``RealDecimal``: such a row "loads, and can be deleted"); the receiving leg becomes an ADJUSTMENT
        +4, unlinked, at its 42 EUR."""
        planted_id = await _plant(world, unreadable=("quantity",))
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        receiving_id = stored.subject.id
        source_id, dest_id = world.source.id, world.dest.id
        source_rows = list(await _raw_rows(world, [source_id]))
        assert planted_id in source_rows, f"scaffold: the planted BUY id={planted_id} must be one of source's rows {source_rows}"

        response = await _delete_with_force(world, source_id)

        assert [(result.id, result.success, result.message) for result in response.results] == [(source_id, True, None)], f"Deleting the sender, whose pool no cost reads, failed: {response.results}"
        assert await _brokers_now(world, [source_id, dest_id]) == [dest_id]
        assert await _rows_by_id(world, [*source_rows, receiving_id]) == {receiving_id: (TransactionType.ADJUSTMENT, TRANSFER_QUANTITY, None, STORED_COST.amount, STORED_COST.code)}
