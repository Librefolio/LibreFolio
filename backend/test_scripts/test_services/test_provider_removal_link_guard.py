"""X-R62 -> X-R69 (workstream X): removing an asset's provider while transactions are linked to the events it generated.

History, short. X-R62 made ``DELETE /api/v1/assets/provider?asset_ids=…`` (``remove_providers_bulk``, ``api/v1/assets/providers.py``
-> ``ProviderManagementOperations.bulk_remove_providers``, ``services/assets/provider_management.py``) refuse with
``PROVIDER_REMOVAL_LINKED_TRANSACTIONS`` (409) while a transaction was linked to an event the removed assignment generated
(``asset_events.provider_assignment_id`` is ``ON DELETE CASCADE``, ``transactions.asset_event_id`` ``ON DELETE RESTRICT``,
and every connection turns SQLite's foreign keys on), instead of the 500 with the SQL text it answered before. That
refusal is REPLACED by the developer's decision of 22-23/10 (lot X5-1): «togli» (remove the provider) and «cambia»
(change the provider, or a parametric provider's params) follow ONE rule. A dry run (``POST /assets/provider/impact``,
``test_provider_change_impact.py``) tells what would be lost; once confirmed, both UNLINK the transactions linked to the
events that disappear. ``PROVIDER_REMOVAL_LINKED_TRANSACTIONS`` no longer exists.

The contract this file pins:

* ``bulk_remove_providers(asset_ids, session, *, current_user_id=None)``. For every asset of the request with an
  assignment: ``transactions.asset_event_id`` is set to NULL for every transaction linked to an event of the assignment
  (``asset_events.provider_assignment_id == assignment.id``), whoever owns the broker; then the assignment is deleted, its
  events with it (the cascade), and the commit. The answer is the same ``FABulkRemoveResponse``. Manual events
  (``provider_assignment_id IS NULL``) are untouched and their linked transactions stay linked; prices are NOT deleted.
* The one hard refusal left is X-R49's: a SPLIT among the events that disappear with linked incoming ADJUSTMENTs WITHOUT a
  purchase cost (``split_guard.splits_with_costless_adjustments``): ``AssetSourceError`` with ``error_code`` exactly
  ``PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST`` (the code of the change, X-R49), ``details`` exactly ``{"asset_id",
  "item_index" (the asset's first position in the request), "splits"}``, ``splits`` as ``split_guard`` names them for the
  caller (visible ids, ``hidden_transactions_count``), the message starting with the code and giving the totals only,
  never an id. All or nothing: checked before the first write, nothing written for any asset of the request (those before
  the refused one included), not even pending in the refused call's session. A SPLIT whose adjustments HAVE a cost does
  not refuse: it is disconnected like any other event.
* The route answers that refusal and ``PROVIDER_REMOVAL_CONFLICT`` (the IntegrityError of a link made between the
  disconnection and the delete: rolled back, ``details`` ``{}``, the message exactly ``CONFLICT_MESSAGE``) 409,
  ``detail`` exactly ``{"error_code", "message", "params"}``, never the SQL text.

Guards, green before and after: a provider without a linked transaction (removed, its events with it), a manual event with
a linked transaction (it stays, still linked), an asset without an assignment, an empty request, and the two helpers of
``event_links.py`` the dry run reuses.

A refusal is looked for as the router meets it: nobody commits after a refused call, the session just closes. Right after
the refusal its own session is read: nothing pending there (``new``, ``dirty``, ``deleted``) and, through raw SQL, the
rows as they were; once that session is closed, a fresh connection reads what is committed; every column, ``updated_at``
included. A call that raises where the contract expects an answer fails its test naming the exception, never as an error.
The route tests call the route in process: the provider router mounted at ``/api/v1/assets`` as the app mounts it, on an
app of the call's own, ``get_current_user`` overridden there to the unit's user, the session the real dependency opens; the
answer read as the client reads it, JSON. The race of the conflict tests is a real one: an SQLAlchemy ``before_cursor_execute``
listener on the lane's engine re-links the disconnected transaction to its event on the same connection, just before the
first DELETE of the removal, so the RESTRICT fires whatever order the implementation deletes in. Each red says what happens
before the lot ("Red today"); a guard passes before and after.

Isolation: WRITE-SCOPED, the services default. Every row is this unit's own, under a unique marker: three EUR assets,
inactive so that no scheduler of the lane refreshes them (the market asset, the plan's, the bare one), two users and two
brokers, user A holding an access to broker A alone, user B to broker B alone. Each test finds the market asset assigned
yfinance under a ticker of the unit's own, the plan's asset scheduled_investment with a plan of 1984, the bare asset
without an assignment, and no price, event or transaction. The two assignments are written for each test: a removal
deletes them, and their table, without AUTOINCREMENT, may give a deleted id to the next row, so no id is kept across
tests. Only the rows of those assets and brokers are written, read and wiped, by asset and broker id; nothing is fetched,
a removal asks no provider for anything; nothing here counts or reads a row it did not write. The readers, the route's
helpers and two barriers are X-R49's, imported from ``test_provider_wipe_split_guard``; the rows, their fixtures and the
cases are this unit's.
"""

import asyncio
import json
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
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
from sqlalchemy import bindparam, delete, event, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.assets import providers as providers_api
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
from backend.app.services.assets.event_links import events_with_linked_transactions, visible_transaction_ids
from backend.app.services.assets.manager import AssetSourceManager
from backend.test_scripts.test_services.test_provider_wipe_split_guard import (
    _WHOLE_NUMBER,
    _add,
    _barrier_costless,
    _barrier_who_sees_what,
    _body,
    _caller,
    _changes,
    _committed,
    _detail,
    _read,
    _State,
    _undated,
    _unlinked,
)
from backend.test_scripts.test_services.test_provider_wipe_split_guard import _assert_details as _assert_split_details
from backend.test_scripts.test_services.test_provider_wipe_split_guard import _details as _split_details
from backend.test_scripts.test_utils import unique_id

#: The refusal's code: X-R49's, the change's, now the removal's too (X-R69). The code X-R62 gave a removal,
#: PROVIDER_REMOVAL_LINKED_TRANSACTIONS, no longer exists.
CODE = "PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST"
#: The code of a link made between the disconnection and the delete, and its message, exactly.
CONFLICT = "PROVIDER_REMOVAL_CONFLICT"
CONFLICT_MESSAGE = "PROVIDER_REMOVAL_CONFLICT: the provider could not be removed, because a row still refers to the events it generated; nothing was removed"
#: The providers: a market one, whose refresh stores dividends and splits, and the parametric plan, whose refresh stores
#: its coupons.
MARKET = "yfinance"
PLAN = "scheduled_investment"
#: The route under test, as the app mounts it.
REMOVE_PATH = "/api/v1/assets/provider"
#: Today's answer for each asset of a removal that goes through, whether it held an assignment or not.
REMOVED = {"success": True, "deleted_count": 1, "message": "Provider removed"}
#: The unit's assets by role.
ASSET_TYPES = {"market": AssetType.STOCK, "plan": AssetType.BOND, "bare": AssetType.STOCK}
#: What an answer carrying the SQL text holds, read case-insensitively: none belongs to an answer of the removal.
SQL_MARKERS = ("foreign key", "constraint", "delete from", "integrityerror", "sqlite", "[sql:")
#: What a removal meets before X-R69, for the message of the test it fails.
TODAY = "Before X-R69 a removal is refused with PROVIDER_REMOVAL_LINKED_TRANSACTIONS (409) while a transaction links to an event its assignment generated, instead of unlinking it"

# A window far from the mock dataset and from the other units that write events (1986, 1988, 1990, 1991-1992,
# 1994-1995). Rows are scoped by asset and broker anyway: the dates only keep the failure output readable.
BASE_DATE = date(1984, 4, 2)
#: Offsets from BASE_DATE.
UNLINKED_DAY = 5  # a generated event no transaction links to
SPLIT_DAY = 20  # a generated SPLIT
DIVIDEND_DAY = 20  # a generated DIVIDEND, on the SPLIT's day: between the two, their ids give the order
COUPON_DAY = 28  # a plan's coupon
MANUAL_DAY = 35  # a manual event
LATE_DAY = 50  # a generated DIVIDEND written before the others and listed after them


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


