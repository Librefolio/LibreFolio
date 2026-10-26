"""N68 (lot X5-3, "policy A"): the market-data wipe and the currency change keep the SPLIT events.

Replaces ``test_market_data_wipe_split_guard.py`` (X-R48), whose refusal this lot removes.

Measured before the cure: ``CurrencyChangeOperations.wipe_market_data_for_currency_change``
(``services/assets/currency_change.py``, reached as ``AssetSourceManager.wipe_market_data_for_currency_change``) counts,
then, unless it is the dry run, refuses with ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST`` while a SPLIT of the asset has
incoming adjustments without a cost (X-R48), else sets ``transactions.asset_event_id = NULL`` for every transaction linked
to an event of the asset, deletes every event, SPLITs included, and every price, and commits. The currency PATCH
(``AssetCRUDService.patch_assets_bulk``, ``services/assets/crud.py``) refuses an asset that has prices or events with the
token ``CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|...``, and the front end then wipes and PATCHes again.

The contract of N68 (decided by the developer on 19/10, defaults confirmed on 24/10):

* the wipe keeps every SPLIT event of the asset, manual or provider, untouched (every column), and keeps the transactions
  linked to it: an incoming ADJUSTMENT without a cost stays linked to its SPLIT, so it keeps rescaling the position and
  never becomes an acquisition of unknown cost (``financial_math.splits.costless_incoming_split_adjustments`` still lists
  it). It deletes the prices and every NON-SPLIT event (manual and provider), and sets ``asset_event_id`` to NULL on the
  transactions linked to those, which stay. It never refuses for the costless adjustments of a SPLIT (the code
  ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST``, the guard and the route's 409 are gone; the other guard,
  ``split_guard.splits_with_costless_adjustments``, stays for the provider changes, X-R49);
* its answer, and the dry run's (``GET .../market-data/summary``), are exactly ``{prices, events_manual, events_provider,
  splits_kept, linked_tx, oldest, newest, dry_run}``: ``events_manual`` and ``events_provider`` count the NON-SPLIT events
  that go, ``splits_kept`` the SPLIT events that stay, ``linked_tx`` the transactions linked to the events that go (not
  those linked to a SPLIT);
* the currency PATCH always succeeds for such an asset, in the same call and the same transaction: it does what the wipe
  does (prices, non-split events gone, their transactions unlinked, SPLITs and their transactions kept), changes the
  currency, and never produces the token. An unknown asset of the batch fails by itself (partial success); the same
  currency changes nothing.

Each red says what the user faces before the cure («Red today»); a guard passes before and after.

Isolation: WRITE-SCOPED, the services default. Every row is this unit's own: two EUR STOCK assets created under a unique
name, the one wiped (assigned to a provider code of the unit's own that no provider has: its provider events need one,
nothing is fetched) and another, plus a third created and deleted at once, whose id no asset has or will have
(AUTOINCREMENT); two users and two brokers under the same marker, user A holding an access to broker A alone, user B to
broker B alone. Only the events and prices of those assets and the transactions on those brokers are written, read and
wiped, by asset and broker id (and the two assets' currency, put back to EUR around every test). Nothing here counts or
reads a row it did not write.
"""

import asyncio
import sys
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

import httpx
from fastapi import FastAPI
from sqlalchemy import bindparam, delete, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.assets import market_data as market_data_api
from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    Broker,
    BrokerUserAccess,
    PriceHistory,
    ProviderInputType,
    Transaction,
    TransactionType,
    User,
    UserRole,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.financial_math.splits import costless_incoming_split_adjustments
from backend.test_scripts.test_utils import unique_id

#: The code of X-R48's refusal, gone with this lot: no answer carries it any more.
OLD_CODE = "MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST"
#: The token of the currency PATCH's block, gone with this lot.
OLD_TOKEN = "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA"
#: The exact keys of the wipe's answer and of the summary's.
SUMMARY_KEYS = ["dry_run", "events_manual", "events_provider", "linked_tx", "newest", "oldest", "prices", "splits_kept"]

# A window far from the mock dataset and from the other split units. Rows are scoped by asset and broker anyway: the
# dates only keep the failure output readable.
BASE_DATE = date(1988, 4, 4)


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


def _wipe_path(asset_id: int) -> str:
    return f"/api/v1/assets/{asset_id}/market-data/wipe"


def _summary_path(asset_id: int) -> str:
    return f"/api/v1/assets/{asset_id}/market-data/summary"


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Owned:
    """What this unit created: the EUR STOCK asset whose market data are wiped, assigned to a provider code of the unit's
    own, and that assignment; another EUR STOCK asset; the id of a third, created and deleted at once; two users and two
    brokers, user A holding an access to broker A alone, user B to broker B alone."""

    asset_id: int
    other_asset_id: int
    ghost_asset_id: int
    assignment_id: int
    user_a_id: int
    user_b_id: int
    broker_a_id: int
    broker_b_id: int

    @property
    def asset_ids(self) -> list[int]:
        return [self.asset_id, self.other_asset_id]

    @property
    def user_ids(self) -> list[int]:
        return [self.user_a_id, self.user_b_id]

    @property
    def broker_ids(self) -> list[int]:
        return [self.broker_a_id, self.broker_b_id]


