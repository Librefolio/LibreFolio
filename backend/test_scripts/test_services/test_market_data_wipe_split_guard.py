"""X-R48 (workstream X): ``POST /assets/{asset_id}/market-data/wipe`` deletes the SPLITs that costless incoming
adjustments rely on.

Measured before the cure (read at 90ec69e0f): ``CurrencyChangeOperations.wipe_market_data_for_currency_change``
(``services/assets/currency_change.py``, reached as ``AssetSourceManager.wipe_market_data_for_currency_change``) counts,
then, unless it is the dry run, sets ``transactions.asset_event_id = NULL`` for every transaction linked to an event of
the asset, deletes every event of the asset, manual and provider, SPLITs included, and every price, and commits. Linked
to a SPLIT, an incoming ADJUSTMENT needs no cost of its own: it only rescales the position, and the Auto mode stores none
(``financial_math.splits.costless_incoming_split_adjustments`` lists those rows). Disconnected by the wipe, it becomes an
acquisition of unknown cost: ``MISSING_COST_BASIS`` on the Dashboard and in the lots. The asset is global: any user can
call the wipe, and the adjustments it disconnects may sit on another user's broker. The route
(``api/v1/assets/market_data.py``) answers every ``AssetSourceError`` 404 (``ASSET_NOT_FOUND``) or 400 with
``detail=str(e)``; and the wipe knows no caller: given a ``current_user_id``, it raises ``TypeError``.

The cure's contract (X-R48: J's P-10 guard, decision 27, applied to the wipe):

* ``wipe_market_data_for_currency_change(asset_id, session, dry_run=False, *, current_user_id=None)``; the route passes
  ``current_user_id=_current_user.id``;
* in the real wipe only, before any write: when at least one SPLIT of the asset, manual or provider, has costless
  incoming adjustments, ``AssetSourceError`` ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST``, its ``details`` exactly
  ``{"splits": [...]}``: one entry per such SPLIT, ordered by (event date, event id), each exactly ``{"event_id",
  "date" (the event's, ISO), "transaction_ids", "hidden_transactions_count"}``: ``transaction_ids`` the adjustments the
  caller can see, sorted (a ``BrokerUserAccess`` row of ``current_user_id`` for the transaction's broker, as P-10 decides
  since R13-SEC7), ``hidden_transactions_count`` the others; without a ``current_user_id`` none is named and all are
  counted (fail closed, as X-R47b). The message gives the totals only (how many SPLITs, how many adjustments), never an
  id, whoever asks. Nothing is written: prices, events (every column, ``updated_at`` included) and every transaction (its
  ``asset_event_id`` above all) as they were, nothing committed;
* the route answers it 409, ``detail`` exactly ``{"error_code", "message", "params": {"splits": [...]}}``, the caller's
  view; every other error keeps today's answer (404 ``ASSET_NOT_FOUND``, a string detail);
* the summary (``dry_run=True``, ``GET …/market-data/summary``) never refuses: today's counters.

Guards, green before and after: an incoming adjustment with a cost (0 included), an outgoing one without, a SPLIT nothing
links to beside a DIVIDEND linked to a transaction, another asset's SPLIT with a costless adjustment: the wipe proceeds as
today, the asset's events and prices gone, the linked transactions kept and disconnected, nothing else touched; the
summary of the refused case; an unknown asset.

A refusal is looked for as the router meets it: nobody commits after a refused call, the session just closes. The refused
call's own session is read right after it (raw SQL, so a write made before the refusal shows, committed or not) and, once
that session is closed, a fresh connection reads what is committed; every column, ``updated_at`` included. A call that
raises today where the contract refuses (the ``TypeError`` of the unknown keyword) fails its test naming the exception,
never as an error; a wipe that proceeds fails its test with what it deleted and disconnected. The route tests call the
route in process: the market-data router mounted at ``/api/v1/assets`` as the app mounts it, on an app of the call's own,
``get_current_user`` overridden there to the unit's user, the session the real dependency opens; the answer read as the
client reads it, JSON. Each red says what the user faces before the cure («Red today»); a guard passes before and after.

Isolation: WRITE-SCOPED, the services default. Every row is this unit's own: two EUR STOCK assets created under a unique
name, the one wiped (assigned to a provider code of the unit's own that no provider has: its provider SPLITs need one,
nothing is fetched) and another, plus a third created and deleted at once, whose id no asset has or will have
(AUTOINCREMENT); two users and two brokers under the same marker, user A holding an access to broker A alone, user B to
broker B alone. Only the events and prices of those assets and the transactions on those brokers are written, read and
wiped, by asset and broker id. Nothing here counts or reads a row it did not write.
"""

import asyncio
import re
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
from sqlalchemy import bindparam, delete, or_, select, text
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
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.financial_math.splits import costless_incoming_split_adjustments
from backend.test_scripts.test_utils import unique_id

#: The refusal's code (X-R48).
CODE = "MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST"