def _plan() -> dict:
    """The plan's params (``FAScheduledInvestmentSchedule``): 1 000 EUR over 1984 at 4 %, monthly coupons, no planned
    event. A new dict at each call."""
    period = {"start_date": "1984-01-01", "end_date": "1984-12-31", "annual_rate": "0.04", "maturation_frequency": "MONTHLY", "generate_interest": True}
    return {"initial_value": {"code": "EUR", "amount": "1000.00"}, "schedule": [period], "asset_events": []}


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Unit:
    """What this unit created once: three EUR assets, inactive (the market asset; the plan's; the bare one, never
    assigned), two users and two brokers, user A holding an access to broker A alone, user B to broker B alone; and the
    ticker the market asset is assigned under."""

    market_asset_id: int
    plan_asset_id: int
    bare_asset_id: int
    ticker: str
    user_a_id: int
    user_b_id: int
    broker_a_id: int
    broker_b_id: int

    @property
    def asset_ids(self) -> list[int]:
        return [self.market_asset_id, self.plan_asset_id, self.bare_asset_id]

    @property
    def user_ids(self) -> list[int]:
        return [self.user_a_id, self.user_b_id]

    @property
    def broker_ids(self) -> list[int]:
        return [self.broker_a_id, self.broker_b_id]


@dataclass(frozen=True)
class _Owned(_Unit):
    """The unit as a test finds it: the market asset's assignment (yfinance under the unit's ticker) and the plan's
    (scheduled_investment with the plan), written for the test; the bare asset without one."""

    market_assignment_id: int
    plan_assignment_id: int

    @property
    def role_ids(self) -> dict[str, int]:
        """The assets by role, as a request names them."""
        return {"market": self.market_asset_id, "plan": self.plan_asset_id, "bare": self.bare_asset_id}


async def _clear(unit: _Unit) -> None:
    """No transaction on the unit's brokers (they RESTRICT the events they link to), no event, price or assignment of its
    assets. Bulk statements by id: no row is loaded."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(Transaction).where(Transaction.broker_id.in_(unit.broker_ids)))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(unit.asset_ids)))
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(unit.asset_ids)))
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(unit.asset_ids)))
        await session.commit()


async def _assign(unit: _Unit) -> _Owned:
    """The market asset assigned yfinance under the unit's ticker, the plan's asset scheduled_investment with the plan,
    as a save leaves them, never fetched; the bare asset left without. Written for each test: a removal deletes them."""
    market = AssetProviderAssignment(asset_id=unit.market_asset_id, provider_code=MARKET, identifier=unit.ticker, identifier_type=ProviderInputType.TICKER, provider_params=None, last_fetch_at=None)
    plan = AssetProviderAssignment(asset_id=unit.plan_asset_id, provider_code=PLAN, identifier=None, identifier_type=ProviderInputType.AUTO_GENERATED, provider_params=json.dumps(_plan()), last_fetch_at=None)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add_all([market, plan])
        await session.commit()
    return _Owned(**asdict(unit), market_assignment_id=market.id, plan_assignment_id=plan.id)


@pytest.fixture(scope="module")
def unit() -> _Unit:
    """The assets, the users, the brokers and the accesses, under names no concurrent worker can repeat, dropped in
    FK-safe order in teardown with every assignment, price, event and transaction written against them."""
    marker = f"{unique_id('XR62')}_{uuid.uuid4().hex[:8]}"
    ticker = f"XR62.{uuid.uuid4().hex[:10].upper()}"

    async def _create() -> _Unit:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            assets = {role: Asset(display_name=f"X-R62 {role} {marker}", currency="EUR", asset_type=asset_type, active=False) for role, asset_type in ASSET_TYPES.items()}
            user_a = User(username=f"xr62a_{marker}".lower(), email=f"xr62a_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            user_b = User(username=f"xr62b_{marker}".lower(), email=f"xr62b_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            broker_a = Broker(name=f"X-R62 A {marker}")
            broker_b = Broker(name=f"X-R62 B {marker}")
            session.add_all([*assets.values(), user_a, user_b, broker_a, broker_b])
            await session.commit()
            access_a = BrokerUserAccess(user_id=user_a.id, broker_id=broker_a.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            access_b = BrokerUserAccess(user_id=user_b.id, broker_id=broker_b.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            session.add_all([access_a, access_b])
            await session.commit()
            return _Unit(
                market_asset_id=assets["market"].id,
                plan_asset_id=assets["plan"].id,
                bare_asset_id=assets["bare"].id,
                ticker=ticker,
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                broker_a_id=broker_a.id,
                broker_b_id=broker_b.id,
            )

    async def _drop(created: _Unit) -> None:
        await _clear(created)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(BrokerUserAccess).where(or_(BrokerUserAccess.broker_id.in_(created.broker_ids), BrokerUserAccess.user_id.in_(created.user_ids))))
            await session.execute(delete(Broker).where(Broker.id.in_(created.broker_ids)))
            await session.execute(delete(Asset).where(Asset.id.in_(created.asset_ids)))
            await session.execute(delete(User).where(User.id.in_(created.user_ids)))
            await session.commit()

    created = asyncio.run(_create())
    yield created
    asyncio.run(_drop(created))


@pytest_asyncio.fixture
async def owned(unit: _Unit):
    """The unit with its two assignments written for the test, and no price, event or transaction of its assets or on
    its brokers, before and after the test."""
    await _clear(unit)
    yield await _assign(unit)
    await _clear(unit)


# --------------------------------------------------------------------------- #
# Seeding: rows written directly, as earlier refreshes, saves and imports left them
# --------------------------------------------------------------------------- #


async def _event(asset_id: int, offset: int, kind: AssetEventType, amount: str, *, assignment_id: int | None = None, notes: str | None = None) -> int:
    """An event of ``asset_id`` on day ``offset``, in EUR, as a refresh under ``assignment_id`` stores it, or, without
    one, as a manual save left it: its id."""
    return await _add(AssetEvent(asset_id=asset_id, date=_day(offset), type=kind, value=Decimal(amount), currency="EUR", notes=notes, provider_assignment_id=assignment_id))


async def _income(asset_id: int, broker_id: int, kind: TransactionType, offset: int, amount: str, *, event_id: int | None = None) -> int:
    """A DIVIDEND or an INTEREST of ``amount`` EUR from ``asset_id`` on ``broker_id``, booked on day ``offset``, linked to
    ``event_id`` or to no event: its id."""
    return await _add(Transaction(broker_id=broker_id, asset_id=asset_id, type=kind, date=_day(offset), quantity=Decimal("0"), amount=Decimal(amount), currency="EUR", asset_event_id=event_id))


async def _adjustment(asset_id: int, broker_id: int, event_id: int, offset: int, *, cost: str | None = None) -> int:
    """An ADJUSTMENT +10 of ``asset_id`` on ``broker_id``, booked on day ``offset`` and linked to ``event_id``: without a
    cost, as the Auto mode stores one linked to a SPLIT, or with ``cost`` EUR a unit. Its id."""
    return await _add(
        Transaction(
            broker_id=broker_id,
            asset_id=asset_id,
            type=TransactionType.ADJUSTMENT,
            date=_day(offset),
            quantity=Decimal("10"),
            amount=Decimal("0"),
            currency=None,
            cost_basis_override=None if cost is None else Decimal(cost),
            cost_basis_currency=None if cost is None else "EUR",
            asset_event_id=event_id,
        )
    )


async def _buy(asset_id: int, broker_id: int, offset: int) -> int:
    """A BUY of 10 units of ``asset_id`` for 1 000 EUR on ``broker_id``, booked on day ``offset``, linked to no event: its
    id."""
    return await _add(Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=_day(offset), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"))


# --------------------------------------------------------------------------- #
# Barriers: the case is the one the test names
# --------------------------------------------------------------------------- #

_RAW_LINKS = text("SELECT e.id AS event_id, e.provider_assignment_id AS assignment_id, t.id AS transaction_id FROM asset_events e LEFT JOIN transactions t ON t.asset_event_id = e.id WHERE e.asset_id IN :asset_ids ORDER BY e.id, t.id").bindparams(bindparam("asset_ids", expanding=True))


async def _barrier_links(owned: _Owned, expected: dict[int, tuple[int | None, list[int]]], story: str) -> None:
    """Barrier: the events of the unit's assets are exactly ``expected``, each event's id -> (the assignment that
    generated it, None for a manual one; the transactions linked to it, sorted): so the removal meets the links the test
    names, and no other."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(_RAW_LINKS, {"asset_ids": owned.asset_ids})).all()
    links: dict[int, tuple[int | None, list[int]]] = {}
    for event_id, assignment_id, transaction_id in rows:
        linked = links.setdefault(event_id, (assignment_id, []))[1]
        if transaction_id is not None:
            linked.append(transaction_id)
    assert links == expected, f"barrier: {story}: the unit's events read {links} as event -> (assignment, linked transactions): expected {expected}"


async def _barrier_foreign_keys() -> None:
    """Barrier: the lane's connections enforce foreign keys (``db/session.py`` turns them on at connect): a removed
    assignment's events go with it (CASCADE) and an event a transaction links to cannot go (RESTRICT), as the test
    expects."""
    async with get_async_engine().connect() as connection:
        enforced = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
    assert enforced == 1, f"barrier: PRAGMA foreign_keys reads {enforced!r} on a fresh connection: expected 1, the CASCADE and the RESTRICT this test relies on enforced"