async def _clear(owned: _Owned) -> None:
    """Drop the transactions on this unit's brokers (they RESTRICT the events they link to), then every event and every
    price of its assets, and put both assets back to EUR. Bulk deletes: no row is loaded."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(Transaction).where(Transaction.broker_id.in_(owned.broker_ids)))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)))
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned.asset_ids)))
        await session.execute(update(Asset).where(Asset.id.in_(owned.asset_ids)).values(currency="EUR"))
        await session.commit()


@pytest.fixture(scope="module")
def owned_module() -> _Owned:
    """The assets, the assignment, the users, the brokers and the accesses, under names no concurrent worker can repeat,
    dropped in FK-safe order in teardown with every event, price and transaction written against them. The provider code
    is no provider's: nothing is ever fetched for it. The third asset is deleted in the same transaction that writes the
    accesses: its id stays unknown for good, ``assets`` being AUTOINCREMENT."""
    marker = f"{unique_id('N68')}_{uuid.uuid4().hex[:8]}"

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            wiped = Asset(display_name=f"N68 Wiped {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            other = Asset(display_name=f"N68 Other {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            ghost = Asset(display_name=f"N68 Ghost {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            user_a = User(username=f"n68a_{marker}".lower(), email=f"n68a_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            user_b = User(username=f"n68b_{marker}".lower(), email=f"n68b_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            broker_a = Broker(name=f"N68 A {marker}")
            broker_b = Broker(name=f"N68 B {marker}")
            session.add_all([wiped, other, ghost, user_a, user_b, broker_a, broker_b])
            await session.commit()
            ghost_id = ghost.id
            await session.execute(delete(Asset).where(Asset.id == ghost_id))
            assignment = AssetProviderAssignment(asset_id=wiped.id, provider_code=f"n68_{uuid.uuid4().hex[:12]}", identifier=f"N68.{marker}", identifier_type=ProviderInputType.TICKER)
            access_a = BrokerUserAccess(user_id=user_a.id, broker_id=broker_a.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            access_b = BrokerUserAccess(user_id=user_b.id, broker_id=broker_b.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            session.add_all([assignment, access_a, access_b])
            await session.commit()
            return _Owned(
                asset_id=wiped.id,
                other_asset_id=other.id,
                ghost_asset_id=ghost_id,
                assignment_id=assignment.id,
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                broker_a_id=broker_a.id,
                broker_b_id=broker_b.id,
            )

    async def _drop(owned: _Owned) -> None:
        await _clear(owned)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(BrokerUserAccess).where(or_(BrokerUserAccess.broker_id.in_(owned.broker_ids), BrokerUserAccess.user_id.in_(owned.user_ids))))
            await session.execute(delete(Broker).where(Broker.id.in_(owned.broker_ids)))
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.id == owned.assignment_id))
            await session.execute(delete(Asset).where(Asset.id.in_([*owned.asset_ids, owned.ghost_asset_id])))
            await session.execute(delete(User).where(User.id.in_(owned.user_ids)))
            await session.commit()

    owned = asyncio.run(_create())
    yield owned
    asyncio.run(_drop(owned))


@pytest_asyncio.fixture
async def owned(owned_module: _Owned):
    """The module's rows, with no event, no price and no transaction before and after the test, both assets in EUR."""
    await _clear(owned_module)
    yield owned_module
    await _clear(owned_module)


# --------------------------------------------------------------------------- #
# Seeding: rows written directly, as earlier saves and refreshes left them
# --------------------------------------------------------------------------- #


async def _add(row: AssetEvent | PriceHistory | Transaction) -> int:
    """``row`` written and committed in a session of its own: its id."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add(row)
        await session.commit()
        return row.id


async def _event(asset_id: int, offset: int, kind: AssetEventType, amount: str, *, assignment_id: int | None = None, notes: str | None = None) -> int:
    """An event of ``asset_id`` on day ``offset``, in EUR, as an earlier save left it, or a refresh under
    ``assignment_id``: its id."""
    return await _add(AssetEvent(asset_id=asset_id, date=_day(offset), type=kind, value=Decimal(amount), currency="EUR", notes=notes, provider_assignment_id=assignment_id))


async def _price(asset_id: int, offset: int, close: str) -> int:
    """A closing price of ``asset_id`` on day ``offset``, in EUR: its id."""
    return await _add(PriceHistory(asset_id=asset_id, date=_day(offset), close=Decimal(close), currency="EUR", source_plugin_key="test"))


async def _adjustment(asset_id: int, broker_id: int, event_id: int, offset: int, *, quantity: str = "10", cost: str | None = None) -> int:
    """An ADJUSTMENT of ``quantity`` units of ``asset_id`` on ``broker_id``, booked on day ``offset`` and linked to
    ``event_id``: without a cost, what the Auto mode stores on a row linked to a SPLIT, or with ``cost`` EUR a unit. Its
    id."""
    return await _add(
        Transaction(
            broker_id=broker_id,
            asset_id=asset_id,
            type=TransactionType.ADJUSTMENT,
            date=_day(offset),
            quantity=Decimal(quantity),
            amount=Decimal("0"),
            currency=None,
            cost_basis_override=None if cost is None else Decimal(cost),
            cost_basis_currency=None if cost is None else "EUR",
            asset_event_id=event_id,
        )
    )


async def _dividend(asset_id: int, broker_id: int, event_id: int, offset: int, amount: str) -> int:
    """A DIVIDEND of ``amount`` EUR of ``asset_id`` on ``broker_id``, booked on day ``offset`` and linked to the DIVIDEND
    event ``event_id``: its id."""
    return await _add(Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.DIVIDEND, date=_day(offset), quantity=Decimal("0"), amount=Decimal(amount), currency="EUR", asset_event_id=event_id))


async def _barrier_costless(event_ids: list[int], expected: dict[int, list[int]], story: str) -> None:
    """Barrier: among ``event_ids``, P-10's layer (``costless_incoming_split_adjustments``) lists exactly ``expected``, so
    what the wipe keeps or loses is about those rows."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        costless = await costless_incoming_split_adjustments(session, event_ids)
    assert costless == expected, f"barrier: {story}: the layer lists {costless} as the costless incoming adjustments of the SPLITs among the events {event_ids}, not {expected}"