# A window far from the mock dataset and from the other split units (1990, 1991-1992, 1994-1995). Rows are scoped by
# asset and broker anyway: the dates only keep the failure output readable.
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
    price of its assets. Bulk deletes: no row is loaded."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(Transaction).where(Transaction.broker_id.in_(owned.broker_ids)))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)))
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned.asset_ids)))
        await session.commit()


@pytest.fixture(scope="module")
def owned_module() -> _Owned:
    """The assets, the assignment, the users, the brokers and the accesses, under names no concurrent worker can repeat,
    dropped in FK-safe order in teardown with every event, price and transaction written against them. The provider code
    is no provider's: nothing is ever fetched for it. The third asset is deleted in the same transaction that writes the
    accesses: its id stays unknown for good, ``assets`` being AUTOINCREMENT."""
    marker = f"{unique_id('XR48')}_{uuid.uuid4().hex[:8]}"

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            wiped = Asset(display_name=f"X-R48 Wiped {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            other = Asset(display_name=f"X-R48 Other {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            ghost = Asset(display_name=f"X-R48 Ghost {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            user_a = User(username=f"xr48a_{marker}".lower(), email=f"xr48a_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            user_b = User(username=f"xr48b_{marker}".lower(), email=f"xr48b_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            broker_a = Broker(name=f"X-R48 A {marker}")
            broker_b = Broker(name=f"X-R48 B {marker}")
            session.add_all([wiped, other, ghost, user_a, user_b, broker_a, broker_b])
            await session.commit()
            ghost_id = ghost.id
            await session.execute(delete(Asset).where(Asset.id == ghost_id))
            assignment = AssetProviderAssignment(asset_id=wiped.id, provider_code=f"xr48_{uuid.uuid4().hex[:12]}", identifier=f"XR48.{marker}", identifier_type=ProviderInputType.TICKER)
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
    """The module's rows, with no event, no price and no transaction before and after the test."""
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
    the refusal, or its absence, is about those rows."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        costless = await costless_incoming_split_adjustments(session, event_ids)
    assert costless == expected, f"barrier: {story}: the layer lists {costless} as the costless incoming adjustments of the SPLITs among the events {event_ids}, not {expected}"


async def _barrier_who_sees_what(owned: _Owned) -> None:
    """Barrier: of the unit's brokers, user A holds an access to broker A alone and user B to broker B alone, so a refusal
    naming one adjustment and counting another is about who sees what."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(select(BrokerUserAccess.user_id, BrokerUserAccess.broker_id).where(BrokerUserAccess.broker_id.in_(owned.broker_ids)))).all()
    held = sorted((user_id, broker_id) for user_id, broker_id in rows)
    expected = sorted([(owned.user_a_id, owned.broker_a_id), (owned.user_b_id, owned.broker_b_id)])
    assert held == expected, f"barrier: the accesses to the unit's brokers are {held} as (user, broker): expected {expected}, user A on broker A alone, user B on broker B alone"


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
    """``_State`` through ``session``, with raw SQL: a session that wrote reads its own writes, committed or not."""
    assets, brokers = {"asset_ids": owned.asset_ids}, {"broker_ids": owned.broker_ids}
    prices = (await session.execute(_RAW_PRICES, assets)).mappings().all()
    events = (await session.execute(_RAW_EVENTS, assets)).mappings().all()
    transactions = (await session.execute(_RAW_TRANSACTIONS, brokers)).mappings().all()
    return _State(prices=_by_id(prices), events=_by_id(events), transactions=_by_id(transactions))


async def _committed(owned: _Owned) -> _State:
    """What is committed: ``_State`` read on a fresh connection (the engine pools none)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await _read(session, owned)


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
# The service, called as the route calls it
# --------------------------------------------------------------------------- #


async def _refused_wipe(owned: _Owned, before: _State, story: str, **caller: int) -> tuple[AssetSourceError, _State]:
    """The real wipe of the unit's asset, for a call the contract refuses, ``caller`` the ``current_user_id`` it is given
    if any: the refusal, and what the refused call's own session reads right after it, its writes included, committed or
    not. As in the route, nobody commits after it: the session closes. Any other exception fails the test, naming it (the
    ``TypeError`` of the unknown keyword before the cure); so does a wipe that goes through, saying what it deleted and
    disconnected against ``before``."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            counters = await AssetSourceManager.wipe_market_data_for_currency_change(asset_id=owned.asset_id, session=session, dry_run=False, **caller)
        except AssetSourceError as refusal:
            return refusal, await _read(session, owned)
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            given = f" (X-R48: the wipe takes the caller as the keyword current_user_id, here {caller})" if caller else ""
            pytest.fail(
                f"{story} raised {exc!r} instead of the refusal {CODE}{given}. Today the route calls the wipe without a caller and the wipe goes through: it deletes every SPLIT of the asset and disconnects the adjustments linked to them, and a costless incoming one becomes an acquisition of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots)"
            )
    pytest.fail(
        f"{story} went through ({counters}) instead of being refused with {CODE}: {_changes(before, await _committed(owned))}. Each costless incoming adjustment disconnected from its SPLIT is now an acquisition of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots), on whichever user's broker it sits"
    )


async def _wipe_counters(owned: _Owned, story: str, *, dry_run: bool = False) -> dict:
    """The wipe of the unit's asset, or its dry run, for a call that must go through, without a caller as the route calls
    it today: its counters. A refusal, or any other exception, fails the test, naming it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            return await AssetSourceManager.wipe_market_data_for_currency_change(asset_id=owned.asset_id, session=session, dry_run=dry_run)
        except AssetSourceError as refusal:
            pytest.fail(f"{story} was refused: {refusal.error_code} {refusal.message} {refusal.details} (X-R48 refuses only the real wipe of an asset with a SPLIT whose incoming adjustments have no cost)")
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
    mounts it (``asset_router`` includes it under ``/assets``, the app the v1 router under ``/api/v1``), on an app of the
    call's own, so ``get_current_user`` is overridden there, never on the shared app, with the session the real
    dependency opens on the lane's database. Nothing is mocked behind the route."""
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


def _detail(response: httpx.Response) -> dict:
    """The structured ``detail`` of an answer: {} when the body holds no object there (a 200, today's string detail, a
    500's text)."""
    body = _body(response)
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, dict) else {}


# --------------------------------------------------------------------------- #
# What the contract expects
# --------------------------------------------------------------------------- #


def _entry(event_id: int, offset: int, seen: list[int], hidden: int) -> dict:
    """One SPLIT of the refusal, as the contract gives it: the event, its date, the adjustments the caller sees, how many
    it does not."""
    return {"event_id": event_id, "date": _day(offset).isoformat(), "transaction_ids": seen, "hidden_transactions_count": hidden}


def _assert_splits(splits: object, expected: list[dict], story: str, where: str) -> None:
    """``splits`` (the refusal's ``details["splits"]`` or the 409's ``params["splits"]``) is exactly ``expected``: the same
    SPLITs in the same order, each entry exactly the expected one."""
    entries = splits if isinstance(splits, list) else []
    order = [entry.get("event_id") if isinstance(entry, dict) else entry for entry in entries]
    wanted = [entry["event_id"] for entry in expected]
    assert isinstance(splits, list) and order == wanted, f"{story}: {where} lists the SPLITs {order} ({splits!r}): expected {wanted}, each SPLIT with costless incoming adjustments once, ordered by (event date, event id)"
    for found, entry in zip(entries, expected, strict=True):
        assert found == entry, f"{story}: {where} gives the SPLIT {entry['event_id']} as {found}: expected exactly {entry}: the event's date, the adjustments the caller can see on their brokers (sorted), the others counted, no other key (which could carry a hidden id)"


def _assert_refused(refusal: AssetSourceError, expected: list[dict], story: str) -> None:
    """The refusal is ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST`` and its details are exactly ``{"splits": expected}``."""
    assert refusal.error_code == CODE, f"{story} was refused with {refusal.error_code} ({refusal.message}), not {CODE}: {refusal.details}"
    details = refusal.details if isinstance(refusal.details, dict) else {}
    assert sorted(details) == ["splits"], f"{story}: the refusal's details hold the keys {sorted(details)}: expected exactly ['splits'], another key could carry a hidden id: {refusal.details}"
    _assert_splits(details["splits"], expected, story, "the refusal")


# A whole number in a text: not part of a word, a date, a decimal or a signed figure ("P-10", "1988-04-04", "X-R48" hold
# none).
_WHOLE_NUMBER = re.compile(r"(?<![\w.+-])\d+(?![\w.+-])")


def _assert_totals_only(message: object, story: str, owned: _Owned, *, splits: int, adjustments: int, ids: Collection[int]) -> None:
    """The refusal's message gives the totals (how many SPLITs, how many adjustments, as whole numbers) and names no
    event or transaction id of the case: whoever reads it, it carries nothing the details filter. An id that reads as a
    total or as the asset's id cannot be told from them, so it is not looked for."""
    assert isinstance(message, str) and message.strip(), f"{story}: the refusal's message is {message!r}: expected a text"
    numbers = {int(number) for number in _WHOLE_NUMBER.findall(message)}
    named = sorted((set(ids) & numbers) - {splits, adjustments, owned.asset_id})
    assert not named, f"{story}: the message {message!r} names the id(s) {named}: expected the totals only, never an id (X-R48); a hidden adjustment's id would reach a user who cannot see its broker"
    missing = sorted({splits, adjustments} - numbers)
    assert not missing, f"{story}: the message {message!r} lacks the total(s) {missing}: expected how many SPLITs ({splits}) and how many adjustments ({adjustments}) (X-R48: the totals only)"


async def _assert_nothing_written(owned: _Owned, before: _State, seen_by_its_session: _State, story: str) -> None:
    """Refused before any write: the refused call's own session reads ``before``; and nothing committed: once that session
    is closed, a fresh connection reads ``before`` too. Every column, ``updated_at`` included."""
    assert seen_by_its_session == before, f"{story} was refused after writing: its own session reads {_changes(before, seen_by_its_session)} (X-R48: refused before any write)"
    after = await _committed(owned)
    assert after == before, f"{story} was refused, yet the database changed: {_changes(before, after)}"


def _summary(*, prices: int, manual: int, linked: int, priced: int | None, dry_run: bool) -> dict:
    """The wipe's counters as today, for ``prices`` prices all on day ``priced`` (none: no day), ``manual`` manual events,
    no provider event and ``linked`` linked transactions."""
    day = None if priced is None else _day(priced).isoformat()
    return {"prices": prices, "events_manual": manual, "events_provider": 0, "linked_tx": linked, "oldest": day, "newest": day, "dry_run": dry_run}


def _unlinked(row: dict) -> dict:
    """A transaction row as the wipe leaves a disconnected one: its link NULL, ``updated_at`` left out (the contract does
    not fix it)."""
    return {key: (None if key == "asset_event_id" else value) for key, value in row.items() if key != "updated_at"}


def _undated(row: dict) -> dict:
    """A transaction row with ``updated_at`` left out."""
    return {key: value for key, value in row.items() if key != "updated_at"}


async def _assert_wiped(owned: _Owned, before: _State, story: str, *, disconnected: Collection[int]) -> None:
    """What the wipe does today, and still does when it goes through: no event and no price of the wiped asset left, the
    other asset's as they were; every transaction on the unit's brokers kept, the ``disconnected`` ones with their link
    NULL and every other column as before (``updated_at`` aside), the others untouched, every column."""
    after = await _committed(owned)
    left = (sorted(_of(after.events, owned.asset_id)), sorted(_of(after.prices, owned.asset_id)))
    assert left == ([], []), f"{story}: the wipe left the asset's events {left[0]} and prices {left[1]}: expected none, as today"
    other = (_of(after.events, owned.other_asset_id), _of(after.prices, owned.other_asset_id))
    assert other == (_of(before.events, owned.other_asset_id), _of(before.prices, owned.other_asset_id)), f"{story}: the other asset's events or prices changed: {_changes(before, after)}"
    expected = {tx_id: (_unlinked(row) if tx_id in disconnected else row) for tx_id, row in before.transactions.items()}
    found = {tx_id: (_undated(row) if tx_id in disconnected else row) for tx_id, row in after.transactions.items()}
    assert found == expected, f"{story}: the transactions on the unit's brokers moved as {_changes(before, after)}: expected {sorted(disconnected)} kept and disconnected, every other transaction untouched"


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

    @property
    def ids(self) -> list[int]:
        """Every event and transaction id of the case: what the refusal's message never names."""
        return [self.split_id, self.adjustment_id, self.dividend_id, self.dividend_tx_id]


async def _split_beside_a_dividend(owned: _Owned, offset: int) -> _SplitBesideADividend:
    """On the wiped asset: a price (day ``offset - 1``); a manual SPLIT of 2 (day ``offset``) with a costless ADJUSTMENT
    +10 linked on broker A, booked the next day; a DIVIDEND of 1.5 EUR (day ``offset + 5``) linked to a DIVIDEND of 15 EUR
    on broker A (day ``offset + 7``). Barriers: P-10's layer lists the adjustment alone, and user A holds broker A."""
    await _price(owned.asset_id, offset - 1, "100")
    split_id = await _event(owned.asset_id, offset, AssetEventType.SPLIT, "2", notes="2-for-1")
    dividend_id = await _event(owned.asset_id, offset + 5, AssetEventType.DIVIDEND, "1.5")
    adjustment_id = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, offset + 1)
    dividend_tx_id = await _dividend(owned.asset_id, owned.broker_a_id, dividend_id, offset + 7, "15")
    await _barrier_costless([split_id, dividend_id], {split_id: [adjustment_id]}, "a SPLIT with a costless adjustment, beside a linked dividend")
    await _barrier_who_sees_what(owned)
    return _SplitBesideADividend(split_id=split_id, adjustment_id=adjustment_id, dividend_id=dividend_id, dividend_tx_id=dividend_tx_id)


@dataclass(frozen=True)
class _SplitOnTwoBrokers:
    """A SPLIT with a costless adjustment on each of the unit's brokers."""

    split_id: int
    on_a: int  # on broker A: user A sees it, user B does not
    on_b: int  # on broker B: user B sees it, user A does not

    @property
    def ids(self) -> list[int]:
        """Every event and transaction id of the case: what the refusal's message never names."""
        return [self.split_id, self.on_a, self.on_b]


async def _split_on_two_brokers(owned: _Owned, offset: int) -> _SplitOnTwoBrokers:
    """On the wiped asset: a manual SPLIT of 2 (day ``offset``) with a costless ADJUSTMENT +10 linked on broker B, then one
    on broker A, both booked the next day. Broker B's is written first, so the one user A cannot see has the lower id and
    a positional filter would show it. Barriers: P-10's layer lists both, user A holds broker A alone, user B broker B
    alone."""
    split_id = await _event(owned.asset_id, offset, AssetEventType.SPLIT, "2", notes="2-for-1")
    on_b = await _adjustment(owned.asset_id, owned.broker_b_id, split_id, offset + 1)
    on_a = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, offset + 1)
    await _barrier_costless([split_id], {split_id: sorted([on_b, on_a])}, "a SPLIT with a costless adjustment on each broker")
    await _barrier_who_sees_what(owned)
    return _SplitOnTwoBrokers(split_id=split_id, on_a=on_a, on_b=on_b)


# ─────────────────────────────────────────────────────────────────────────────
# Reds: the real wipe refuses while a SPLIT of the asset has costless incoming adjustments
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_wipe_refuses_a_split_with_a_costless_incoming_adjustment_and_writes_nothing(owned):
    """Red today (X-R48): the wipe takes no ``current_user_id`` (TypeError). Called without one, as the route calls it, it
    goes through: it deletes the SPLIT of 2, the dividend and the price, and disconnects the costless ADJUSTMENT +10,
    which becomes an acquisition of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots).

    Contract: as user A, who holds an access to the adjustment's broker, the real wipe is refused with
    MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST, its details exactly ``{"splits": [{event_id, date (day 10),
    transaction_ids [the adjustment], hidden_transactions_count 0}]}``, its message the totals only (1 SPLIT, 1
    adjustment); refused before any write: the refused call's own session still reads the price, both events and the
    links of both transactions, the adjustment's and the dividend's, and nothing is committed (every column, ``updated_at``
    included).
    """
    case = await _split_beside_a_dividend(owned, 10)
    before = await _committed(owned)
    story = f"user A wiping the market data of the asset whose SPLIT {case.split_id} of {_day(10)} the costless adjustment {case.adjustment_id} (broker A, theirs) links to, beside the dividend {case.dividend_id} linked to the transaction {case.dividend_tx_id} and a price"

    refusal, seen_by_its_session = await _refused_wipe(owned, before, story, current_user_id=owned.user_a_id)

    _assert_refused(refusal, [_entry(case.split_id, 10, [case.adjustment_id], 0)], story)
    _assert_totals_only(refusal.message, story, owned, splits=1, adjustments=1, ids=case.ids)
    await _assert_nothing_written(owned, before, seen_by_its_session, story)


@pytest.mark.asyncio
async def test_the_refusal_lists_every_such_split_by_its_date(owned):
    """Red today (X-R48): the wipe takes no ``current_user_id`` (TypeError). Called without one, as the route calls it, it
    deletes both SPLITs and disconnects both costless adjustments: two acquisitions of unknown cost.

    Contract: two SPLITs of 2, each with a costless ADJUSTMENT +10 on broker A, written out of date order: the SPLIT of
    day 30 and its adjustment (booked day 31) first, then the SPLIT of day 20 and its adjustment (booked day 34). Their
    event ids, their adjustments' ids and their adjustments' dates all give the other order. As user A the refusal lists
    both by the event's date, day 20 then day 30, each with its adjustment and 0 hidden; its message the totals only (2
    SPLITs, 2 adjustments); nothing written.
    """
    later = await _event(owned.asset_id, 30, AssetEventType.SPLIT, "2")
    on_later = await _adjustment(owned.asset_id, owned.broker_a_id, later, 31)
    earlier = await _event(owned.asset_id, 20, AssetEventType.SPLIT, "2")
    on_earlier = await _adjustment(owned.asset_id, owned.broker_a_id, earlier, 34)
    await _barrier_costless([later, earlier], {later: [on_later], earlier: [on_earlier]}, "two SPLITs written out of date order")
    await _barrier_who_sees_what(owned)
    before = await _committed(owned)
    story = f"user A wiping the market data of the asset whose SPLITs {later} of {_day(30)} and {earlier} of {_day(20)}, written in that order, the costless adjustments {on_later} and {on_earlier} (broker A) link to"

    refusal, seen_by_its_session = await _refused_wipe(owned, before, story, current_user_id=owned.user_a_id)

    _assert_refused(refusal, [_entry(earlier, 20, [on_earlier], 0), _entry(later, 30, [on_later], 0)], story)
    _assert_totals_only(refusal.message, story, owned, splits=2, adjustments=2, ids=[later, earlier, on_later, on_earlier])
    await _assert_nothing_written(owned, before, seen_by_its_session, story)


@pytest.mark.asyncio
async def test_a_provider_split_counts_and_splits_of_one_day_follow_their_ids(owned):
    """Red today (X-R48): the wipe takes no ``current_user_id`` (TypeError). Called without one, as the route calls it, it
    deletes the provider's SPLIT with the manual one (it deletes every event of the asset) and disconnects both costless
    adjustments.

    Contract: the wipe deletes provider events too, so a provider SPLIT is guarded as a manual one is; and SPLITs of one
    day follow their event ids. A provider SPLIT of day 40, written first, then a manual SPLIT of the same day, each with
    a costless ADJUSTMENT +10 on broker A; the manual one's adjustment is written first and booked first (day 41, the
    provider one's day 42), so the adjustments' ids and dates give the other order. As user A the refusal lists the
    provider SPLIT, then the manual one, each with its adjustment and 0 hidden; its message the totals only (2 SPLITs, 2
    adjustments); nothing written.
    """
    provider = await _event(owned.asset_id, 40, AssetEventType.SPLIT, "2", assignment_id=owned.assignment_id)
    manual = await _event(owned.asset_id, 40, AssetEventType.SPLIT, "2", notes="2-for-1")
    on_manual = await _adjustment(owned.asset_id, owned.broker_a_id, manual, 41)
    on_provider = await _adjustment(owned.asset_id, owned.broker_a_id, provider, 42)
    await _barrier_costless([provider, manual], {provider: [on_provider], manual: [on_manual]}, "a provider SPLIT and a manual SPLIT of one day")
    await _barrier_who_sees_what(owned)
    before = await _committed(owned)
    story = f"user A wiping the market data of the asset whose provider SPLIT {provider} and manual SPLIT {manual}, both of {_day(40)}, the costless adjustments {on_provider} and {on_manual} (broker A) link to"

    refusal, seen_by_its_session = await _refused_wipe(owned, before, story, current_user_id=owned.user_a_id)

    _assert_refused(refusal, [_entry(provider, 40, [on_provider], 0), _entry(manual, 40, [on_manual], 0)], story)
    _assert_totals_only(refusal.message, story, owned, splits=2, adjustments=2, ids=[provider, manual, on_provider, on_manual])
    await _assert_nothing_written(owned, before, seen_by_its_session, story)


@pytest.mark.asyncio
async def test_the_refusal_shows_each_caller_only_the_adjustments_on_their_brokers(owned):
    """Red today (X-R48): the wipe takes no ``current_user_id`` (TypeError). Called without one, as the route calls it, it
    disconnects both adjustments whoever asks: user A, who cannot see broker B, turns user B's adjustment into an
    acquisition of unknown cost.

    Contract (R13-SEC7's rule, as P-10): a SPLIT of 2 (day 50) with a costless ADJUSTMENT +10 on broker B, written first so
    that a positional filter would show it, and one on broker A. As user A the refusal's one entry shows [broker A's] and
    counts 1 hidden; as user B, [broker B's] and 1 hidden. The message is the same for both and for a call without a
    caller: the totals only (1 SPLIT, 2 adjustments), naming neither adjustment. None of the three writes anything.
    """
    case = await _split_on_two_brokers(owned, 50)
    before = await _committed(owned)
    story = f"wiping the market data of the asset whose SPLIT {case.split_id} of {_day(50)} the costless adjustments {case.on_b} (broker B, written first) and {case.on_a} (broker A) link to"

    as_a, seen_a = await _refused_wipe(owned, before, f"user A {story}", current_user_id=owned.user_a_id)
    _assert_refused(as_a, [_entry(case.split_id, 50, [case.on_a], 1)], f"user A {story}")
    await _assert_nothing_written(owned, before, seen_a, f"user A {story}")
    as_b, seen_b = await _refused_wipe(owned, before, f"user B {story}", current_user_id=owned.user_b_id)
    _assert_refused(as_b, [_entry(case.split_id, 50, [case.on_b], 1)], f"user B {story}")
    await _assert_nothing_written(owned, before, seen_b, f"user B {story}")
    unknown, seen_unknown = await _refused_wipe(owned, before, f"a call without a caller {story}")
    await _assert_nothing_written(owned, before, seen_unknown, f"a call without a caller {story}")

    messages = {"user A": as_a.message, "user B": as_b.message, "no caller": unknown.message}
    assert len(set(messages.values())) == 1, f"{story}: the message depends on who asks: {messages} (X-R48: the totals only, whoever asks)"
    _assert_totals_only(as_a.message, story, owned, splits=1, adjustments=2, ids=case.ids)


@pytest.mark.asyncio
async def test_without_a_caller_the_refusal_names_no_adjustment_and_counts_them_all(owned):
    """Red today (X-R48): not refused. Called without a caller, as the route calls it today, the wipe deletes the SPLIT and
    disconnects both costless adjustments, each now an acquisition of unknown cost on its broker.

    Contract (fail closed, as X-R47b): without a ``current_user_id`` the wipe knows no user who may see either adjustment:
    refused, the SPLIT (day 60) its one entry with ``transaction_ids`` [] and ``hidden_transactions_count`` 2; its message
    the totals only (1 SPLIT, 2 adjustments); nothing written.
    """
    case = await _split_on_two_brokers(owned, 60)
    before = await _committed(owned)
    story = f"a call without a caller wiping the market data of the asset whose SPLIT {case.split_id} of {_day(60)} the costless adjustments {case.on_b} (broker B) and {case.on_a} (broker A) link to"

    refusal, seen_by_its_session = await _refused_wipe(owned, before, story)

    _assert_refused(refusal, [_entry(case.split_id, 60, [], 2)], story)
    _assert_totals_only(refusal.message, story, owned, splits=1, adjustments=2, ids=case.ids)
    await _assert_nothing_written(owned, before, seen_by_its_session, story)


@pytest.mark.asyncio
async def test_the_wipe_endpoint_answers_409_with_the_callers_view_and_writes_nothing(owned):
    """Red today (X-R48): 200, the wipe done. As user A: the SPLIT and the price deleted, both costless adjustments
    disconnected, user B's too, on a broker user A cannot see: each now an acquisition of unknown cost.

    Contract: ``POST /assets/{id}/market-data/wipe`` as user A (in process), the asset holding a price and a SPLIT of 2 (day
    70) with a costless ADJUSTMENT +10 on broker B, then one on broker A: 409, ``detail`` exactly {``error_code``
    MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST, ``message`` (the totals only: 1 SPLIT, 2 adjustments), ``params``
    {"splits": [{event_id, date, transaction_ids [broker A's], hidden_transactions_count 1}]}}, user A's view; nothing
    written.
    """
    case = await _split_on_two_brokers(owned, 70)
    await _price(owned.asset_id, 69, "100")
    before = await _committed(owned)
    story = f"POST /assets/{owned.asset_id}/market-data/wipe as user A, the SPLIT {case.split_id} of {_day(70)} linked to the costless adjustments {case.on_b} (broker B, user B's) and {case.on_a} (broker A, theirs)"

    response = await _route(owned.user_a_id, "POST", _wipe_path(owned.asset_id))

    if response.status_code == 200:
        pytest.fail(
            f"{story} answered 200 {response.text} and wiped: {_changes(before, await _committed(owned))}. User B's adjustment {case.on_b}, on a broker user A cannot see, and user A's {case.on_a} are now acquisitions of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots); expected 409 {CODE}"
        )
    detail = _detail(response)
    assert (response.status_code, detail.get("error_code")) == (409, CODE), f"{story} answers {response.status_code} {response.text}: expected 409 {CODE}"
    assert sorted(detail) == ["error_code", "message", "params"], f"{story}: the 409's detail holds the keys {sorted(detail)}: expected exactly error_code, message and params: {detail}"
    _assert_totals_only(detail["message"], story, owned, splits=1, adjustments=2, ids=case.ids)
    params = detail["params"]
    assert isinstance(params, dict) and sorted(params) == ["splits"], f"{story}: the 409's params are {params!r}: expected exactly the key splits, another key could carry a hidden id"
    _assert_splits(params["splits"], [_entry(case.split_id, 70, [case.on_a], 1)], story, "the 409")
    after = await _committed(owned)
    assert after == before, f"{story} was refused, yet the database changed: {_changes(before, after)}"


# ─────────────────────────────────────────────────────────────────────────────
# Guards: green before and after the cure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("cost", [pytest.param("12.5", id="cost-12.5"), pytest.param("0", id="cost-0")])
async def test_guard_a_split_whose_incoming_adjustment_has_a_cost_is_wiped(owned, cost):
    """Guard: green today and after. A SPLIT of 2 (day 80) with an ADJUSTMENT +10 linked that has a cost, ``cost`` EUR a
    unit (0 is a cost, not a missing one), and a price: P-10's layer lists nothing, so the wipe goes through as today: its
    counters (1 price, 1 manual event, 1 linked transaction), the SPLIT and the price gone, the adjustment kept and
    disconnected."""
    split_id = await _event(owned.asset_id, 80, AssetEventType.SPLIT, "2")
    adjustment_id = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, 81, cost=cost)
    await _price(owned.asset_id, 79, "100")
    await _barrier_costless([split_id], {}, f"a SPLIT whose incoming adjustment costs {cost} EUR a unit")
    before = await _committed(owned)
    story = f"the wipe of the asset whose SPLIT {split_id} the adjustment {adjustment_id} (+10, {cost} EUR a unit) links to"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=1, linked=1, priced=79, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected today's counters {expected}"
    await _assert_wiped(owned, before, story, disconnected={adjustment_id})