def _barrier_unassigned(before: _State, asset_id: int, story: str) -> None:
    """Barrier: the asset ``asset_id`` holds no assignment, so the removal has nothing of its own to check or delete."""
    held = sorted(row_id for row_id, row in before.assignments.items() if row["asset_id"] == asset_id)
    assert not held, f"barrier: {story}: the asset {asset_id} holds the assignment(s) {held}: expected none"


# --------------------------------------------------------------------------- #
# The removal, called as the route calls it
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Refused:
    """A refused removal, and what its own session holds right after it: the ORM changes pending there (``new``,
    ``dirty``, ``deleted``), whether it is still in a transaction, and every row of the unit's as raw SQL reads it there,
    committed or not."""

    error: AssetSourceError
    pending: dict[str, list]
    in_transaction: bool
    seen: _State


async def _refused_remove(owned: _Owned, asset_ids: list[int], before: _State, story: str, *, code: str = CODE, **caller: int) -> _Refused:
    """The removal of ``asset_ids``, for a request the contract refuses with ``code``, ``caller`` the ``current_user_id``
    it is given if any: the refusal, and what the refused call's own session holds right after it. As in the route,
    nobody commits after it: the session closes. Any other exception fails the test, naming it; so does a removal that
    goes through, saying what it deleted against ``before``."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            answer = await AssetSourceManager.bulk_remove_providers(asset_ids, session, **caller)
        except AssetSourceError as refusal:
            pending = {"new": list(session.new), "dirty": list(session.dirty), "deleted": list(session.deleted)}
            in_transaction = session.in_transaction()
            return _Refused(error=refusal, pending=pending, in_transaction=in_transaction, seen=await _read(session, owned))
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            pytest.fail(f"{story} raised {exc!r} instead of the refusal {code}. {TODAY}")
    pytest.fail(f"{story} went through, answering {answer.model_dump(mode='json')}, instead of being refused with {code}: {_changes(before, await _committed(owned))}")


async def _removed(owned: _Owned, asset_ids: list[int], story: str, *, via: str) -> object:
    """``asset_ids`` removed through ``via``, for a removal that must go through: the service without a caller, as the
    route calls it today, or ``DELETE /assets/provider`` in process as user A; the answer as the client reads it (JSON).
    A refusal, another status or any other exception fails the test, naming it."""
    if via == "route":
        response = await _route(owned.user_a_id, asset_ids)
        assert response.status_code == 200, f"{story} answers {response.status_code} {response.text}: expected 200, as today"
        return _body(response)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            answer = await AssetSourceManager.bulk_remove_providers(asset_ids, session)
        except AssetSourceError as refusal:
            pytest.fail(f"{story} was refused: {refusal.error_code} {refusal.message} {refusal.details} (X-R69 refuses only a SPLIT whose linked incoming adjustments have no purchase cost; {TODAY})")
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story} raised {exc!r}: the route answers 500")
    return answer.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# The route, in process
# --------------------------------------------------------------------------- #


async def _route(user_id: int, asset_ids: list[int]) -> httpx.Response:
    """``DELETE /api/v1/assets/provider?asset_ids=…`` in process, as the user ``user_id``: the provider router mounted at
    ``/api/v1/assets`` as the app mounts it (``asset_router`` includes it under ``/assets``, the app the v1 router under
    ``/api/v1``), on an app of the call's own, so ``get_current_user`` is overridden there, never on the shared app, with
    the session the real dependency opens on the lane's database. Nothing is mocked behind the route but what the test
    patches."""
    caller = await _caller(user_id)
    app = FastAPI()
    app.include_router(providers_api.provider_router, prefix="/api/v1/assets")
    app.dependency_overrides[get_current_user] = lambda: caller
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.delete(REMOVE_PATH, params={"asset_ids": asset_ids})


def _sql_in(response: httpx.Response) -> list[str]:
    """What of the SQL text the answer carries, anywhere in its body."""
    body = response.text.lower()
    return [marker for marker in SQL_MARKERS if marker in body]


def _assert_answered_409(response: httpx.Response, story: str, *, code: str) -> tuple[str, object]:
    """The answer is 409, ``detail`` exactly ``{"error_code": code, "message", "params"}``, and no SQL anywhere in its body:
    its message and its params, for the test to read."""
    sql = _sql_in(response)
    shown = f", carrying the SQL text ({', '.join(sql)})" if sql else ""
    assert response.status_code == 409 and not sql, f"{story} answers {response.status_code}{shown}: {response.text}; expected 409 {code}, never the SQL text"
    detail = _detail(response)
    assert sorted(detail) == ["error_code", "message", "params"], f"{story}: the 409's detail holds the keys {sorted(detail)}: expected exactly error_code, message and params: {detail}"
    assert detail["error_code"] == code, f"{story}: the 409 names {detail['error_code']} ({detail['message']}): expected {code}"
    return detail["message"], detail["params"]


# --------------------------------------------------------------------------- #
# What the contract expects
# --------------------------------------------------------------------------- #


def _entry(event_id: int, offset: int, kind: AssetEventType, seen: list[int], hidden: int) -> dict:
    """One event as ``events_with_linked_transactions`` gives it: its id, its date (ISO), its type, the linked transactions
    the caller sees (sorted), how many it does not."""
    return {"event_id": event_id, "date": _day(offset).isoformat(), "type": kind.value, "transaction_ids": sorted(seen), "hidden_transactions_count": hidden}


def _split_entry(event_id: int, offset: int, seen: list[int], hidden: int) -> dict:
    """One SPLIT of the refusal, as ``split_guard`` gives it: the event, its date (ISO), the costless adjustments the caller
    sees (sorted), how many it does not."""
    return {"event_id": event_id, "date": _day(offset).isoformat(), "transaction_ids": sorted(seen), "hidden_transactions_count": hidden}


def _assert_events(events: object, expected: list[dict], story: str, where: str) -> None:
    """``events`` is exactly ``expected``: the same events in the same order, each entry exactly the expected one."""
    entries = events if isinstance(events, list) else []
    order = [entry.get("event_id") if isinstance(entry, dict) else entry for entry in entries]
    wanted = [entry["event_id"] for entry in expected]
    assert isinstance(events, list) and order == wanted, f"{story}: {where} list the events {order} ({events!r}): expected {wanted}, each event a transaction links to once, ordered by (date, event id); none without a link"
    for found, entry in zip(entries, expected, strict=True):
        assert found == entry, f"{story}: {where} give the event {entry['event_id']} as {found}: expected exactly {entry}: its date (ISO), its type, the linked transactions the caller can see on their brokers (sorted), the others counted, no other key (which could carry a hidden id)"


def _assert_refused(error: AssetSourceError, expected: dict, story: str, *, splits: int, adjustments: int, ids: list[int]) -> None:
    """The refusal is ``PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST``, its details exactly ``expected`` (the refused asset,
    its first position, its SPLITs as the caller may see them), its message starting with the code and naming no id of the
    case (``ids``): whoever reads it, it carries nothing the details filter. The totals (``splits`` SPLITs, ``adjustments``
    adjustments) and the asset and position are not looked for as ids: they read as plain numbers."""
    assert error.error_code == CODE, f"{story} was refused with {error.error_code} ({error.message}), not {CODE}: {error.details}"
    _assert_split_details(error.details, expected, story, "the refusal's details")
    assert isinstance(error.message, str) and error.message.startswith(f"{CODE}:"), f"{story}: the refusal's message reads {error.message!r}: expected it to start with {CODE}:"
    numbers = {int(number) for number in _WHOLE_NUMBER.findall(error.message)}
    named = sorted((set(ids) & numbers) - {splits, adjustments, expected["asset_id"], expected["item_index"]})
    assert not named, f"{story}: the message {error.message!r} names the id(s) {named}: expected no id, a hidden adjustment's id would reach a user who cannot see its broker"


async def _assert_nothing_written(owned: _Owned, before: _State, refused: _Refused, story: str) -> None:
    """All or nothing: nothing pending in the refused call's own session, which reads ``before`` (no write of the
    request there, the assets before the refused one included); and nothing committed: once that session is closed, a
    fresh connection reads ``before`` too. Every column of every assignment, event, price and transaction of the unit's,
    ``updated_at`` included."""
    pending = {name: rows for name, rows in refused.pending.items() if rows}
    assert not pending, f"{story} was refused with changes pending in its session: {pending} (X-R69: nothing of the request written, not even pending: a caller committing after the refusal would store it)"
    assert refused.seen == before, f"{story} was refused after writing: its own session reads {_changes(before, refused.seen)} (X-R69: all or nothing, nothing of the request written, not even pending in its session)"
    after = await _committed(owned)
    assert after == before, f"{story} was refused, yet the database changed: {_changes(before, after)}"


def _assert_answered_as_today(answer: object, asset_ids: list[int], story: str) -> None:
    """The answer of a removal that goes through, as today: each asset of the request in its order, a success,
    ``deleted_count`` 1, "Provider removed"; ``success_count`` their number; no error."""
    expected = {"results": [{"asset_id": asset_id, **REMOVED} for asset_id in asset_ids], "success_count": len(asset_ids), "errors": []}
    assert answer == expected, f"{story} answered {answer}: expected {expected}, as today"


def _assert_removed(before: _State, after: _State, story: str, *, asset_ids: set[int]) -> None:
    """What today's removal does, and still does when it goes through: the assignments of ``asset_ids`` gone, with every
    event they generated (the cascade); every other assignment and event (a manual one of those assets included), every
    price and every transaction as it was, every column, the links included."""
    gone = {row_id for row_id, row in before.assignments.items() if row["asset_id"] in asset_ids}
    assert gone, f"barrier: {story}: none of the assets {sorted(asset_ids)} holds an assignment before the removal: nothing to remove"
    assignments = {row_id: row for row_id, row in before.assignments.items() if row_id not in gone}
    events = {row_id: row for row_id, row in before.events.items() if row["provider_assignment_id"] not in gone}
    gone_events = sorted(set(before.events) - set(events))
    assert (after.assignments, after.events) == (assignments, events), f"{story}: the assignments and events moved as {_changes(before, after)}: expected the assignments {sorted(gone)} gone with the events {gone_events} they generated, every other one as it was, as today"
    assert (after.prices, after.transactions) == (before.prices, before.transactions), f"{story}: the prices or transactions moved as {_changes(before, after)}: expected every one as it was, its link included, as today"


def _assert_removed_and_disconnected(before: _State, after: _State, story: str, *, asset_ids: set[int], disconnected: set[int]) -> None:
    """What the removal does when it goes through (X-R69): the assignments of ``asset_ids`` gone, with every event they
    generated (the cascade); every other assignment and event (a manual one of those assets included) and every price as
    it was; no transaction deleted; the ``disconnected`` ones (exactly those linked to a generated event that went) with
    ``asset_event_id`` NULL and every other column as it was (``updated_at`` aside); every other transaction as it was, every
    column, its link included."""
    gone = {row_id for row_id, row in before.assignments.items() if row["asset_id"] in asset_ids}
    assert gone, f"barrier: {story}: none of the assets {sorted(asset_ids)} holds an assignment before the removal: nothing to remove"
    assignments = {row_id: row for row_id, row in before.assignments.items() if row_id not in gone}
    events = {row_id: row for row_id, row in before.events.items() if row["provider_assignment_id"] not in gone}
    gone_events = set(before.events) - set(events)
    linked = {row_id for row_id, row in before.transactions.items() if row["asset_event_id"] in gone_events}
    assert linked == disconnected, f"barrier: {story}: the transactions linked to the events {sorted(gone_events)} that go are {sorted(linked)}, the test expects {sorted(disconnected)}"
    assert (after.assignments, after.events) == (assignments, events), f"{story}: the assignments and events moved as {_changes(before, after)}: expected the assignments {sorted(gone)} gone with the events {sorted(gone_events)} they generated, every other one as it was"
    assert after.prices == before.prices, f"{story}: the prices moved as {_changes(before, after)}: expected every one as it was, a removal deletes none"
    assert set(after.transactions) == set(before.transactions), f"{story}: the transactions moved as {_changes(before, after)}: expected every one kept, a removal deletes none"
    for row_id, row in before.transactions.items():
        found = after.transactions[row_id]
        if row_id in disconnected:
            assert _undated(found) == _unlinked(row), f"{story}: the transaction {row_id} reads {found}: expected the same row with asset_event_id NULL (was {row['asset_event_id']})"
        else:
            assert found == row, f"{story}: the transaction {row_id} moved from {row} to {found}: expected it untouched, its link included"


# --------------------------------------------------------------------------- #
# The cases
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Linked:
    """A generated event, and the transaction linked to it."""

    event_id: int
    tx_id: int


async def _dividend(owned: _Owned) -> _Linked:
    """On the market asset: a DIVIDEND of 0.50 EUR on day ``DIVIDEND_DAY``, an event of its yfinance assignment as the
    provider's refresh stores it, linked to the DIVIDEND of 5 EUR on broker A booked that day."""
    event_id = await _event(owned.market_asset_id, DIVIDEND_DAY, AssetEventType.DIVIDEND, "0.50", assignment_id=owned.market_assignment_id)
    tx_id = await _income(owned.market_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, DIVIDEND_DAY, "5.00", event_id=event_id)
    return _Linked(event_id=event_id, tx_id=tx_id)