# --------------------------------------------------------------------------- #
# Reading back: raw SQL, every column
# --------------------------------------------------------------------------- #

_RAW_PRICES = text("SELECT id, asset_id, date, open, high, low, close, volume, adjusted_close, currency, source_plugin_key, fetched_at FROM price_history WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))
_RAW_EVENTS = text("SELECT id, asset_id, date, type, value, currency, provider_assignment_id, notes, created_at, updated_at FROM asset_events WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))
_RAW_TRANSACTIONS = text("SELECT id, broker_id, asset_id, type, date, quantity, amount, currency, related_transaction_id, tags, description, cost_basis_override, cost_basis_currency, asset_event_id, created_at, updated_at FROM transactions WHERE broker_id IN :broker_ids ORDER BY id").bindparams(
    bindparam("broker_ids", expanding=True)
)


@dataclass(frozen=True)
class _State:
    """Every price and every event of the unit's assets and every transaction on its brokers: id -> its columns."""

    prices: dict[int, dict]
    events: dict[int, dict]
    transactions: dict[int, dict]


def _by_id(rows) -> dict[int, dict]:
    return {row["id"]: dict(row) for row in rows}


async def _read(session: AsyncSession, owned: _Owned) -> _State:
    """``_State`` through ``session``, with raw SQL."""
    assets, brokers = {"asset_ids": owned.asset_ids}, {"broker_ids": owned.broker_ids}
    prices = (await session.execute(_RAW_PRICES, assets)).mappings().all()
    events = (await session.execute(_RAW_EVENTS, assets)).mappings().all()
    transactions = (await session.execute(_RAW_TRANSACTIONS, brokers)).mappings().all()
    return _State(prices=_by_id(prices), events=_by_id(events), transactions=_by_id(transactions))


async def _committed(owned: _Owned) -> _State:
    """What is committed: ``_State`` read on a fresh connection (the engine pools none)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await _read(session, owned)


async def _currency_of(asset_id: int) -> str:
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return (await session.execute(select(Asset.currency).where(Asset.id == asset_id))).scalar_one()


def _table_changes(name: str, old: dict[int, dict], new: dict[int, dict]) -> str:
    """How one table moved between two reads: the rows gone, the rows added, and the changed columns of the others as
    (before, after)."""
    changed = {row_id: {key: (value, new[row_id].get(key)) for key, value in row.items() if new[row_id].get(key) != value} for row_id, row in old.items() if row_id in new and new[row_id] != row}
    return f"{name}: gone {sorted(set(old) - set(new))}, added {sorted(set(new) - set(old))}, changed {changed}"


def _changes(before: _State, after: _State) -> str:
    """What differs between two reads, table by table: for a failure message."""
    moved = [_table_changes(name, getattr(before, name), getattr(after, name)) for name in ("prices", "events", "transactions") if getattr(before, name) != getattr(after, name)]
    return "; ".join(moved) or "nothing"


def _of(rows: dict[int, dict], asset_id: int) -> dict[int, dict]:
    """The rows of ``asset_id`` among prices or events."""
    return {row_id: row for row_id, row in rows.items() if row["asset_id"] == asset_id}


# --------------------------------------------------------------------------- #
# The service and the PATCH, called as the route calls them
# --------------------------------------------------------------------------- #


async def _wipe_counters(owned: _Owned, story: str, *, dry_run: bool = False) -> dict:
    """The wipe of the unit's asset, or its dry run, as the route calls it: its counters. A refusal, or any other
    exception, fails the test, naming it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            return await AssetSourceManager.wipe_market_data_for_currency_change(asset_id=owned.asset_id, session=session, dry_run=dry_run)
        except AssetSourceError as refusal:
            pytest.fail(f"{story} was refused: {refusal.error_code} {refusal.message} {refusal.details}. Red today (X-R48): a SPLIT with a costless incoming adjustment makes the wipe refuse; N68 keeps the SPLIT and the wipe goes through, never refusing for it")
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story} raised {exc!r}: the route answers 500")


async def _not_found(asset_id: int, story: str, *, dry_run: bool) -> AssetSourceError:
    """The wipe, or its dry run, of ``asset_id``, which must raise: the ``AssetSourceError``. Anything else fails the test,
    naming it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            counters = await AssetSourceManager.wipe_market_data_for_currency_change(asset_id=asset_id, session=session, dry_run=dry_run)
        except AssetSourceError as error:
            return error
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            pytest.fail(f"{story} raised {exc!r} instead of ASSET_NOT_FOUND: the route answers 500")
    pytest.fail(f"{story} answered {counters} instead of raising ASSET_NOT_FOUND")


async def _patch_currency(asset_ids: list[int], currency: str):
    """``AssetCRUDService.patch_assets_bulk`` for the currency of ``asset_ids``, in a session of its own: the response."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await AssetCRUDService.patch_assets_bulk([FAAssetPatchItem(asset_id=asset_id, currency=currency) for asset_id in asset_ids], session)


def _assert_patched(response, asset_ids: Collection[int], story: str) -> None:
    """Every asset of ``asset_ids`` was patched: success, and no result carries the block's token."""
    by_id = {result.asset_id: result for result in response.results}
    for asset_id in asset_ids:
        result = by_id.get(asset_id)
        assert result is not None and result.success is True, f"{story}: the PATCH answered {result!r} for the asset {asset_id}: expected success. Red today (N68): an asset that has prices or events is refused with {OLD_TOKEN}|..., and the user must wipe first"
    tokens = [result.message for result in response.results if OLD_TOKEN in (result.message or "")]
    assert not tokens, f"{story}: the PATCH still produces the block's token: {tokens}"


# --------------------------------------------------------------------------- #
# The routes, in process
# --------------------------------------------------------------------------- #


async def _caller(user_id: int) -> User:
    """The user ``user_id`` as ``get_current_user`` hands it to a route: the row, loaded and detached."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None, f"barrier: the unit's user {user_id} is gone"
    return user


async def _route(user_id: int, method: str, path: str) -> httpx.Response:
    """``method path`` in process, as the user ``user_id``: the market-data router mounted at ``/api/v1/assets`` as the app
    mounts it, on an app of the call's own, so ``get_current_user`` is overridden there, never on the shared app, with
    the session the real dependency opens on the lane's database. Nothing is mocked behind the route."""
    caller = await _caller(user_id)
    app = FastAPI()
    app.include_router(market_data_api.market_data_router, prefix="/api/v1/assets")
    app.dependency_overrides[get_current_user] = lambda: caller
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path)