@pytest.mark.asyncio
async def test_guard_a_split_with_an_outgoing_costless_adjustment_is_wiped(owned):
    """Guard: green today and after. A reverse SPLIT of 0.5 (day 90) with an ADJUSTMENT -10 linked, without a cost, and a
    price: without its SPLIT an outgoing row is a reduction at average cost, which needs no cost, so P-10's layer lists
    nothing and the wipe goes through as today: its counters, the SPLIT and the price gone, the adjustment kept and
    disconnected."""
    split_id = await _event(owned.asset_id, 90, AssetEventType.SPLIT, "0.5", notes="1-for-2")
    adjustment_id = await _adjustment(owned.asset_id, owned.broker_a_id, split_id, 91, quantity="-10")
    await _price(owned.asset_id, 89, "100")
    await _barrier_costless([split_id], {}, "a reverse SPLIT with an outgoing costless adjustment")
    before = await _committed(owned)
    story = f"the wipe of the asset whose reverse SPLIT {split_id} the outgoing costless adjustment {adjustment_id} (-10) links to"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=1, linked=1, priced=89, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected today's counters {expected}"
    await _assert_wiped(owned, before, story, disconnected={adjustment_id})


@pytest.mark.asyncio
async def test_guard_the_endpoint_wipes_a_split_nothing_links_to_and_disconnects_a_dividend(owned):
    """Guard: green today and after. A SPLIT of 2 nothing links to (day 100), a DIVIDEND of 1.5 EUR (day 101) linked to a
    DIVIDEND transaction on broker A, and a price: ``POST …/market-data/wipe`` as user A (in process) answers 200 with
    today's counters (1 price, 2 manual events, 1 linked transaction); the events and the price are gone, the dividend's
    transaction kept and disconnected. Through the route: once it passes its caller, this answer must not change."""
    split_id = await _event(owned.asset_id, 100, AssetEventType.SPLIT, "2")
    dividend_id = await _event(owned.asset_id, 101, AssetEventType.DIVIDEND, "1.5")
    dividend_tx_id = await _dividend(owned.asset_id, owned.broker_a_id, dividend_id, 103, "15")
    await _price(owned.asset_id, 99, "100")
    await _barrier_costless([split_id, dividend_id], {}, "a SPLIT nothing links to, beside a linked dividend")
    before = await _committed(owned)
    story = f"POST /assets/{owned.asset_id}/market-data/wipe as user A, the SPLIT {split_id} linked to nothing, the dividend {dividend_id} linked to the transaction {dividend_tx_id}"

    response = await _route(owned.user_a_id, "POST", _wipe_path(owned.asset_id))

    expected = _summary(prices=1, manual=2, linked=1, priced=99, dry_run=False)
    assert (response.status_code, _body(response)) == (200, expected), f"{story} answers {response.status_code} {response.text}: expected 200 and today's counters {expected}"
    await _assert_wiped(owned, before, story, disconnected={dividend_tx_id})