async def _coupon(owned: _Owned) -> _Linked:
    """On the plan's asset: a coupon of 3.33 EUR on day ``COUPON_DAY``, an INTEREST event of the plan's assignment as its
    refresh stores it, linked to the INTEREST of 3.33 EUR on broker A booked that day: J's case."""
    event_id = await _event(owned.plan_asset_id, COUPON_DAY, AssetEventType.INTEREST, "3.33", assignment_id=owned.plan_assignment_id)
    tx_id = await _income(owned.plan_asset_id, owned.broker_a_id, TransactionType.INTEREST, COUPON_DAY, "3.33", event_id=event_id)
    return _Linked(event_id=event_id, tx_id=tx_id)


@dataclass(frozen=True)
class _Spread:
    """Events of the market asset's yfinance assignment spread over dates and brokers: a DIVIDEND of day ``LATE_DAY``,
    written first, linked on broker A; a SPLIT of day ``SPLIT_DAY`` linked to an adjustment on broker B, then to two on
    broker A (one costless, one with a cost); a DIVIDEND of day ``DIVIDEND_DAY`` (the SPLIT's), written after it, linked
    on broker B; a PRICE_ADJUSTMENT no transaction links to."""

    late: int
    late_on_a: int
    split: int
    split_on_b: int
    split_on_a: tuple[int, int]
    early: int
    early_on_b: int
    unlinked: int

    def links(self, assignment_id: int) -> dict[int, tuple[int | None, list[int]]]:
        """The events as ``_barrier_links`` reads them, all of ``assignment_id``, each with its linked transactions."""
        return {self.late: (assignment_id, [self.late_on_a]), self.split: (assignment_id, sorted([self.split_on_b, *self.split_on_a])), self.early: (assignment_id, [self.early_on_b]), self.unlinked: (assignment_id, [])}


async def _spread(owned: _Owned) -> _Spread:
    """``_Spread`` written on the market asset: the late DIVIDEND first, so the event listed last has the lowest id; the
    SPLIT's adjustment on broker B before broker A's two, so the transaction user A cannot see has the lowest id."""
    asset_id, assignment_id = owned.market_asset_id, owned.market_assignment_id
    late = await _event(asset_id, LATE_DAY, AssetEventType.DIVIDEND, "0.50", assignment_id=assignment_id)
    late_on_a = await _income(asset_id, owned.broker_a_id, TransactionType.DIVIDEND, LATE_DAY, "5.00", event_id=late)
    split = await _event(asset_id, SPLIT_DAY, AssetEventType.SPLIT, "2", assignment_id=assignment_id, notes="2-for-1")
    split_on_b = await _adjustment(asset_id, owned.broker_b_id, split, SPLIT_DAY + 1)
    split_on_a = (await _adjustment(asset_id, owned.broker_a_id, split, SPLIT_DAY + 1), await _adjustment(asset_id, owned.broker_a_id, split, SPLIT_DAY + 1, cost="12.5"))
    early = await _event(asset_id, DIVIDEND_DAY, AssetEventType.DIVIDEND, "0.40", assignment_id=assignment_id)
    early_on_b = await _income(asset_id, owned.broker_b_id, TransactionType.DIVIDEND, DIVIDEND_DAY, "4.00", event_id=early)
    unlinked = await _event(asset_id, UNLINKED_DAY, AssetEventType.PRICE_ADJUSTMENT, "-0.10", assignment_id=assignment_id)
    return _Spread(late=late, late_on_a=late_on_a, split=split, split_on_b=split_on_b, split_on_a=split_on_a, early=early, early_on_b=early_on_b, unlinked=unlinked)