def _body(response: httpx.Response) -> object:
    """The JSON body as the client reads it: None when there is none to read (a 500's text)."""
    try:
        return response.json()
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# What the contract expects
# --------------------------------------------------------------------------- #


def _summary(*, prices: int, manual: int, provider: int = 0, kept: int, linked: int, priced: int | None, dry_run: bool) -> dict:
    """The wipe's answer for ``prices`` prices all on day ``priced`` (none: no day), ``manual`` and ``provider`` NON-SPLIT
    events that go, ``kept`` SPLIT events that stay and ``linked`` transactions linked to the events that go."""
    day = None if priced is None else _day(priced).isoformat()
    return {"prices": prices, "events_manual": manual, "events_provider": provider, "splits_kept": kept, "linked_tx": linked, "oldest": day, "newest": day, "dry_run": dry_run}


def _unlinked(row: dict) -> dict:
    """A transaction row as the wipe leaves a disconnected one: its link NULL, ``updated_at`` left out (the contract does
    not fix it)."""
    return {key: (None if key == "asset_event_id" else value) for key, value in row.items() if key != "updated_at"}


def _undated(row: dict) -> dict:
    """A transaction row with ``updated_at`` left out."""
    return {key: value for key, value in row.items() if key != "updated_at"}


async def _assert_wiped_keeping(owned: _Owned, before: _State, story: str, *, kept_events: Collection[int], disconnected: Collection[int]) -> None:
    """What N68's wipe, or the currency PATCH, leaves: no price of the wiped asset; of its events only ``kept_events`` (the
    SPLITs), every column as before; every transaction on the unit's brokers kept, the ``disconnected`` ones with their
    link NULL and every other column as before (``updated_at`` aside), all the others, the SPLIT-linked adjustments
    included, untouched, link and every column; the other asset's rows as they were."""
    after = await _committed(owned)
    prices_left = sorted(_of(after.prices, owned.asset_id))
    assert prices_left == [], f"{story}: the asset's prices {prices_left} are still there: expected none"
    expected_events = {event_id: before.events[event_id] for event_id in kept_events}
    found_events = _of(after.events, owned.asset_id)
    assert found_events == expected_events, f"{story}: the asset's events are {_table_changes('events', expected_events, found_events)}: expected exactly the SPLITs {sorted(kept_events)}, every column as before, and no other event"
    other = (_of(after.events, owned.other_asset_id), _of(after.prices, owned.other_asset_id))
    assert other == (_of(before.events, owned.other_asset_id), _of(before.prices, owned.other_asset_id)), f"{story}: the other asset's events or prices changed: {_changes(before, after)}"
    expected = {tx_id: (_unlinked(row) if tx_id in disconnected else row) for tx_id, row in before.transactions.items()}
    found = {tx_id: (_undated(row) if tx_id in disconnected else row) for tx_id, row in after.transactions.items()}
    assert found == expected, f"{story}: the transactions on the unit's brokers moved as {_changes(before, after)}: expected {sorted(disconnected)} kept and disconnected, every other transaction untouched, the SPLIT-linked ones still linked"


# --------------------------------------------------------------------------- #
# The cases
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _SplitBesideADividend:
    """A SPLIT and its costless adjustment, beside a dividend and its transaction (and a price)."""

    split_id: int
    adjustment_id: int
    dividend_id: int
    dividend_tx_id: int
    price_day: int


async def _split_beside_a_dividend(owned: _Owned, offset: int) -> _SplitBesideADividend:
    """On the wiped asset: a price (day ``offset - 1``); a manual SPLIT of 2 (day ``offset``) with a costless ADJUSTMENT
    +10 linked on broker A, booked the next day; a DIVIDEND of 1.5 EUR (day ``offset + 5``) linked to a DIVIDEND of 15 EUR
    on broker A (day ``offset + 7``). Barrier: P-10's layer lists the adjustment alone."""
    await _price(owned.asset_id, offset - 1, "100")
    split_id = await _event(owned.asset_id, offset, AssetEventType.SPLIT, "2", notes="2-for-1")
    dividend_id = await _event(owned.asset_id, offset + 5, AssetEventType.DIVIDEND, "1.5")
    adjustment_id = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, offset + 1)
    dividend_tx_id = await _dividend(owned.asset_id, owned.broker_a_id, dividend_id, offset + 7, "15")
    await _barrier_costless([split_id, dividend_id], {split_id: [adjustment_id]}, "a SPLIT with a costless adjustment, beside a linked dividend")
    return _SplitBesideADividend(split_id=split_id, adjustment_id=adjustment_id, dividend_id=dividend_id, dividend_tx_id=dividend_tx_id, price_day=offset - 1)