@pytest.mark.asyncio
async def test_guard_the_summary_counts_the_refused_case_and_never_refuses(owned):
    """Guard: green today and after. The case the real wipe refuses (``_split_beside_a_dividend``, day 110): the dry run
    and ``GET …/market-data/summary`` as user A (in process) answer today's counters (1 price, 2 manual events, no
    provider event, 2 linked transactions, the price's day as oldest and newest, ``dry_run`` true) and write nothing: the
    summary only counts, it never refuses."""
    case = await _split_beside_a_dividend(owned, 110)
    before = await _committed(owned)
    expected = _summary(prices=1, manual=2, linked=2, priced=109, dry_run=True)
    story = f"the summary of the asset whose SPLIT {case.split_id} the costless adjustment {case.adjustment_id} links to, beside the dividend {case.dividend_id} and a price"

    counters = await _wipe_counters(owned, f"the dry run, {story}", dry_run=True)
    response = await _route(owned.user_a_id, "GET", _summary_path(owned.asset_id))

    assert counters == expected, f"the dry run, {story}, answers {counters}: expected today's counters {expected}"
    assert (response.status_code, _body(response)) == (200, expected), f"GET /assets/{owned.asset_id}/market-data/summary as user A, {story}, answers {response.status_code} {response.text}: expected 200 and today's counters {expected}"
    after = await _committed(owned)
    assert after == before, f"{story} wrote: {_changes(before, after)}"