def _views(spread: _Spread) -> dict[str, list[dict]]:
    """The linked events of ``spread`` as each caller sees them, by (date, id): the SPLIT and the early DIVIDEND (day 20,
    by id), then the late DIVIDEND (day 50, the lowest id); the PRICE_ADJUSTMENT, linked to nothing, never."""
    split, early, late = (spread.split, SPLIT_DAY, AssetEventType.SPLIT), (spread.early, DIVIDEND_DAY, AssetEventType.DIVIDEND), (spread.late, LATE_DAY, AssetEventType.DIVIDEND)
    return {
        "user A": [_entry(*split, list(spread.split_on_a), 1), _entry(*early, [], 1), _entry(*late, [spread.late_on_a], 0)],
        "user B": [_entry(*split, [spread.split_on_b], 2), _entry(*early, [spread.early_on_b], 0), _entry(*late, [], 1)],
        "no caller": [_entry(*split, [], 3), _entry(*early, [], 1), _entry(*late, [], 1)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reds: removing a provider unlinks the transactions of the events that disappear; only a costless SPLIT refuses
# ─────────────────────────────────────────────────────────────────────────────


async def _price(asset_id: int, offset: int, close: str) -> int:
    """A closing price of ``asset_id`` on day ``offset``, in EUR: its id."""
    return await _add(PriceHistory(asset_id=asset_id, date=_day(offset), close=Decimal(close), currency="EUR", source_plugin_key="test"))


@dataclass(frozen=True)
class _SplitCase:
    """A provider's SPLIT of 2 (day ``SPLIT_DAY``) of the asset of ``role``, with the transactions linked to it."""

    role: str
    asset_id: int
    split_id: int
    adjustments: list[int]


async def _split_case(owned: _Owned, role: str, *, on_b: bool = False, cost: str | None = None) -> _SplitCase:
    """On the asset of ``role`` (the market asset or the plan's): its provider's SPLIT of 2, an event of its assignment, with
    an ADJUSTMENT +10 on broker B first when ``on_b``, then one on broker A, booked the next day, costless or with ``cost``
    EUR a unit. Barrier: P-10's layer lists the costless adjustments, none when they have a cost."""
    asset_id = owned.role_ids[role]
    assignment_id = owned.market_assignment_id if role == "market" else owned.plan_assignment_id
    split_id = await _event(asset_id, SPLIT_DAY, AssetEventType.SPLIT, "2", assignment_id=assignment_id, notes="2-for-1")
    adjustments = []
    if on_b:
        adjustments.append(await _adjustment(asset_id, owned.broker_b_id, split_id, SPLIT_DAY + 1, cost=cost))
    adjustments.append(await _adjustment(asset_id, owned.broker_a_id, split_id, SPLIT_DAY + 1, cost=cost))
    kind = "without a cost" if cost is None else f"costing {cost} EUR a unit"
    await _barrier_costless([split_id], {split_id: sorted(adjustments)} if cost is None else {}, f"the {role} provider's SPLIT with incoming adjustments {kind}")
    await _barrier_who_sees_what(owned)
    return _SplitCase(role=role, asset_id=asset_id, split_id=split_id, adjustments=sorted(adjustments))


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_removing_a_provider_unlinks_the_transactions_linked_to_its_dividend(owned, via):
    """Red today (X-R69): the removal is refused with PROVIDER_REMOVAL_LINKED_TRANSACTIONS (409 through the route) while a
    transaction links to an event of the assignment.

    Contract: the market provider's DIVIDEND (day 20) is linked to a DIVIDEND on broker A; beside it a PRICE_ADJUSTMENT
    linked to nothing, a price of the market asset, and a manual DIVIDEND (day 35) linked to a DIVIDEND on broker A. Removing
    the market asset's provider, through the service without a caller or the route as user A: answered as before (a
    success, ``deleted_count`` 1, "Provider removed"); the assignment gone with its two events (the cascade); the DIVIDEND
    transaction still there, its ``asset_event_id`` NULL, every other column as it was; the price kept; the manual event
    and its transaction as they were, still linked.
    """
    case = await _dividend(owned)
    unlinked = await _event(owned.market_asset_id, UNLINKED_DAY, AssetEventType.PRICE_ADJUSTMENT, "-0.10", assignment_id=owned.market_assignment_id)
    manual = await _event(owned.market_asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
    manual_on_a = await _income(owned.market_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, MANUAL_DAY, "4.50", event_id=manual)
    await _price(owned.market_asset_id, UNLINKED_DAY, "10")
    await _barrier_links(owned, {case.event_id: (owned.market_assignment_id, [case.tx_id]), unlinked: (owned.market_assignment_id, []), manual: (None, [manual_on_a])}, "the provider's DIVIDEND linked to a transaction on broker A, its PRICE_ADJUSTMENT to none, a manual DIVIDEND linked")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    story = f"removing the provider of the asset {owned.market_asset_id} via the {via}, whose DIVIDEND {case.event_id} the transaction {case.tx_id} links to, beside a manual DIVIDEND {manual} linked to {manual_on_a}"

    answer = await _removed(owned, [owned.market_asset_id], story, via=via)

    _assert_answered_as_today(answer, [owned.market_asset_id], story)
    _assert_removed_and_disconnected(before, await _committed(owned), story, asset_ids={owned.market_asset_id}, disconnected={case.tx_id})


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_removing_a_plan_unlinks_the_interest_its_coupon_paid(owned, via):
    """Red today (X-R69), J's case: the removal is refused with PROVIDER_REMOVAL_LINKED_TRANSACTIONS (409 through the route)
    while the INTEREST a coupon paid links to it.

    Contract: the plan's coupon (day 28, an INTEREST event of the plan's assignment) is linked to the INTEREST of 3.33 EUR
    it paid on broker A. Removing the plan of the plan's asset, through the service or the route as user A: answered as
    before; the assignment gone with its coupon; the INTEREST transaction kept, unlinked, every other column as it was.
    """
    coupon = await _coupon(owned)
    await _barrier_links(owned, {coupon.event_id: (owned.plan_assignment_id, [coupon.tx_id])}, "the plan's coupon linked to the INTEREST it paid on broker A")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    story = f"removing the plan of the asset {owned.plan_asset_id} via the {via}, whose coupon {coupon.event_id} the INTEREST {coupon.tx_id} links to"

    answer = await _removed(owned, [owned.plan_asset_id], story, via=via)

    _assert_answered_as_today(answer, [owned.plan_asset_id], story)
    _assert_removed_and_disconnected(before, await _committed(owned), story, asset_ids={owned.plan_asset_id}, disconnected={coupon.tx_id})


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_the_unlinking_reaches_every_transaction_of_every_event_whoever_owns_the_broker(owned, via):
    """Red today (X-R69): the removal is refused while any transaction links to an event of the assignment.

    Contract: the market provider's DIVIDEND (day 20) linked to a DIVIDEND on broker B, written first (user B's, which user A
    cannot see), then on broker A; a second DIVIDEND (day 50) linked on broker B alone; a PRICE_ADJUSTMENT linked to
    nothing. Removing the provider through the service without a caller or the route as user A: every one of the three
    transactions is unlinked, visible to the caller or not (a removal's unlinking is not a view), nothing else moves.
    """
    first = await _event(owned.market_asset_id, DIVIDEND_DAY, AssetEventType.DIVIDEND, "0.50", assignment_id=owned.market_assignment_id)
    on_b = await _income(owned.market_asset_id, owned.broker_b_id, TransactionType.DIVIDEND, DIVIDEND_DAY, "5.00", event_id=first)
    on_a = await _income(owned.market_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, DIVIDEND_DAY, "5.00", event_id=first)
    second = await _event(owned.market_asset_id, LATE_DAY, AssetEventType.DIVIDEND, "0.60", assignment_id=owned.market_assignment_id)
    second_on_b = await _income(owned.market_asset_id, owned.broker_b_id, TransactionType.DIVIDEND, LATE_DAY, "6.00", event_id=second)
    other = await _event(owned.market_asset_id, UNLINKED_DAY, AssetEventType.PRICE_ADJUSTMENT, "-0.10", assignment_id=owned.market_assignment_id)
    await _barrier_links(owned, {first: (owned.market_assignment_id, sorted([on_b, on_a])), second: (owned.market_assignment_id, [second_on_b]), other: (owned.market_assignment_id, [])}, "two DIVIDENDs linked on both brokers, a PRICE_ADJUSTMENT to none")
    await _barrier_who_sees_what(owned)
    before = await _committed(owned)
    story = f"removing the provider of the asset {owned.market_asset_id} via the {via}, whose DIVIDENDs {first} and {second} the transactions {on_b} (broker B), {on_a} (broker A) and {second_on_b} (broker B) link to"

    answer = await _removed(owned, [owned.market_asset_id], story, via=via)

    _assert_answered_as_today(answer, [owned.market_asset_id], story)
    _assert_removed_and_disconnected(before, await _committed(owned), story, asset_ids={owned.market_asset_id}, disconnected={on_b, on_a, second_on_b})


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["market", "plan"])
async def test_removing_a_provider_whose_split_has_costless_adjustments_is_refused_with_the_changes_code(owned, role):
    """Red today (X-R69): the removal is refused with PROVIDER_REMOVAL_LINKED_TRANSACTIONS, the retired code.

    Contract: the provider's SPLIT of 2 (day 20) linked to an ADJUSTMENT +10 on broker A without a purchase cost (the case
    of P-10: without the SPLIT it would be an acquisition of unknown cost). As user A, removing the provider of the market
    asset or of the plan's is refused with PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST, X-R49's code; details exactly
    ``{"asset_id", "item_index": 0, "splits": [{event_id, date (day 20), transaction_ids [the adjustment],
    hidden_transactions_count 0}]}``, the message starting with the code and naming no id. Nothing written, not even
    pending in the refused call's session.
    """
    case = await _split_case(owned, role)
    await _barrier_links(owned, {case.split_id: (owned.market_assignment_id if role == "market" else owned.plan_assignment_id, case.adjustments)}, f"the {role} provider's SPLIT linked to a costless adjustment on broker A")
    before = await _committed(owned)
    story = f"user A removing the provider of the asset {case.asset_id} ({role}), whose SPLIT {case.split_id} of {_day(SPLIT_DAY)} the costless adjustment(s) {case.adjustments} (broker A, theirs) link to"

    refused = await _refused_remove(owned, [case.asset_id], before, story, current_user_id=owned.user_a_id)

    _assert_refused(refused.error, _split_details(case.asset_id, 0, [_split_entry(case.split_id, SPLIT_DAY, case.adjustments, 0)]), story, splits=1, adjustments=1, ids=case.adjustments)
    await _assert_nothing_written(owned, before, refused, story)


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_removing_a_provider_whose_split_adjustments_have_a_cost_unlinks_them_instead_of_refusing(owned, via):
    """Red today (X-R69): the removal is refused with PROVIDER_REMOVAL_LINKED_TRANSACTIONS.

    Contract: the same SPLIT, its ADJUSTMENT +10 on broker A with a cost of 12.5 EUR a unit, beside a DIVIDEND linked on
    broker A. The cost lifts X-R49's refusal: through the service or the route as user A the removal goes through, answered as
    before; the SPLIT and the DIVIDEND gone with the assignment, the adjustment and the DIVIDEND transaction kept, unlinked,
    every other column (the cost included) as it was.
    """
    case = await _split_case(owned, "market", cost="12.5")
    dividend = await _dividend(owned)
    await _barrier_links(owned, {case.split_id: (owned.market_assignment_id, case.adjustments), dividend.event_id: (owned.market_assignment_id, [dividend.tx_id])}, "the provider's SPLIT linked to an adjustment with a cost, its DIVIDEND to a transaction")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    story = f"removing the provider of the asset {owned.market_asset_id} via the {via}, whose SPLIT {case.split_id} the adjustment(s) {case.adjustments} with a cost link to"

    answer = await _removed(owned, [owned.market_asset_id], story, via=via)

    _assert_answered_as_today(answer, [owned.market_asset_id], story)
    _assert_removed_and_disconnected(before, await _committed(owned), story, asset_ids={owned.market_asset_id}, disconnected={*case.adjustments, dividend.tx_id})


@pytest.mark.asyncio
async def test_the_refusal_shows_each_caller_only_the_costless_adjustments_on_their_brokers(owned):
    """Red today (X-R69): the removal is refused with PROVIDER_REMOVAL_LINKED_TRANSACTIONS, naming events, not SPLITs.

    Contract (R13-SEC7's rule, as X-R48 and X-R49): the market provider's events spread over dates and brokers
    (``_Spread``): the SPLIT of day 20 linked to a costless adjustment on broker B, written first, then to a costless one and
    one with a cost on broker A; two DIVIDENDs and a PRICE_ADJUSTMENT; beside them a manual SPLIT (day 35) linked to a
    costless adjustment on broker A. The refusal names the provider's SPLIT alone (the DIVIDENDs are unlinked, the manual
    SPLIT survives the removal, the adjustment with a cost is not a costless one): as user A its costless adjustment on
    broker A and 1 hidden; as user B broker B's and 1 hidden; without a caller (the default, fail closed) none named and 2
    hidden. The message starts with the code and names no id. None of the three writes anything.
    """
    spread = await _spread(owned)
    manual = await _event(owned.market_asset_id, MANUAL_DAY, AssetEventType.SPLIT, "3", notes="manual 3-for-1")
    manual_on_a = await _adjustment(owned.market_asset_id, owned.broker_a_id, manual, MANUAL_DAY + 1)
    costless = sorted([spread.split_on_b, spread.split_on_a[0]])
    await _barrier_costless([spread.split, manual], {spread.split: costless, manual: [manual_on_a]}, "the provider's SPLIT and a manual SPLIT, both with costless adjustments")
    await _barrier_who_sees_what(owned)
    before = await _committed(owned)
    views = {
        "user A": ({"current_user_id": owned.user_a_id}, [_split_entry(spread.split, SPLIT_DAY, [spread.split_on_a[0]], 1)]),
        "user B": ({"current_user_id": owned.user_b_id}, [_split_entry(spread.split, SPLIT_DAY, [spread.split_on_b], 1)]),
        "no caller": ({}, [_split_entry(spread.split, SPLIT_DAY, [], 2)]),
    }
    story = f"removing the provider of the asset {owned.market_asset_id}, whose SPLIT {spread.split} the costless adjustments {costless} (brokers B and A) link to, beside a manual SPLIT {manual}"

    for caller, (keyword, splits) in views.items():
        refused = await _refused_remove(owned, [owned.market_asset_id], before, f"{caller} {story}", **keyword)
        _assert_refused(refused.error, _split_details(owned.market_asset_id, 0, splits), f"{caller} {story}", splits=1, adjustments=2, ids=[*costless, manual_on_a, *spread.split_on_a])
        await _assert_nothing_written(owned, before, refused, f"{caller} {story}")


@pytest.mark.asyncio
@pytest.mark.parametrize(("roles", "item_index"), [pytest.param(("market", "plan"), 1, id="removable-then-blocked"), pytest.param(("plan", "plan"), 0, id="blocked-twice"), pytest.param(("bare", "plan"), 1, id="unassigned-then-blocked")])
async def test_a_blocked_asset_refuses_the_whole_request_at_its_first_position(owned, roles, item_index):
    """Red today (X-R69): the request is refused with the retired code, naming a coupon-like event.

    Contract: all or nothing. The plan's SPLIT, linked to a costless adjustment on broker A, blocks the plan's asset; the
    market asset's provider, whose DIVIDEND a transaction links to (it would be unlinked), could go; the bare asset has no
    assignment. As user A: the market asset then the plan's, refused at ``item_index`` 1, the market asset's assignment
    removed neither, its DIVIDEND transaction still linked; the plan's twice, refused at 0, its first position; the bare asset
    then the plan's, refused at 1 (the bare asset skipped, still counted). Each refusal's details exactly ``{"asset_id": the
    plan's asset, "item_index", "splits": [the SPLIT, [its adjustment], 0 hidden]}``; nothing of the request written, in the
    refused call's session neither: the unlinking is part of what is not written.
    """
    plan = await _split_case(owned, "plan")
    dividend = await _dividend(owned)
    await _barrier_links(owned, {plan.split_id: (owned.plan_assignment_id, plan.adjustments), dividend.event_id: (owned.market_assignment_id, [dividend.tx_id])}, "the plan's SPLIT linked to a costless adjustment on broker A, the market provider's DIVIDEND to a transaction")
    before = await _committed(owned)
    _barrier_unassigned(before, owned.bare_asset_id, "the bare asset")
    asset_ids = [owned.role_ids[role] for role in roles]
    story = f"user A removing the providers of the assets {asset_ids} ({', '.join(roles)}), the plan's SPLIT {plan.split_id} linked to the costless adjustment(s) {plan.adjustments}, the market provider's DIVIDEND {dividend.event_id} to {dividend.tx_id}"

    refused = await _refused_remove(owned, asset_ids, before, story, current_user_id=owned.user_a_id)

    _assert_refused(refused.error, _split_details(owned.plan_asset_id, item_index, [_split_entry(plan.split_id, SPLIT_DAY, plan.adjustments, 0)]), story, splits=1, adjustments=1, ids=[*plan.adjustments, dividend.tx_id])
    await _assert_nothing_written(owned, before, refused, story)


@pytest.mark.asyncio
async def test_the_removal_endpoint_answers_409_with_the_changes_code_and_the_callers_view_and_writes_nothing(owned):
    """Red today (X-R69): 409, but ``error_code`` PROVIDER_REMOVAL_LINKED_TRANSACTIONS and ``params.events``; and for a SPLIT
    only, the code the route now answers does not exist for a removal: 500.

    Contract: ``DELETE /assets/provider?asset_ids=`` the market asset, as user A (in process), its provider's SPLIT (day
    20) linked to a costless adjustment on broker B, written first (user B's), and to one on broker A: 409, ``detail`` exactly
    {``error_code`` PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST, ``message`` (starting with the code, no id), ``params``
    {"asset_id", "item_index": 0, "splits": [{event_id, date, transaction_ids [broker A's], hidden_transactions_count
    1}]}}, user A's view: the route passes its caller. No SQL anywhere in the body; nothing written.
    """
    case = await _split_case(owned, "market", on_b=True)
    on_b, on_a = case.adjustments[0], case.adjustments[-1]
    before = await _committed(owned)
    story = f"DELETE /assets/provider as user A, the asset {owned.market_asset_id}, whose SPLIT {case.split_id} of {_day(SPLIT_DAY)} the costless adjustments {on_b} (broker B, user B's) and {on_a} (broker A, theirs) link to"

    response = await _route(owned.user_a_id, [owned.market_asset_id])

    if response.status_code == 200:
        pytest.fail(f"{story} answered 200 {response.text} and removed: {_changes(before, await _committed(owned))}: expected 409 {CODE}")
    message, params = _assert_answered_409(response, story, code=CODE)
    assert message.startswith(f"{CODE}:"), f"{story}: the 409's message reads {message!r}: expected it to start with {CODE}:"
    _assert_split_details(params, _split_details(owned.market_asset_id, 0, [_split_entry(case.split_id, SPLIT_DAY, [on_a], 1)]), story, "the 409's params")
    after = await _committed(owned)
    assert after == before, f"{story} was refused, yet the database changed: {_changes(before, after)}"


@contextmanager
def _link_made_before_the_delete(event_id: int, tx_id: int) -> Iterator[list[str]]:
    """The race of a link made after the removal disconnected its transactions and before it deletes: a listener on the
    lane's engine (``before_cursor_execute``) that, at the first DELETE of an assignment or of an event, sets the
    transaction ``tx_id``'s ``asset_event_id`` back to ``event_id`` on the same connection and in the same transaction, as a
    concurrent import would have. The RESTRICT of ``transactions.asset_event_id`` then stops the DELETE, whatever order the
    removal deletes in. Yields the statements the listener fired on (empty when the removal never deleted); the listener is
    removed on exit."""
    fired: list[str] = []

    def relink(connection, cursor, statement, parameters, context, executemany):  # noqa: ARG001 — the signature SQLAlchemy calls
        if fired or not statement.lstrip().upper().startswith(("DELETE FROM ASSET_PROVIDER_ASSIGNMENTS", "DELETE FROM ASSET_EVENTS")):
            return
        fired.append(statement)
        connection.exec_driver_sql("UPDATE transactions SET asset_event_id = ? WHERE id = ?", (event_id, tx_id))

    engine = get_async_engine().sync_engine
    event.listen(engine, "before_cursor_execute", relink)
    try:
        yield fired
    finally:
        event.remove(engine, "before_cursor_execute", relink)


@pytest.mark.asyncio
async def test_a_link_made_after_the_unlinking_is_a_conflict_rolled_back_and_nothing_is_removed(owned):
    """Red today (X-R69): the removal refuses first with PROVIDER_REMOVAL_LINKED_TRANSACTIONS, so the DELETE is never reached.

    Contract: the provider's DIVIDEND is linked to a DIVIDEND on broker A; a listener sets that link back just before the
    removal's first DELETE (``_link_made_before_the_delete``). As user A the DELETE raises an IntegrityError: the removal rolls
    its session back, then refuses with PROVIDER_REMOVAL_CONFLICT, ``details`` ``{}``, its message exactly ``CONFLICT_MESSAGE``.
    Nothing removed, and the unlinking rolled back with it: the assignment, its event and the link as they were; the refused
    call's session out of its transaction, nothing pending there; nothing committed.
    """
    case = await _dividend(owned)
    await _barrier_links(owned, {case.event_id: (owned.market_assignment_id, [case.tx_id])}, "the provider's DIVIDEND linked to a transaction on broker A")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    story = f"user A removing the provider of the asset {owned.market_asset_id}, the transaction {case.tx_id} linked back to its DIVIDEND {case.event_id} just before the DELETE"

    with _link_made_before_the_delete(case.event_id, case.tx_id) as fired:
        refused = await _refused_remove(owned, [owned.market_asset_id], before, story, code=CONFLICT, current_user_id=owned.user_a_id)

    assert fired, f"{story}: the removal never reached a DELETE of an assignment or of an event, so the race never happened"
    assert (refused.error.error_code, refused.error.details) == (CONFLICT, {}), f"{story} was refused with {refused.error.error_code} {refused.error.details} ({refused.error.message}): expected {CONFLICT} and no details"
    assert refused.error.message == CONFLICT_MESSAGE, f"{story}: the conflict's message reads {refused.error.message!r}: expected exactly {CONFLICT_MESSAGE!r}, never the SQL text"
    assert not refused.in_transaction, f"{story} was refused with its session still in a transaction, the failed DELETE's: the removal rolls the session back, then refuses"
    await _assert_nothing_written(owned, before, refused, story)


@pytest.mark.asyncio
async def test_the_removal_endpoint_answers_a_late_link_409_without_the_sql_text(owned):
    """Red today (X-R69): the route answers 409 PROVIDER_REMOVAL_LINKED_TRANSACTIONS from the check before the DELETE.

    Contract: the same race (``_link_made_before_the_delete``): ``DELETE /assets/provider`` as user A (in process) answers 409,
    ``detail`` exactly {``error_code`` PROVIDER_REMOVAL_CONFLICT, ``message`` ``CONFLICT_MESSAGE``, ``params`` {}}; no SQL anywhere
    in the body; nothing removed.
    """
    case = await _dividend(owned)
    await _barrier_links(owned, {case.event_id: (owned.market_assignment_id, [case.tx_id])}, "the provider's DIVIDEND linked to a transaction on broker A")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    story = f"DELETE /assets/provider as user A, the asset {owned.market_asset_id}, the transaction {case.tx_id} linked back to its DIVIDEND {case.event_id} just before the DELETE"

    with _link_made_before_the_delete(case.event_id, case.tx_id) as fired:
        response = await _route(owned.user_a_id, [owned.market_asset_id])

    assert fired, f"{story}: the removal never reached a DELETE of an assignment or of an event, so the race never happened"
    if response.status_code == 200:
        pytest.fail(f"{story} answered 200 {response.text} and removed: {_changes(before, await _committed(owned))}: expected 409 {CONFLICT}")
    message, params = _assert_answered_409(response, story, code=CONFLICT)
    assert message == CONFLICT_MESSAGE, f"{story}: the 409's message reads {message!r}: expected exactly {CONFLICT_MESSAGE!r}"
    assert params == {}, f"{story}: the 409's params are {params!r}: expected {{}}, a conflict names nothing"
    after = await _committed(owned)
    assert after == before, f"{story} was refused, yet the database changed: {_changes(before, after)}"


@pytest.mark.asyncio
async def test_visible_transaction_ids_keeps_only_the_transactions_on_the_callers_brokers(owned):
    """Guard: green before and after (the dry run reuses it).

    Contract: ``visible_transaction_ids(session, transaction_ids, current_user_id)``, of a DIVIDEND on broker B, written
    first, and one on broker A: user A keeps {broker A's}, user B {broker B's}; without a caller, or without an id, an
    empty set; user A given broker B's alone, an empty set. It writes nothing.
    """
    on_b = await _income(owned.market_asset_id, owned.broker_b_id, TransactionType.DIVIDEND, DIVIDEND_DAY, "5.00")
    on_a = await _income(owned.market_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, DIVIDEND_DAY, "5.00")
    await _barrier_who_sees_what(owned)
    before = await _committed(owned)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        found = {
            "user A, both": await visible_transaction_ids(session, [on_b, on_a], owned.user_a_id),
            "user B, both": await visible_transaction_ids(session, [on_b, on_a], owned.user_b_id),
            "no caller, both": await visible_transaction_ids(session, [on_b, on_a], None),
            "user A, no id": await visible_transaction_ids(session, [], owned.user_a_id),
            "user A, broker B's alone": await visible_transaction_ids(session, [on_b], owned.user_a_id),
        }

    expected = {"user A, both": {on_a}, "user B, both": {on_b}, "no caller, both": set(), "user A, no id": set(), "user A, broker B's alone": set()}
    assert found == expected, f"visible_transaction_ids of the transactions {on_b} (broker B) and {on_a} (broker A) gives {found}: expected {expected}, as sets: the ids on a broker the caller holds an access to; none without a caller or without an id"
    after = await _committed(owned)
    assert after == before, f"visible_transaction_ids wrote: {_changes(before, after)}"


@pytest.mark.asyncio
async def test_events_with_linked_transactions_lists_the_linked_events_in_date_order_as_each_caller_sees_them(owned):
    """Guard: green before and after (the dry run reuses it).

    Contract: ``events_with_linked_transactions(session, events, current_user_id)``, ``events`` given as ``(event_id,
    date, type)`` and out of order: the market provider's events spread over dates and brokers (``_Spread``). The linked
    ones, by (date, id): the SPLIT, the DIVIDEND of day 20, the DIVIDEND of day 50; each exactly ``{event_id, date
    (ISO), type, transaction_ids (the caller's, sorted), hidden_transactions_count}``, for user A, user B and no caller
    each their view. The PRICE_ADJUSTMENT, linked to nothing, never: alone it gives ``[]``, as no event does. It writes
    nothing.
    """
    spread = await _spread(owned)
    await _barrier_links(owned, spread.links(owned.market_assignment_id), "the provider's events spread over dates and brokers")
    await _barrier_who_sees_what(owned)
    before = await _committed(owned)
    views = _views(spread)
    given = [(spread.late, _day(LATE_DAY), AssetEventType.DIVIDEND), (spread.unlinked, _day(UNLINKED_DAY), AssetEventType.PRICE_ADJUSTMENT), (spread.early, _day(DIVIDEND_DAY), AssetEventType.DIVIDEND), (spread.split, _day(SPLIT_DAY), AssetEventType.SPLIT)]
    story = f"events_with_linked_transactions of the events {[event_id for event_id, _, _ in given]}, given in that order"

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        found = {
            "user A": await events_with_linked_transactions(session, given, owned.user_a_id),
            "user B": await events_with_linked_transactions(session, given, owned.user_b_id),
            "no caller": await events_with_linked_transactions(session, given, None),
        }
        unlinked_alone = await events_with_linked_transactions(session, [given[1]], owned.user_a_id)
        no_event = await events_with_linked_transactions(session, [], owned.user_a_id)

    for caller, events in found.items():
        _assert_events(events, views[caller], f"{story}, for {caller}", "they")
    assert (unlinked_alone, no_event) == ([], []), f"{story}: the PRICE_ADJUSTMENT {spread.unlinked} alone gives {unlinked_alone!r} and no event {no_event!r}: expected [] for both, no event a transaction links to"
    after = await _committed(owned)
    assert after == before, f"{story} wrote: {_changes(before, after)}"


# ─────────────────────────────────────────────────────────────────────────────
# Guards: green before and after the cure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_guard_a_provider_without_a_linked_transaction_is_removed_as_today_with_its_events(owned, via):
    """Guard: green today and after. The market provider's PRICE_ADJUSTMENT, SPLIT and DIVIDEND, which no transaction
    links to, and a BUY of the market asset linked to no event; beside them the plan's coupon, linked to nothing, under an
    assignment the request leaves alone. Removing the market asset's provider, through the service without a caller, as
    the route calls it today, or ``DELETE /assets/provider`` as user A (in process): answered as today, a success; the
    assignment gone with its three events (the cascade); the BUY, the plan's assignment and its coupon as they were,
    every column."""
    adjusted = await _event(owned.market_asset_id, UNLINKED_DAY, AssetEventType.PRICE_ADJUSTMENT, "-0.10", assignment_id=owned.market_assignment_id)
    split = await _event(owned.market_asset_id, SPLIT_DAY, AssetEventType.SPLIT, "2", assignment_id=owned.market_assignment_id, notes="2-for-1")
    dividend = await _event(owned.market_asset_id, DIVIDEND_DAY, AssetEventType.DIVIDEND, "0.50", assignment_id=owned.market_assignment_id)
    buy = await _buy(owned.market_asset_id, owned.broker_a_id, UNLINKED_DAY)
    coupon = await _event(owned.plan_asset_id, COUPON_DAY, AssetEventType.INTEREST, "3.33", assignment_id=owned.plan_assignment_id)
    unlinked = (owned.market_assignment_id, [])
    await _barrier_links(owned, {adjusted: unlinked, split: unlinked, dividend: unlinked, coupon: (owned.plan_assignment_id, [])}, "the market provider's three events and the plan's coupon, linked to nothing")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    story = f"removing the provider of the asset {owned.market_asset_id} via the {via}, its events {[adjusted, split, dividend]} linked to nothing, its BUY {buy} to no event"

    answer = await _removed(owned, [owned.market_asset_id], story, via=via)

    _assert_answered_as_today(answer, [owned.market_asset_id], story)
    _assert_removed(before, await _committed(owned), story, asset_ids={owned.market_asset_id})


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_guard_a_manual_event_with_a_linked_transaction_does_not_block_the_removal(owned, via):
    """Guard: green today and after. On the market asset a manual DIVIDEND (day 35, no assignment: the user's own)
    linked to a DIVIDEND on broker A, beside the provider's DIVIDEND, which no transaction links to. Removing the market
    asset's provider, through the service without a caller or the route as user A: answered as today; the assignment
    gone with the provider's DIVIDEND; the manual DIVIDEND and its transaction as they were, every column, still linked.
    The removal deletes the events of the assignment alone, so the check reads those alone."""
    manual = await _event(owned.market_asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
    manual_on_a = await _income(owned.market_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, MANUAL_DAY, "4.50", event_id=manual)
    generated = await _event(owned.market_asset_id, DIVIDEND_DAY, AssetEventType.DIVIDEND, "0.50", assignment_id=owned.market_assignment_id)
    await _barrier_links(owned, {manual: (None, [manual_on_a]), generated: (owned.market_assignment_id, [])}, "a manual DIVIDEND linked on broker A, the provider's DIVIDEND linked to nothing")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    story = f"removing the provider of the asset {owned.market_asset_id} via the {via}, whose manual DIVIDEND {manual} (no assignment) the transaction {manual_on_a} links to, beside the provider's DIVIDEND {generated}, linked to nothing"

    answer = await _removed(owned, [owned.market_asset_id], story, via=via)

    _assert_answered_as_today(answer, [owned.market_asset_id], story)
    _assert_removed(before, await _committed(owned), story, asset_ids={owned.market_asset_id})


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_guard_an_asset_without_an_assignment_is_answered_as_today(owned, via):
    """Guard: green today and after. The bare asset has no assignment, and a manual DIVIDEND linked to a DIVIDEND on
    broker A; the market provider's DIVIDEND is linked to nothing. Removing the providers of both, the bare asset first,
    through the service without a caller or the route as user A: no error, both answered as today (a success,
    ``deleted_count`` 1 and "Provider removed", the bare asset's too); the market asset's assignment gone with its
    DIVIDEND; the bare asset still without one, its event and transaction as they were."""
    manual = await _event(owned.bare_asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
    manual_on_a = await _income(owned.bare_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, MANUAL_DAY, "4.50", event_id=manual)
    generated = await _event(owned.market_asset_id, DIVIDEND_DAY, AssetEventType.DIVIDEND, "0.50", assignment_id=owned.market_assignment_id)
    await _barrier_links(owned, {manual: (None, [manual_on_a]), generated: (owned.market_assignment_id, [])}, "the bare asset's manual DIVIDEND linked on broker A, the market provider's DIVIDEND linked to nothing")
    await _barrier_foreign_keys()
    before = await _committed(owned)
    _barrier_unassigned(before, owned.bare_asset_id, "the bare asset")
    asset_ids = [owned.bare_asset_id, owned.market_asset_id]
    story = f"removing the providers of the assets {asset_ids} via the {via}: the first without an assignment, its manual DIVIDEND {manual} linked to the transaction {manual_on_a}; the second's DIVIDEND {generated} linked to nothing"

    answer = await _removed(owned, asset_ids, story, via=via)

    _assert_answered_as_today(answer, asset_ids, story)
    _assert_removed(before, await _committed(owned), story, asset_ids=set(asset_ids))


@pytest.mark.asyncio
async def test_guard_an_empty_request_answers_nothing_as_today(owned):
    """Guard: green today and after. The provider's DIVIDEND linked to a DIVIDEND on broker A, and a request naming no
    asset, through the service without a caller (the route requires ``asset_ids``): answered as today, no result,
    ``success_count`` 0, no error; nothing written."""
    case = await _dividend(owned)
    await _barrier_links(owned, {case.event_id: (owned.market_assignment_id, [case.tx_id])}, "the provider's DIVIDEND linked to a transaction on broker A")
    before = await _committed(owned)
    story = f"removing the providers of no asset, while the DIVIDEND {case.event_id} of the asset {owned.market_asset_id} is linked to the transaction {case.tx_id}"

    answer = await _removed(owned, [], story, via="service")

    _assert_answered_as_today(answer, [], story)
    after = await _committed(owned)
    assert after == before, f"{story} changed the database: {_changes(before, after)}"