async def _split_on_two_brokers(owned: _Owned, offset: int) -> tuple[int, int, int]:
    """On the wiped asset: a manual SPLIT of 2 (day ``offset``) with a costless ADJUSTMENT +10 linked on broker B, then one
    on broker A, both booked the next day: (the SPLIT, broker B's adjustment, broker A's). Barrier: P-10's layer lists
    both."""
    split_id = await _event(owned.asset_id, offset, AssetEventType.SPLIT, "2", notes="2-for-1")
    on_b = await _adjustment(owned.asset_id, owned.broker_b_id, split_id, offset + 1)
    on_a = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, offset + 1)
    await _barrier_costless([split_id], {split_id: sorted([on_b, on_a])}, "a SPLIT with a costless adjustment on each broker")
    return split_id, on_b, on_a


async def _still_costless(split_id: int, adjustments: list[int], story: str) -> None:
    """After the wipe, or the PATCH: P-10's layer still lists ``adjustments`` as the costless incoming rows of the SPLIT, so
    each keeps rescaling the position and none became an acquisition of unknown cost (no MISSING_COST_BASIS)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        costless = await costless_incoming_split_adjustments(session, [split_id])
    assert costless == {split_id: sorted(adjustments)}, f"{story}: afterwards the layer lists {costless} for the SPLIT {split_id}: expected its adjustments {sorted(adjustments)} still linked and costless, so the position math is unchanged and no MISSING_COST_BASIS appears"


# ─────────────────────────────────────────────────────────────────────────────
# Reds: the wipe keeps the SPLITs
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_wipe_keeps_a_split_with_a_costless_adjustment_and_removes_the_rest(owned):
    """Red today (X-R48): the wipe is refused with MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST; the user must give a cost to
    adjustments that need none before the currency can change.

    Contract: a price, a manual SPLIT of 2 with a costless ADJUSTMENT +10 linked, a manual DIVIDEND linked to a DIVIDEND
    transaction. The wipe answers exactly 1 price, 1 manual event (the dividend), 0 provider events, ``splits_kept`` 1,
    ``linked_tx`` 1 (the dividend's transaction, not the adjustment), the price's day as oldest and newest, ``dry_run``
    false. The price and the dividend are gone; the SPLIT stays, every column as before; the ADJUSTMENT is untouched and
    still linked to its SPLIT, still costless in P-10's layer; the dividend's transaction stays, its link NULL."""
    case = await _split_beside_a_dividend(owned, 10)
    before = await _committed(owned)
    story = f"the wipe of the asset whose SPLIT {case.split_id} the costless adjustment {case.adjustment_id} links to, beside the dividend {case.dividend_id} linked to the transaction {case.dividend_tx_id} and a price"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=1, kept=1, linked=1, priced=case.price_day, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected {expected}"
    assert sorted(counters) == SUMMARY_KEYS, f"{story}: the answer's keys are {sorted(counters)}: expected exactly {SUMMARY_KEYS}"
    await _assert_wiped_keeping(owned, before, story, kept_events=[case.split_id], disconnected={case.dividend_tx_id})
    await _still_costless(case.split_id, [case.adjustment_id], story)


@pytest.mark.asyncio
async def test_the_wipe_keeps_manual_and_provider_splits_and_removes_provider_dividends(owned):
    """Red today (X-R48): refused (the wipe deletes the provider's SPLIT with the manual one, and disconnects both costless
    adjustments).

    Contract: a provider SPLIT of day 40 and a manual SPLIT of the same day, each with a costless ADJUSTMENT +10 on broker A;
    a provider DIVIDEND and a manual INTEREST, each linked to a transaction; a price. The wipe answers 1 price, 1 manual
    event (the interest), 1 provider event (the dividend), ``splits_kept`` 2, ``linked_tx`` 2. Both SPLITs stay with every
    column, ``provider_assignment_id`` included; both adjustments stay linked; the dividend and the interest are gone and
    their transactions kept and disconnected."""
    provider_split = await _event(owned.asset_id, 40, AssetEventType.SPLIT, "2", assignment_id=owned.assignment_id)
    manual_split = await _event(owned.asset_id, 40, AssetEventType.SPLIT, "2", notes="2-for-1")
    on_manual = await _adjustment(owned.asset_id, owned.broker_a_id, manual_split, 41)
    on_provider = await _adjustment(owned.asset_id, owned.broker_a_id, provider_split, 42)
    provider_dividend = await _event(owned.asset_id, 45, AssetEventType.DIVIDEND, "1.5", assignment_id=owned.assignment_id)
    manual_interest = await _event(owned.asset_id, 46, AssetEventType.INTEREST, "0.5")
    dividend_tx = await _dividend(owned.asset_id, owned.broker_a_id, provider_dividend, 47, "15")
    interest_tx = await _add(Transaction(broker_id=owned.broker_a_id, asset_id=owned.asset_id, type=TransactionType.INTEREST, date=_day(48), quantity=Decimal("0"), amount=Decimal("5"), currency="EUR", asset_event_id=manual_interest))
    await _price(owned.asset_id, 39, "100")
    await _barrier_costless([provider_split, manual_split], {provider_split: [on_provider], manual_split: [on_manual]}, "a provider SPLIT and a manual SPLIT of one day")
    before = await _committed(owned)
    story = f"the wipe of the asset whose provider SPLIT {provider_split} and manual SPLIT {manual_split} the costless adjustments {on_provider} and {on_manual} link to, beside a provider dividend and a manual interest"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=1, provider=1, kept=2, linked=2, priced=39, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected {expected} (events_manual and events_provider count the NON-SPLIT events that go, splits_kept the SPLITs that stay)"
    await _assert_wiped_keeping(owned, before, story, kept_events=[provider_split, manual_split], disconnected={dividend_tx, interest_tx})
    await _still_costless(provider_split, [on_provider], story)
    await _still_costless(manual_split, [on_manual], story)


@pytest.mark.asyncio
async def test_the_wipe_endpoint_answers_200_to_every_caller_and_keeps_the_splits(owned):
    """Red today (X-R48): 409 ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST`` with the caller's view of the adjustments.

    Contract: ``POST /assets/{id}/market-data/wipe`` as user A (in process), the asset holding a price and a SPLIT of 2 with
    a costless ADJUSTMENT +10 on broker B, then one on broker A (user A sees one of them only): 200, exactly 1 price, no
    NON-SPLIT event, ``splits_kept`` 1, ``linked_tx`` 0; the price is gone, the SPLIT and both adjustments stay linked,
    whoever asks. The same call as user B answers 200 again, now with nothing to delete (idempotent) and ``splits_kept``
    still 1. Neither answer carries the old code."""
    split_id, on_b, on_a = await _split_on_two_brokers(owned, 70)
    await _price(owned.asset_id, 69, "100")
    before = await _committed(owned)
    story = f"POST /assets/{owned.asset_id}/market-data/wipe, the SPLIT {split_id} linked to the costless adjustments {on_b} (broker B, user B's) and {on_a} (broker A, user A's)"

    first = await _route(owned.user_a_id, "POST", _wipe_path(owned.asset_id))

    assert first.status_code != 409 and OLD_CODE not in first.text, f"{story} as user A answers {first.status_code} {first.text}: expected 200, never the refusal {OLD_CODE} (N68)"
    expected_first = _summary(prices=1, manual=0, kept=1, linked=0, priced=69, dry_run=False)
    assert (first.status_code, _body(first)) == (200, expected_first), f"{story} as user A answers {first.status_code} {first.text}: expected 200 and {expected_first}"
    await _assert_wiped_keeping(owned, before, story, kept_events=[split_id], disconnected=set())
    second = await _route(owned.user_b_id, "POST", _wipe_path(owned.asset_id))
    expected_second = _summary(prices=0, manual=0, kept=1, linked=0, priced=None, dry_run=False)
    assert (second.status_code, _body(second)) == (200, expected_second), f"{story} as user B, the second time, answers {second.status_code} {second.text}: expected 200 and {expected_second}"
    await _assert_wiped_keeping(owned, before, story, kept_events=[split_id], disconnected=set())


@pytest.mark.asyncio
async def test_the_summary_counts_the_kept_splits_apart_and_writes_nothing(owned):
    """Red today: the dry run has no ``splits_kept``, and counts the SPLIT as a manual event that goes.

    Contract: the case of the first test (a price, a SPLIT with a costless adjustment, a dividend linked to a transaction).
    The dry run and ``GET .../market-data/summary`` as user A (in process) answer exactly 1 price, 1 manual event,
    0 provider events, ``splits_kept`` 1, ``linked_tx`` 1, the price's day as oldest and newest, ``dry_run`` true; they
    write nothing."""
    case = await _split_beside_a_dividend(owned, 110)
    before = await _committed(owned)
    expected = _summary(prices=1, manual=1, kept=1, linked=1, priced=case.price_day, dry_run=True)
    story = f"the summary of the asset whose SPLIT {case.split_id} the costless adjustment {case.adjustment_id} links to, beside the dividend {case.dividend_id} and a price"

    counters = await _wipe_counters(owned, f"the dry run, {story}", dry_run=True)
    response = await _route(owned.user_a_id, "GET", _summary_path(owned.asset_id))

    assert counters == expected, f"the dry run, {story}, answers {counters}: expected {expected}"
    assert (response.status_code, _body(response)) == (200, expected), f"GET /assets/{owned.asset_id}/market-data/summary as user A, {story}, answers {response.status_code} {response.text}: expected 200 and {expected}"
    after = await _committed(owned)
    assert after == before, f"{story} wrote: {_changes(before, after)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("cost", [pytest.param("12.5", id="cost-12.5"), pytest.param("0", id="cost-0")])
async def test_a_split_whose_incoming_adjustment_has_a_cost_is_kept_too(owned, cost):
    """Red today (counters): a SPLIT of 2 (day 80) with an ADJUSTMENT +10 linked that has a cost, ``cost`` EUR a unit (0 is a
    cost, not a missing one), and a price. Not refused, today as after; but today the SPLIT is deleted and counted as a
    manual event, and the adjustment disconnected.

    Contract: the SPLIT is kept (it is a SPLIT), the adjustment stays linked: 1 price, no event that goes, ``splits_kept``
    1, ``linked_tx`` 0."""
    split_id = await _event(owned.asset_id, 80, AssetEventType.SPLIT, "2")
    adjustment_id = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, 81, cost=cost)
    await _price(owned.asset_id, 79, "100")
    await _barrier_costless([split_id], {}, f"a SPLIT whose incoming adjustment costs {cost} EUR a unit")
    before = await _committed(owned)
    story = f"the wipe of the asset whose SPLIT {split_id} the adjustment {adjustment_id} (+10, {cost} EUR a unit) links to"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=0, kept=1, linked=0, priced=79, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected {expected}"
    await _assert_wiped_keeping(owned, before, story, kept_events=[split_id], disconnected=set())


@pytest.mark.asyncio
async def test_a_reverse_split_with_an_outgoing_costless_adjustment_is_kept_too(owned):
    """Red today (counters): a reverse SPLIT of 0.5 (day 90) with an ADJUSTMENT -10 linked, without a cost, and a price.
    Today the SPLIT goes and the adjustment is disconnected.

    Contract: the SPLIT stays, the adjustment stays linked: 1 price, no event that goes, ``splits_kept`` 1, ``linked_tx`` 0."""
    split_id = await _event(owned.asset_id, 90, AssetEventType.SPLIT, "0.5", notes="1-for-2")
    adjustment_id = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, 91, quantity="-10")
    await _price(owned.asset_id, 89, "100")
    await _barrier_costless([split_id], {}, "a reverse SPLIT with an outgoing costless adjustment")
    before = await _committed(owned)
    story = f"the wipe of the asset whose reverse SPLIT {split_id} the outgoing costless adjustment {adjustment_id} (-10) links to"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=0, kept=1, linked=0, priced=89, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected {expected}"
    await _assert_wiped_keeping(owned, before, story, kept_events=[split_id], disconnected=set())


@pytest.mark.asyncio
async def test_the_endpoint_keeps_a_split_nothing_links_to_and_disconnects_a_dividend(owned):
    """Red today (counters): a SPLIT of 2 nothing links to (day 100), a DIVIDEND of 1.5 EUR (day 101) linked to a DIVIDEND
    transaction on broker A, and a price. Today the answer is 200 with 2 manual events; the SPLIT is deleted.

    Contract: ``POST .../market-data/wipe`` as user A (in process): 200, 1 price, 1 manual event, ``splits_kept`` 1,
    ``linked_tx`` 1; the dividend and the price gone, the SPLIT kept, the dividend's transaction kept and disconnected."""
    split_id = await _event(owned.asset_id, 100, AssetEventType.SPLIT, "2")
    dividend_id = await _event(owned.asset_id, 101, AssetEventType.DIVIDEND, "1.5")
    dividend_tx_id = await _dividend(owned.asset_id, owned.broker_a_id, dividend_id, 103, "15")
    await _price(owned.asset_id, 99, "100")
    await _barrier_costless([split_id, dividend_id], {}, "a SPLIT nothing links to, beside a linked dividend")
    before = await _committed(owned)
    story = f"POST /assets/{owned.asset_id}/market-data/wipe as user A, the SPLIT {split_id} linked to nothing, the dividend {dividend_id} linked to the transaction {dividend_tx_id}"

    response = await _route(owned.user_a_id, "POST", _wipe_path(owned.asset_id))

    expected = _summary(prices=1, manual=1, kept=1, linked=1, priced=99, dry_run=False)
    assert (response.status_code, _body(response)) == (200, expected), f"{story} answers {response.status_code} {response.text}: expected 200 and {expected}"
    await _assert_wiped_keeping(owned, before, story, kept_events=[split_id], disconnected={dividend_tx_id})


@pytest.mark.asyncio
async def test_another_assets_split_neither_changes_the_counters_nor_is_touched(owned):
    """Red today (counters): the other asset has a SPLIT of 2 (day 120) with a costless ADJUSTMENT +10 on broker A; the wiped
    asset a SPLIT of 2 nothing links to and a price. Today the wiped asset's SPLIT is counted as a manual event and deleted.

    Contract: 1 price, no event that goes, ``splits_kept`` 1 (the wiped asset's, never the other's), ``linked_tx`` 0. The
    other asset's SPLIT and its adjustment, link included, stay as they were, every column."""
    other_split = await _event(owned.other_asset_id, 120, AssetEventType.SPLIT, "2", notes="2-for-1")
    on_other = await _adjustment(owned.other_asset_id, owned.broker_a_id, other_split, 121)
    split_id = await _event(owned.asset_id, 120, AssetEventType.SPLIT, "2")
    await _price(owned.asset_id, 119, "100")
    await _barrier_costless([other_split, split_id], {other_split: [on_other]}, "the other asset's SPLIT with a costless adjustment, beside the wiped asset's SPLIT nothing links to")
    before = await _committed(owned)
    story = f"the wipe of the asset whose SPLIT {split_id} nothing links to, while the other asset's SPLIT {other_split} has the costless adjustment {on_other}"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=0, kept=1, linked=0, priced=119, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected {expected}"
    await _assert_wiped_keeping(owned, before, story, kept_events=[split_id], disconnected=set())


# ─────────────────────────────────────────────────────────────────────────────
# Reds: the currency PATCH does the same in its own call
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_currency_patch_keeps_the_split_removes_the_rest_and_changes_the_currency(owned):
    """Red today (N68): the PATCH answers the block's token (prices=1|events_manual=...), the currency stays EUR, nothing is
    deleted; the user must wipe first, and the wipe is refused while the SPLIT has a costless adjustment.

    Contract: a price, a manual SPLIT with a costless ADJUSTMENT +10, a manual DIVIDEND and a provider INTEREST, each
    linked to a transaction. ``patch_assets_bulk`` for the currency USD answers success, no token; in the same call the
    currency is USD, the price, the dividend and the interest are gone, the SPLIT stays (every column), the adjustment
    stays linked to it and costless, the two other transactions stay with their link NULL. A summary afterwards reads
    ``splits_kept`` 1 and nothing else."""
    case = await _split_beside_a_dividend(owned, 130)
    interest_id = await _event(owned.asset_id, 135, AssetEventType.INTEREST, "0.5", assignment_id=owned.assignment_id)
    interest_tx = await _add(Transaction(broker_id=owned.broker_a_id, asset_id=owned.asset_id, type=TransactionType.INTEREST, date=_day(138), quantity=Decimal("0"), amount=Decimal("5"), currency="EUR", asset_event_id=interest_id))
    before = await _committed(owned)
    story = f"the currency PATCH of the asset whose SPLIT {case.split_id} the costless adjustment {case.adjustment_id} links to, beside the dividend {case.dividend_id}, the provider interest {interest_id} and a price"

    response = await _patch_currency([owned.asset_id], "USD")

    _assert_patched(response, [owned.asset_id], story)
    assert await _currency_of(owned.asset_id) == "USD", f"{story}: the asset's currency is {await _currency_of(owned.asset_id)}: expected USD"
    await _assert_wiped_keeping(owned, before, story, kept_events=[case.split_id], disconnected={case.dividend_tx_id, interest_tx})
    await _still_costless(case.split_id, [case.adjustment_id], story)
    summary = await _wipe_counters(owned, f"the summary after {story}", dry_run=True)
    assert summary == _summary(prices=0, manual=0, kept=1, linked=0, priced=None, dry_run=True), f"the summary after {story} reads {summary}: expected nothing left to lose but the kept SPLIT"


@pytest.mark.asyncio
async def test_the_currency_patch_of_a_batch_is_partial_and_touches_no_other_asset(owned):
    """Red today (N68): the unit's asset (a price, a SPLIT with a costless adjustment) is refused with the token; the other
    asset (a price, its own SPLIT with a costless adjustment) is refused too.

    Contract: one batch with both assets and an id no asset has: the two assets succeed, the unknown one fails by itself
    (a message naming it, no token), and each asset has done what the wipe does: its price gone, its SPLIT and its
    adjustment kept and linked. A second batch for the unit's asset alone leaves the other asset's rows as they were."""
    split_id = await _event(owned.asset_id, 140, AssetEventType.SPLIT, "2")
    on_split = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, 141)
    await _price(owned.asset_id, 139, "100")
    other_split = await _event(owned.other_asset_id, 140, AssetEventType.SPLIT, "2")
    on_other = await _adjustment(owned.other_asset_id, owned.broker_b_id, other_split, 141)
    await _price(owned.other_asset_id, 139, "50")
    await _barrier_costless([split_id, other_split], {split_id: [on_split], other_split: [on_other]}, "two assets, each with a SPLIT and a costless adjustment")
    before = await _committed(owned)
    story = f"the currency PATCH of the assets {owned.asset_id} and {owned.other_asset_id}, each with a SPLIT and a costless adjustment, and of the unknown asset {owned.ghost_asset_id}"

    response = await _patch_currency([owned.asset_id, owned.other_asset_id, owned.ghost_asset_id], "USD")

    _assert_patched(response, owned.asset_ids, story)
    by_id = {result.asset_id: result for result in response.results}
    ghost = by_id.get(owned.ghost_asset_id)
    assert ghost is not None and ghost.success is False and OLD_TOKEN not in (ghost.message or ""), f"{story}: the unknown asset answers {ghost!r}: expected a plain failure of its own"
    after = await _committed(owned)
    assert sorted(_of(after.prices, owned.asset_id)) == [] and sorted(_of(after.prices, owned.other_asset_id)) == [], f"{story}: prices left: {_changes(before, after)}"
    assert sorted(_of(after.events, owned.asset_id)) == [split_id] and sorted(_of(after.events, owned.other_asset_id)) == [other_split], f"{story}: events left: {_changes(before, after)}"
    assert after.transactions == before.transactions, f"{story}: the SPLIT-linked adjustments moved: {_changes(before, after)}"
    assert (await _currency_of(owned.asset_id), await _currency_of(owned.other_asset_id)) == ("USD", "USD"), f"{story}: the currencies are not both USD"