@pytest.mark.asyncio
async def test_guard_an_unknown_asset_is_asset_not_found_and_both_routes_answer_404(owned):
    """Guard: green today and after. An asset id no asset has (the unit's third asset, created and deleted: an id never
    reused): the wipe and its dry run raise ASSET_NOT_FOUND, and ``POST …/market-data/wipe`` and ``GET
    …/market-data/summary`` as user A (in process) answer 404 with today's string detail, the service's message. The
    cure's 409 is its refusal's alone."""
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
        assert (response.status_code, detail) == (404, message), f"{method} on the market data of the unknown asset {ghost} answers {response.status_code} {response.text}: expected today's 404 with the string detail {message!r}"


@pytest.mark.asyncio
async def test_guard_another_assets_split_neither_stops_the_wipe_nor_is_touched(owned):
    """Guard: green today and after. The other asset has a SPLIT of 2 (day 120) with a costless ADJUSTMENT +10 on broker A;
    the wiped asset a SPLIT of 2 nothing links to and a price. The wipe goes through as today: the guard reads the wiped
    asset's SPLITs alone. The wiped asset's events and price are gone; the other asset's SPLIT and its adjustment, link
    included, stay as they were, every column."""
    other_split = await _event(owned.other_asset_id, 120, AssetEventType.SPLIT, "2", notes="2-for-1")
    on_other = await _adjustment(owned.other_asset_id, owned.broker_a_id, other_split, 121)
    split_id = await _event(owned.asset_id, 120, AssetEventType.SPLIT, "2")
    await _price(owned.asset_id, 119, "100")
    await _barrier_costless([other_split, split_id], {other_split: [on_other]}, "the other asset's SPLIT with a costless adjustment, beside the wiped asset's SPLIT nothing links to")
    before = await _committed(owned)
    story = f"the wipe of the asset whose SPLIT {split_id} nothing links to, while the other asset's SPLIT {other_split} has the costless adjustment {on_other}"

    counters = await _wipe_counters(owned, story)

    expected = _summary(prices=1, manual=1, linked=0, priced=119, dry_run=False)
    assert counters == expected, f"{story} answers {counters}: expected today's counters {expected}"
    await _assert_wiped(owned, before, story, disconnected=set())