@pytest.mark.asyncio
async def test_guard_a_patch_with_the_same_currency_changes_nothing(owned):
    """Guard: green today and after. The same currency on an asset that has a price, a SPLIT with a costless adjustment and a
    dividend linked to a transaction: success, and nothing, not a price, an event or a link, moves."""
    case = await _split_beside_a_dividend(owned, 150)
    before = await _committed(owned)
    story = f"the PATCH of the unchanged currency EUR of the asset whose SPLIT {case.split_id} the costless adjustment {case.adjustment_id} links to"

    response = await _patch_currency([owned.asset_id], "EUR")

    by_id = {result.asset_id: result for result in response.results}
    assert by_id[owned.asset_id].success is True, f"{story}: answered {by_id[owned.asset_id]!r}"
    after = await _committed(owned)
    assert after == before, f"{story} moved something: {_changes(before, after)}"
    assert await _currency_of(owned.asset_id) == "EUR"


@pytest.mark.asyncio
async def test_guard_an_unknown_asset_is_asset_not_found_and_both_routes_answer_404(owned):
    """Guard: green today and after. An asset id no asset has (the unit's third asset, created and deleted: an id never
    reused): the wipe and its dry run raise ASSET_NOT_FOUND, and ``POST .../market-data/wipe`` and ``GET
    .../market-data/summary`` as user A (in process) answer 404 with the string detail, the service's message."""
    ghost = owned.ghost_asset_id
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        assert await session.get(Asset, ghost) is None, f"barrier: the asset {ghost}, created and deleted by this unit, exists"

    errors = {"wipe": await _not_found(ghost, f"the wipe of the unknown asset {ghost}", dry_run=False), "dry run": await _not_found(ghost, f"the dry run of the unknown asset {ghost}", dry_run=True)}
    answers = {"POST": await _route(owned.user_a_id, "POST", _wipe_path(ghost)), "GET": await _route(owned.user_a_id, "GET", _summary_path(ghost))}

    for name, error in errors.items():
        assert error.error_code == "ASSET_NOT_FOUND", f"the {name} of the unknown asset {ghost} raised {error.error_code} ({error.message}): expected ASSET_NOT_FOUND"
    message = errors["wipe"].message
    for method, response in answers.items():
        body = _body(response)
        detail = body.get("detail") if isinstance(body, dict) else None
        assert (response.status_code, detail) == (404, message), f"{method} on the market data of the unknown asset {ghost} answers {response.status_code} {response.text}: expected the 404 with the string detail {message!r}"
