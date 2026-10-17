"""X-R49 (workstream X): changing a Scheduled Investment's plan, or leaving it for another provider, deletes the plan's
SPLITs that costless incoming adjustments rely on.

Measured before the cure (read at 8aafffad8): ``ProviderManagementOperations.bulk_assign_providers``
(``services/assets/provider_management.py``, reached as ``AssetSourceManager.bulk_assign_providers``) saves the items of
the request one by one. For an asset that already has an assignment it wipes when a parametric provider
(``provider_kind == PARAMETRIC_GENERATION``: ``scheduled_investment``) keeps its code and its ``provider_params`` change,
or when the asset leaves a parametric provider for another code: every price of the asset and every event of that
assignment (``provider_assignment_id`` its id) deleted, the transactions linked to those events first set
``asset_event_id = NULL``; manual events (``provider_assignment_id IS NULL``) stay. The assignment then takes the item's
code, identifier, input type and params; one commit after the last item; every item answers ``success=True``. A plan
(``FAScheduledInvestmentSchedule``) lists its events in ``asset_events``, a SPLIT as any other, and the provider's
refresh stores them as events of its assignment: the wipe deletes the plan's SPLIT. Linked to a SPLIT, an incoming
ADJUSTMENT needs no cost of its own: it only rescales the position, and the Auto mode stores none
(``financial_math.splits.costless_incoming_split_adjustments`` lists those rows). Disconnected by the wipe, it becomes an
acquisition of unknown cost: ``MISSING_COST_BASIS`` on the Dashboard and in the lots. The asset is global: the
adjustments the wipe disconnects may sit on another user's broker. The route (``POST /api/v1/assets/provider``,
``api/v1/assets/providers.py``) answers any exception 500 with a string detail; and the save knows no caller: given a
``current_user_id``, it raises ``TypeError``.

The cure's contract (X-R49: P-10's guard, decision 27, applied to the plan's wipe, as X-R48 applied it to the
currency-change wipe):

* ``bulk_assign_providers(assignments, session, *, current_user_id=None)``; the route passes
  ``current_user_id=_current_user.id``;
* before the wipe of an item, with the events of that item's assignment: when a SPLIT among them has costless incoming
  adjustments, ``AssetSourceError`` ``PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST``, its ``details`` exactly
  ``{"asset_id", "item_index" (the item's position in the request), "splits": [...]}``, ``splits`` as X-R48's: one entry
  per such SPLIT, ordered by (event date, event id), each exactly ``{"event_id", "date" (the event's, ISO),
  "transaction_ids", "hidden_transactions_count"}``: ``transaction_ids`` the adjustments the caller can see, sorted (a
  ``BrokerUserAccess`` row of ``current_user_id`` for the transaction's broker), ``hidden_transactions_count`` the
  others; without a ``current_user_id`` none is named and all are counted. The message gives the totals only (how many
  SPLITs, how many adjustments), never an id, whoever asks. All or nothing: nothing of the request is written, the items
  before the refused one included: prices, events (every column, ``updated_at`` included), every transaction (its
  ``asset_event_id`` above all) and every assignment (its code and params above all) as they were, not even pending in
  the refused call's session (a caller committing after the refusal would store them), nothing committed;
* the route answers it 409, ``detail`` exactly ``{"error_code", "message", "params"}``, ``params`` the details, the
  caller's view; every other answer unchanged.

Guards, green before and after: the plan's SPLIT whose incoming adjustment has a cost (0 included), a manual SPLIT with a
costless adjustment (the wipe leaves manual events), the same params (no wipe), an online provider whose params change
(no wipe, even with a SPLIT of its assignment), a new assignment (nothing to wipe), through the service and the route:
the save goes through as today, every item a success, the wipe today's or none.

A refusal is looked for as the router meets it: nobody commits after a refused call, the session just closes. The refused
call's own session is read right after it (raw SQL, so a write made before the refusal shows, committed or not) and, once
that session is closed, a fresh connection reads what is committed; every column, ``updated_at`` included. A call that
raises today where the contract refuses (the ``TypeError`` of the unknown keyword) fails its test naming the exception,
never as an error; a save that goes through fails its test with what it deleted, disconnected and rewrote. The route
tests call the route in process: the provider router mounted at ``/api/v1/assets`` as the app mounts it, on an app of
the call's own, ``get_current_user`` overridden there to the unit's user, the session the real dependency opens; the
answer read as the client reads it, JSON. Each red says what the user faces before the cure («Red today»); a guard
passes before and after.

Isolation: WRITE-SCOPED, the services default. Every row is this unit's own, under a unique marker: four EUR assets (the
plan's, assigned to ``scheduled_investment`` with a plan whose events hold a SPLIT; a sibling plan's, the same provider
with a plan without one; an online one, assigned to ``yfinance`` under a ticker of the unit's own; a fresh one without an
assignment), their three assignments, two users and two brokers, user A holding an access to broker A alone, user B to
broker B alone. Nothing is fetched: saving an assignment asks no provider for data. Each test starts from the three
assignments as the module wrote them (restored by id), the fresh asset without one, and no price, event or transaction;
only the rows of those assets and brokers are written, read and wiped, by asset and broker id. Nothing here counts or
reads a row it did not write.
"""

import asyncio
import json
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
from sqlalchemy import bindparam, delete, or_, select, text, update
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
from backend.app.schemas.provider import FAProviderAssignmentItem, FAProviderKind
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.financial_math.splits import costless_incoming_split_adjustments
from backend.test_scripts.test_utils import unique_id

#: The refusal's code (X-R49).
CODE = "PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST"
#: The parametric provider, whose plan generates the asset's series and events, and an online one.
PLAN = "scheduled_investment"
ONLINE = "yfinance"
#: The plans' annual rate as stored, and the rate a change asks for.
OLD_RATE = "0.04"
NEW_RATE = "0.05"
#: The online assignment's params as stored, and as a change sends them (yfinance reads none: any object is valid).
ONLINE_PARAMS = {"note": "X-R49 first"}
ONLINE_PARAMS_CHANGED = {"note": "X-R49 second"}
#: The route under test, as the app mounts it.
ASSIGN_PATH = "/api/v1/assets/provider"
#: The unit's assets by role.
ASSET_TYPES = {"plan": AssetType.BOND, "sibling": AssetType.BOND, "online": AssetType.STOCK, "fresh": AssetType.BOND}

# A window far from the mock dataset and from the other split units (1988, 1990, 1991-1992, 1994-1995), inside the plans'
# year. Rows are scoped by asset and broker anyway: the dates only keep the failure output readable.
BASE_DATE = date(1986, 3, 3)
#: Offsets from BASE_DATE: the plan's SPLIT (one of its planned events), a plan's coupon, a manual SPLIT.
SPLIT_DAY = 10
COUPON_DAY = 28
MANUAL_SPLIT_DAY = 40


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


# --------------------------------------------------------------------------- #
# Plans, requests and the assignments as the module writes them
# --------------------------------------------------------------------------- #


def _plan(rate: str, *, split: bool = True) -> dict:
    """A plan (``FAScheduledInvestmentSchedule``): 1 000 EUR over 1986 at ``rate``, monthly coupons; among its planned
    events the SPLIT of 2 of day ``SPLIT_DAY``, or none. A new dict at each call."""
    planned = [{"date": _day(SPLIT_DAY).isoformat(), "type": "SPLIT", "value": {"code": "EUR", "amount": "2"}, "notes": "2-for-1"}] if split else []
    period = {"start_date": "1986-01-01", "end_date": "1986-12-31", "annual_rate": rate, "maturation_frequency": "MONTHLY", "generate_interest": True}
    return {"initial_value": {"code": "EUR", "amount": "1000.00"}, "schedule": [period], "asset_events": planned}


def _plan_item(asset_id: int, rate: str, *, split: bool = True) -> FAProviderAssignmentItem:
    """An item assigning ``asset_id`` the plan at ``rate``, as the asset form sends it: an empty AUTO_GENERATED
    identifier."""
    return FAProviderAssignmentItem(asset_id=asset_id, provider_code=PLAN, identifier="", identifier_type=ProviderInputType.AUTO_GENERATED.value, provider_params=_plan(rate, split=split))


def _online_item(asset_id: int, ticker: str, params: dict | None) -> FAProviderAssignmentItem:
    """An item assigning ``asset_id`` yfinance under ``ticker``, with ``params``."""
    return FAProviderAssignmentItem(asset_id=asset_id, provider_code=ONLINE, identifier=ticker, identifier_type=ProviderInputType.TICKER.value, provider_params=params)


def _params_text(item: FAProviderAssignmentItem) -> str | None:
    """The params of ``item`` as the save stores them: JSON text, or NULL."""
    return None if item.provider_params is None else json.dumps(item.provider_params)


def _saved(item: FAProviderAssignmentItem) -> dict:
    """The columns the save writes from ``item``, as raw SQL reads them: its code, identifier (an empty AUTO_GENERATED one
    stored NULL), input type and params."""
    return {"provider_code": item.provider_code, "identifier": item.identifier or None, "identifier_type": item.identifier_type, "provider_params": _params_text(item)}


def _columns(code: str, identifier: str | None, identifier_type: ProviderInputType, params: dict) -> dict:
    return {"provider_code": code, "identifier": identifier, "identifier_type": identifier_type, "provider_params": json.dumps(params), "last_fetch_at": None}


def _seeded(ticker: str) -> dict[str, dict]:
    """The columns of the three assignments the module writes, by role, as every test finds them: the plan at OLD_RATE,
    the SPLIT among its planned events; the sibling plan at OLD_RATE, without one; yfinance under the unit's ticker."""
    return {
        "plan": _columns(PLAN, None, ProviderInputType.AUTO_GENERATED, _plan(OLD_RATE)),
        "sibling": _columns(PLAN, None, ProviderInputType.AUTO_GENERATED, _plan(OLD_RATE, split=False)),
        "online": _columns(ONLINE, ticker, ProviderInputType.TICKER, ONLINE_PARAMS),
    }


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Owned:
    """What this unit created: the plan's asset (``scheduled_investment``, the SPLIT among the plan's events), the sibling
    plan's (the same provider, a plan without a SPLIT), the online one (``yfinance`` under ``ticker``) and their
    assignments; the fresh asset, without one; two users and two brokers, user A holding an access to broker A alone, user
    B to broker B alone."""

    plan_asset_id: int
    sibling_asset_id: int
    online_asset_id: int
    fresh_asset_id: int
    plan_assignment_id: int
    sibling_assignment_id: int
    online_assignment_id: int
    ticker: str
    user_a_id: int
    user_b_id: int
    broker_a_id: int
    broker_b_id: int

    @property
    def asset_ids(self) -> list[int]:
        return [self.plan_asset_id, self.sibling_asset_id, self.online_asset_id, self.fresh_asset_id]

    @property
    def assignment_ids(self) -> dict[str, int]:
        return {"plan": self.plan_assignment_id, "sibling": self.sibling_assignment_id, "online": self.online_assignment_id}

    @property
    def user_ids(self) -> list[int]:
        return [self.user_a_id, self.user_b_id]

    @property
    def broker_ids(self) -> list[int]:
        return [self.broker_a_id, self.broker_b_id]


async def _reset(owned: _Owned) -> None:
    """Back to where every test starts: no transaction on the unit's brokers (they RESTRICT the events they link to), no
    event and no price of its assets, the fresh asset without an assignment, the three others as the module wrote them,
    by id. Bulk statements: no row is loaded."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(Transaction).where(Transaction.broker_id.in_(owned.broker_ids)))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)))
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned.asset_ids)))
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == owned.fresh_asset_id))
        for role, columns in _seeded(owned.ticker).items():
            await session.execute(update(AssetProviderAssignment).where(AssetProviderAssignment.id == owned.assignment_ids[role]).values(**columns))
        await session.commit()


@pytest.fixture(scope="module")
def owned_module() -> _Owned:
    """The assets, the assignments, the users, the brokers and the accesses, under names no concurrent worker can repeat,
    dropped in FK-safe order in teardown with every price, event and transaction written against them."""
    marker = f"{unique_id('XR49')}_{uuid.uuid4().hex[:8]}"
    ticker = f"XR49.{uuid.uuid4().hex[:10].upper()}"

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            assets = {role: Asset(display_name=f"X-R49 {role} {marker}", currency="EUR", asset_type=asset_type, active=True) for role, asset_type in ASSET_TYPES.items()}
            user_a = User(username=f"xr49a_{marker}".lower(), email=f"xr49a_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            user_b = User(username=f"xr49b_{marker}".lower(), email=f"xr49b_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            broker_a = Broker(name=f"X-R49 A {marker}")
            broker_b = Broker(name=f"X-R49 B {marker}")
            session.add_all([*assets.values(), user_a, user_b, broker_a, broker_b])
            await session.commit()
            assignments = {role: AssetProviderAssignment(asset_id=assets[role].id, **columns) for role, columns in _seeded(ticker).items()}
            access_a = BrokerUserAccess(user_id=user_a.id, broker_id=broker_a.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            access_b = BrokerUserAccess(user_id=user_b.id, broker_id=broker_b.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            session.add_all([*assignments.values(), access_a, access_b])
            await session.commit()
            return _Owned(
                plan_asset_id=assets["plan"].id,
                sibling_asset_id=assets["sibling"].id,
                online_asset_id=assets["online"].id,
                fresh_asset_id=assets["fresh"].id,
                plan_assignment_id=assignments["plan"].id,
                sibling_assignment_id=assignments["sibling"].id,
                online_assignment_id=assignments["online"].id,
                ticker=ticker,
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                broker_a_id=broker_a.id,
                broker_b_id=broker_b.id,
            )

    async def _drop(owned: _Owned) -> None:
        await _reset(owned)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(BrokerUserAccess).where(or_(BrokerUserAccess.broker_id.in_(owned.broker_ids), BrokerUserAccess.user_id.in_(owned.user_ids))))
            await session.execute(delete(Broker).where(Broker.id.in_(owned.broker_ids)))
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(owned.asset_ids)))
            await session.execute(delete(Asset).where(Asset.id.in_(owned.asset_ids)))
            await session.execute(delete(User).where(User.id.in_(owned.user_ids)))
            await session.commit()

    owned = asyncio.run(_create())
    yield owned
    asyncio.run(_drop(owned))


@pytest_asyncio.fixture
async def owned(owned_module: _Owned):
    """The module's rows as they were written, with no price, no event and no transaction, before and after the test."""
    await _reset(owned_module)
    yield owned_module
    await _reset(owned_module)


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
    """An event of ``asset_id`` on day ``offset``, in EUR, as a refresh under ``assignment_id`` stores it, or, without
    one, as a manual save left it: its id."""
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


@dataclass(frozen=True)
class _Coupon:
    """A plan's coupon, an INTEREST event of its assignment, with the INTEREST transaction linked to it; and a price of
    the plan's asset."""

    price_id: int
    event_id: int
    tx_id: int


async def _coupon(owned: _Owned, asset_id: int, assignment_id: int) -> _Coupon:
    """On ``asset_id``: a price (day ``SPLIT_DAY - 1``) and a coupon of 3.33 EUR (day ``COUPON_DAY``), an event of
    ``assignment_id`` as the plan's refresh stores it, linked to an INTEREST of 3.33 EUR on broker A booked that day:
    what a wipe of the plan deletes and disconnects."""
    price_id = await _price(asset_id, SPLIT_DAY - 1, "1000")
    event_id = await _event(asset_id, COUPON_DAY, AssetEventType.INTEREST, "3.33", assignment_id=assignment_id)
    tx_id = await _add(Transaction(broker_id=owned.broker_a_id, asset_id=asset_id, type=TransactionType.INTEREST, date=_day(COUPON_DAY), quantity=Decimal("0"), amount=Decimal("3.33"), currency="EUR", asset_event_id=event_id))
    return _Coupon(price_id=price_id, event_id=event_id, tx_id=tx_id)


# --------------------------------------------------------------------------- #
# Barriers: the case is the one the test names
# --------------------------------------------------------------------------- #


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


def _barrier_kinds() -> None:
    """Barrier: scheduled_investment generates its series from its params (PARAMETRIC_GENERATION) and yfinance does not,
    as the save's wipe rule reads them from the registry."""
    kinds = {code: getattr(AssetProviderRegistry.get_provider_instance(code), "provider_kind", None) for code in (PLAN, ONLINE)}
    assert kinds[PLAN] == FAProviderKind.PARAMETRIC_GENERATION and kinds[ONLINE] not in (None, FAProviderKind.PARAMETRIC_GENERATION), f"barrier: the providers' kinds are {kinds}: expected {PLAN} parametric, {ONLINE} registered and not parametric"


async def _barrier_change(item: FAProviderAssignmentItem, *, same: bool, story: str) -> None:
    """Barrier: the item's asset holds an assignment whose code and params ``item`` keeps, as the very text the save
    stores (``same``), or not (a change, or no assignment at all); and the providers' kinds are those the wipe's rule reads.
    So the save wipes, or does not, for the reason the test names."""
    _barrier_kinds()
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        row = (await session.execute(select(AssetProviderAssignment.provider_code, AssetProviderAssignment.provider_params).where(AssetProviderAssignment.asset_id == item.asset_id))).one_or_none()
    stored = None if row is None else tuple(row)
    sent = (item.provider_code, _params_text(item))
    assert (stored == sent) == same, f"barrier: {story}: the asset {item.asset_id} holds {stored or 'no assignment'} as (code, params) and the request sends {sent}: expected {'the same' if same else 'a change'}"


# --------------------------------------------------------------------------- #
# Reading back: raw SQL, every column
# --------------------------------------------------------------------------- #

_RAW_PRICES = text("SELECT id, asset_id, date, open, high, low, close, volume, adjusted_close, currency, source_plugin_key, fetched_at FROM price_history WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))
_RAW_EVENTS = text("SELECT id, asset_id, date, type, value, currency, provider_assignment_id, notes, created_at, updated_at FROM asset_events WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))
_RAW_TRANSACTIONS = text("SELECT id, broker_id, asset_id, type, date, quantity, amount, currency, related_transaction_id, tags, description, cost_basis_override, cost_basis_currency, asset_event_id, created_at, updated_at FROM transactions WHERE broker_id IN :broker_ids ORDER BY id").bindparams(
    bindparam("broker_ids", expanding=True)
)
_RAW_ASSIGNMENTS = text("SELECT id, asset_id, provider_code, identifier, identifier_type, provider_params, last_fetch_at, created_at, updated_at FROM asset_provider_assignments WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))

_TABLES = ("prices", "events", "transactions", "assignments")


@dataclass(frozen=True)
class _State:
    """Every price, event and assignment of the unit's assets and every transaction on its brokers: id -> its columns."""

    prices: dict[int, dict]
    events: dict[int, dict]
    transactions: dict[int, dict]
    assignments: dict[int, dict]


def _by_id(rows) -> dict[int, dict]:
    return {row["id"]: dict(row) for row in rows}


async def _read(session: AsyncSession, owned: _Owned) -> _State:
    """``_State`` through ``session``, with raw SQL: a session that wrote reads its own writes, committed or not."""
    assets, brokers = {"asset_ids": owned.asset_ids}, {"broker_ids": owned.broker_ids}
    prices = (await session.execute(_RAW_PRICES, assets)).mappings().all()
    events = (await session.execute(_RAW_EVENTS, assets)).mappings().all()
    transactions = (await session.execute(_RAW_TRANSACTIONS, brokers)).mappings().all()
    assignments = (await session.execute(_RAW_ASSIGNMENTS, assets)).mappings().all()
    return _State(prices=_by_id(prices), events=_by_id(events), transactions=_by_id(transactions), assignments=_by_id(assignments))


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
    moved = [_table_changes(name, getattr(before, name), getattr(after, name)) for name in _TABLES if getattr(before, name) != getattr(after, name)]
    return "; ".join(moved) or "nothing"


def _undated(row: dict) -> dict:
    """A row with ``updated_at`` left out."""
    return {key: value for key, value in row.items() if key != "updated_at"}


def _unlinked(row: dict) -> dict:
    """A transaction row as the wipe leaves a disconnected one: its link NULL, ``updated_at`` left out (the contract does
    not fix it)."""
    return {key: (None if key == "asset_event_id" else value) for key, value in row.items() if key != "updated_at"}


# --------------------------------------------------------------------------- #
# The save, called as the route calls it
# --------------------------------------------------------------------------- #


async def _refused_assign(owned: _Owned, items: list[FAProviderAssignmentItem], before: _State, story: str, **caller: int) -> tuple[AssetSourceError, _State]:
    """The save of ``items``, for a request the contract refuses, ``caller`` the ``current_user_id`` it is given if any:
    the refusal, and what the refused call's own session reads right after it, its writes included, committed or not. As
    in the route, nobody commits after it: the session closes. Any other exception fails the test, naming it (the
    ``TypeError`` of the unknown keyword before the cure); so does a save that goes through, saying what it deleted,
    disconnected and rewrote against ``before``."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            results = await AssetSourceManager.bulk_assign_providers(items, session, **caller)
        except AssetSourceError as refusal:
            return refusal, await _read(session, owned)
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            given = f" (X-R49: the save takes the caller as the keyword current_user_id, here {caller})" if caller else ""
            pytest.fail(
                f"{story} raised {exc!r} instead of the refusal {CODE}{given}. Today the route calls the save without a caller and it goes through: it deletes the events of the plan's assignment, its SPLIT included, and every price of the asset, and disconnects the transactions linked to them; a costless incoming adjustment becomes an acquisition of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots)"
            )
    answered = [(result.asset_id, result.success) for result in results]
    pytest.fail(
        f"{story} went through, answering {answered} as (asset, success), instead of being refused with {CODE}: {_changes(before, await _committed(owned))}. Each costless incoming adjustment disconnected from the plan's SPLIT is now an acquisition of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots), on whichever user's broker it sits"
    )


async def _save(owned: _Owned, items: list[FAProviderAssignmentItem], story: str, *, via: str = "service") -> list[tuple[object, object]]:
    """``items`` saved through ``via``, for a save that must go through: the service without a caller, as the route calls
    it today, or ``POST /assets/provider`` in process as user A; each item's (asset id, success) as answered. A refusal,
    another status or any other exception fails the test, naming it."""
    if via == "route":
        return await _route_answers(owned.user_a_id, items, story)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            results = await AssetSourceManager.bulk_assign_providers(items, session)
        except AssetSourceError as refusal:
            pytest.fail(f"{story} was refused: {refusal.error_code} {refusal.message} {refusal.details} (X-R49 refuses only a save that deletes a SPLIT of the item's assignment while incoming adjustments linked to it have no cost)")
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story} raised {exc!r}: the route answers 500")
    return [(result.asset_id, result.success) for result in results]


# --------------------------------------------------------------------------- #
# The route, in process
# --------------------------------------------------------------------------- #


async def _caller(user_id: int) -> User:
    """The user ``user_id`` as ``get_current_user`` hands it to a route: the row, loaded and detached."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None, f"barrier: the unit's user {user_id} is gone"
    return user


async def _route(user_id: int, items: list[FAProviderAssignmentItem]) -> httpx.Response:
    """``POST /api/v1/assets/provider`` in process, as the user ``user_id``, ``items`` the body as the client sends it: the
    provider router mounted at ``/api/v1/assets`` as the app mounts it (``asset_router`` includes it under ``/assets``,
    the app the v1 router under ``/api/v1``), on an app of the call's own, so ``get_current_user`` is overridden there,
    never on the shared app, with the session the real dependency opens on the lane's database. Nothing is mocked behind
    the route."""
    caller = await _caller(user_id)
    app = FastAPI()
    app.include_router(providers_api.provider_router, prefix="/api/v1/assets")
    app.dependency_overrides[get_current_user] = lambda: caller
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(ASSIGN_PATH, json=[item.model_dump(mode="json") for item in items])


def _body(response: httpx.Response) -> object:
    """The JSON body as the client reads it: None when there is none to read (a 500's text)."""
    try:
        return response.json()
    except ValueError:
        return None


def _detail(response: httpx.Response) -> dict:
    """The structured ``detail`` of an answer: {} when the body holds no object there (a 200, a string detail, a 500's
    text)."""
    body = _body(response)
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, dict) else {}


async def _route_answers(user_id: int, items: list[FAProviderAssignmentItem], story: str) -> list[tuple[object, object]]:
    """``items`` saved through the route as the user ``user_id``, for a save that must go through: each item's (asset id,
    success) as the client reads them. Another status fails the test, with the answer."""
    response = await _route(user_id, items)
    body = _body(response)
    results = body.get("results") if isinstance(body, dict) else None
    assert response.status_code == 200 and isinstance(results, list), f"{story} answers {response.status_code} {response.text}: expected 200 and the results, as today"
    assert body.get("success_count") == len(items), f"{story} answers {response.text}: expected success_count {len(items)}, as today"
    return [(result.get("asset_id"), result.get("success")) for result in results]


# --------------------------------------------------------------------------- #
# What the contract expects
# --------------------------------------------------------------------------- #


def _entry(event_id: int, offset: int, seen: list[int], hidden: int) -> dict:
    """One SPLIT of the refusal, as the contract gives it: the event, its date, the adjustments the caller sees, how many
    it does not."""
    return {"event_id": event_id, "date": _day(offset).isoformat(), "transaction_ids": seen, "hidden_transactions_count": hidden}


def _details(asset_id: int, item_index: int, splits: list[dict]) -> dict:
    """The refusal's details, as the contract gives them: the refused item's asset, its position in the request, its
    SPLITs."""
    return {"asset_id": asset_id, "item_index": item_index, "splits": splits}


def _assert_splits(splits: object, expected: list[dict], story: str, where: str) -> None:
    """``splits`` is exactly ``expected``: the same SPLITs in the same order, each entry exactly the expected one."""
    entries = splits if isinstance(splits, list) else []
    order = [entry.get("event_id") if isinstance(entry, dict) else entry for entry in entries]
    wanted = [entry["event_id"] for entry in expected]
    assert isinstance(splits, list) and order == wanted, f"{story}: {where} list the SPLITs {order} ({splits!r}): expected {wanted}, each SPLIT with costless incoming adjustments once, ordered by (event date, event id)"
    for found, entry in zip(entries, expected, strict=True):
        assert found == entry, f"{story}: {where} give the SPLIT {entry['event_id']} as {found}: expected exactly {entry}: the event's date, the adjustments the caller can see on their brokers (sorted), the others counted, no other key (which could carry a hidden id)"


def _assert_details(details: object, expected: dict, story: str, where: str) -> None:
    """``details`` (the refusal's, or the 409's ``params``) is exactly ``expected``: the refused item's asset and position
    in the request, and its SPLITs as ``_assert_splits`` reads them; no other key, which could carry a hidden id."""
    found = details if isinstance(details, dict) else {}
    assert sorted(found) == sorted(expected), f"{story}: {where} hold the keys {sorted(found)}: expected exactly {sorted(expected)}, another key could carry a hidden id: {details!r}"
    item, wanted = (found["asset_id"], found["item_index"]), (expected["asset_id"], expected["item_index"])
    assert item == wanted, f"{story}: {where} name the item {item} as (asset_id, item_index): expected {wanted}, the refused item's asset and its position in the request"
    _assert_splits(found["splits"], expected["splits"], story, where)


def _assert_refused(refusal: AssetSourceError, expected: dict, story: str) -> None:
    """The refusal is ``PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST`` and its details are exactly ``expected``."""
    assert refusal.error_code == CODE, f"{story} was refused with {refusal.error_code} ({refusal.message}), not {CODE}: {refusal.details}"
    _assert_details(refusal.details, expected, story, "the refusal's details")


# A whole number in a text: not part of a word, a date, a decimal or a signed figure ("P-10", "1986-03-13", "X-R49" hold
# none).
_WHOLE_NUMBER = re.compile(r"(?<![\w.+-])\d+(?![\w.+-])")


def _assert_totals_only(message: object, story: str, *, splits: int, adjustments: int, ids: Collection[int], item: tuple[int, int]) -> None:
    """The refusal's message gives the totals (how many SPLITs, how many adjustments, as whole numbers) and names no event
    or transaction id of the case: whoever reads it, it carries nothing the details filter. An id that reads as a total,
    as the refused item's asset or as its position (``item``) cannot be told from them, so it is not looked for."""
    assert isinstance(message, str) and message.strip(), f"{story}: the refusal's message is {message!r}: expected a text"
    numbers = {int(number) for number in _WHOLE_NUMBER.findall(message)}
    named = sorted((set(ids) & numbers) - {splits, adjustments, *item})
    assert not named, f"{story}: the message {message!r} names the id(s) {named}: expected the totals only, never an id (X-R49); a hidden adjustment's id would reach a user who cannot see its broker"
    missing = sorted({splits, adjustments} - numbers)
    assert not missing, f"{story}: the message {message!r} lacks the total(s) {missing}: expected how many SPLITs ({splits}) and how many adjustments ({adjustments}) (X-R49: the totals only)"


async def _assert_nothing_written(owned: _Owned, before: _State, seen_by_its_session: _State, story: str) -> None:
    """All or nothing, refused before any write: the refused call's own session reads ``before``, no write of any item
    pending there, the items before the refused one included; and nothing committed: once that session is closed, a
    fresh connection reads ``before`` too. Every column of every price, event, transaction and assignment of the unit's,
    ``updated_at`` included."""
    assert seen_by_its_session == before, f"{story} was refused after writing: its own session reads {_changes(before, seen_by_its_session)} (X-R49: all or nothing, nothing of the request written, not even pending in its session: a caller committing after the refusal would store it)"
    after = await _committed(owned)
    assert after == before, f"{story} was refused, yet the database changed: {_changes(before, after)}"


def _assert_answered(answers: list[tuple[object, object]], items: list[FAProviderAssignmentItem], story: str) -> None:
    """Every item answered a success, in the request's order, as today."""
    expected = [(item.asset_id, True) for item in items]
    assert answers == expected, f"{story} answered {answers} as (asset, success): expected {expected}, every item a success, as today"


def _assert_wiped(before: _State, after: _State, story: str, *, asset_id: int, assignment_id: int, disconnected: Collection[int]) -> None:
    """What today's wipe does, and still does when the save goes through: no price of ``asset_id`` left and none of the
    events of ``assignment_id``, every other price and event as it was, every column (a manual event of the asset
    included); every transaction on the unit's brokers kept, the ``disconnected`` ones with their link NULL and every
    other column as before (``updated_at`` aside), the others untouched, every column."""
    prices = {row_id: row for row_id, row in before.prices.items() if row["asset_id"] != asset_id}
    events = {row_id: row for row_id, row in before.events.items() if row["provider_assignment_id"] != assignment_id}
    gone = (sorted(set(before.prices) - set(prices)), sorted(set(before.events) - set(events)))
    assert (after.prices, after.events) == (prices, events), f"{story}: the prices and events moved as {_changes(before, after)}: expected the prices {gone[0]} of the asset {asset_id} and the events {gone[1]} of its assignment {assignment_id} gone, every other one as it was, as today"
    expected = {tx_id: (_unlinked(row) if tx_id in disconnected else row) for tx_id, row in before.transactions.items()}
    found = {tx_id: (_undated(row) if tx_id in disconnected else row) for tx_id, row in after.transactions.items()}
    assert found == expected, f"{story}: the transactions on the unit's brokers moved as {_changes(before, after)}: expected {sorted(disconnected)} kept and disconnected, every other transaction untouched, as today"


def _assert_market_data_untouched(before: _State, after: _State, story: str) -> None:
    """No wipe: every price, event and transaction of the unit's as it was, every column."""
    moved = [name for name in ("prices", "events", "transactions") if getattr(after, name) != getattr(before, name)]
    assert not moved, f"{story} moved the {moved}: {_changes(before, after)}: expected no wipe, every price, event and transaction as it was, as today"


def _assert_assignments(before: _State, after: _State, story: str, item: FAProviderAssignmentItem) -> None:
    """The assignments after a save of ``item`` that goes through: the item's asset's holds the item's code, identifier,
    input type and params (``_saved``), every other column as before (``updated_at`` aside: today's save rewrites the
    row), or, new, a NULL ``last_fetch_at``; every other assignment of the unit's untouched, every column."""
    old_rows = {row["asset_id"]: row for row in before.assignments.values()}
    new_rows = {row["asset_id"]: row for row in after.assignments.values()}
    others = {asset_id: row for asset_id, row in new_rows.items() if asset_id != item.asset_id}
    assert others == {asset_id: row for asset_id, row in old_rows.items() if asset_id != item.asset_id}, f"{story}: the other assignments moved as {_changes(before, after)}: expected them untouched"
    old, new = old_rows.get(item.asset_id), new_rows.get(item.asset_id)
    expected = {**_saved(item), "last_fetch_at": None} if old is None else {**_undated(old), **_saved(item)}
    found = None if new is None else {key: new[key] for key in expected}
    assert found == expected, f"{story}: the assignment of the asset {item.asset_id} reads {found}: expected {expected}, the item's code, identifier, input type and params, every other column as before, as today"


# --------------------------------------------------------------------------- #
# The cases
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _PlanSplit:
    """The plan's SPLIT and the incoming adjustment linked to it, beside the plan's coupon, its transaction and a price."""

    split_id: int
    adjustment_id: int
    coupon: _Coupon

    @property
    def ids(self) -> list[int]:
        """Every event and transaction id of the case: what the refusal's message never names."""
        return [self.split_id, self.adjustment_id, self.coupon.event_id, self.coupon.tx_id]


async def _plan_split(owned: _Owned, *, cost: str | None = None) -> _PlanSplit:
    """On the plan's asset: the plan's coupon, its transaction and a price (``_coupon``); the plan's SPLIT of 2 (day
    ``SPLIT_DAY``), an event of the plan's assignment as its refresh stores it, with an ADJUSTMENT +10 linked on broker A,
    booked the next day, costless or with ``cost`` EUR a unit. Barriers: P-10's layer lists the adjustment alone when it
    is costless, nothing otherwise; user A holds broker A."""
    coupon = await _coupon(owned, owned.plan_asset_id, owned.plan_assignment_id)
    split_id = await _event(owned.plan_asset_id, SPLIT_DAY, AssetEventType.SPLIT, "2", assignment_id=owned.plan_assignment_id, notes="2-for-1")
    adjustment_id = await _adjustment(owned.plan_asset_id, owned.broker_a_id, split_id, SPLIT_DAY + 1, cost=cost)
    kind = "without a cost" if cost is None else f"costing {cost} EUR a unit"
    await _barrier_costless([split_id, coupon.event_id], {split_id: [adjustment_id]} if cost is None else {}, f"the plan's SPLIT with an incoming adjustment {kind}, beside the plan's coupon")
    await _barrier_who_sees_what(owned)
    return _PlanSplit(split_id=split_id, adjustment_id=adjustment_id, coupon=coupon)


@dataclass(frozen=True)
class _SplitOnTwoBrokers:
    """The plan's SPLIT with a costless adjustment on each of the unit's brokers."""

    split_id: int
    on_a: int  # on broker A: user A sees it, user B does not
    on_b: int  # on broker B: user B sees it, user A does not

    @property
    def ids(self) -> list[int]:
        """Every event and transaction id of the case: what the refusal's message never names."""
        return [self.split_id, self.on_a, self.on_b]


async def _plan_split_on_two_brokers(owned: _Owned) -> _SplitOnTwoBrokers:
    """On the plan's asset: the plan's SPLIT of 2 (day ``SPLIT_DAY``), an event of the plan's assignment, with a costless
    ADJUSTMENT +10 linked on broker B, then one on broker A, both booked the next day. Broker B's is written first, so the
    one user A cannot see has the lower id and a positional filter would show it. Barriers: P-10's layer lists both, user
    A holds broker A alone, user B broker B alone."""
    split_id = await _event(owned.plan_asset_id, SPLIT_DAY, AssetEventType.SPLIT, "2", assignment_id=owned.plan_assignment_id, notes="2-for-1")
    on_b = await _adjustment(owned.plan_asset_id, owned.broker_b_id, split_id, SPLIT_DAY + 1)
    on_a = await _adjustment(owned.plan_asset_id, owned.broker_a_id, split_id, SPLIT_DAY + 1)
    await _barrier_costless([split_id], {split_id: sorted([on_b, on_a])}, "the plan's SPLIT with a costless adjustment on each broker")
    await _barrier_who_sees_what(owned)
    return _SplitOnTwoBrokers(split_id=split_id, on_a=on_a, on_b=on_b)


# ─────────────────────────────────────────────────────────────────────────────
# Reds: a save that wipes refuses while a SPLIT of the item's assignment has costless incoming adjustments
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_rate_change_of_the_plan_is_refused_while_its_split_has_a_costless_adjustment(owned):
    """Red today (X-R49): the save takes no ``current_user_id`` (TypeError). Called without one, as the route calls it, the
    rate change goes through: it deletes the plan's SPLIT of 2 and its coupon with the asset's price, and disconnects the
    costless ADJUSTMENT +10 and the coupon's transaction; the adjustment is now an acquisition of unknown cost
    (MISSING_COST_BASIS on the Dashboard and in the lots).

    Contract: as user A, who holds an access to the adjustment's broker, changing the plan's rate (4 % to 5 %) is refused
    with PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST, its details exactly ``{"asset_id": the plan's asset, "item_index":
    0, "splits": [{event_id, date (day 10), transaction_ids [the adjustment], hidden_transactions_count 0}]}``, its message
    the totals only (1 SPLIT, 1 adjustment); nothing written: the price, both events, both links and the plan's params as
    they were, in the refused call's own session too, and nothing committed (every column, ``updated_at`` included).
    """
    case = await _plan_split(owned)
    item = _plan_item(owned.plan_asset_id, NEW_RATE)
    await _barrier_change(item, same=False, story="the plan's rate change")
    before = await _committed(owned)
    story = f"user A changing the rate of the plan of the asset {owned.plan_asset_id} ({OLD_RATE} to {NEW_RATE}), whose SPLIT {case.split_id} of {_day(SPLIT_DAY)} the costless adjustment {case.adjustment_id} (broker A, theirs) links to, beside the plan's coupon {case.coupon.event_id} linked to the transaction {case.coupon.tx_id} and a price"

    refusal, seen_by_its_session = await _refused_assign(owned, [item], before, story, current_user_id=owned.user_a_id)

    _assert_refused(refusal, _details(owned.plan_asset_id, 0, [_entry(case.split_id, SPLIT_DAY, [case.adjustment_id], 0)]), story)
    _assert_totals_only(refusal.message, story, splits=1, adjustments=1, ids=case.ids, item=(owned.plan_asset_id, 0))
    await _assert_nothing_written(owned, before, seen_by_its_session, story)


@pytest.mark.asyncio
async def test_leaving_the_plan_for_another_provider_is_refused_the_same_way(owned):
    """Red today (X-R49): the save takes no ``current_user_id`` (TypeError). Called without one, as the route calls it,
    leaving the plan for yfinance wipes as a change of the plan does: it deletes the plan's SPLIT of 2 and its coupon with
    the asset's price, disconnects the costless ADJUSTMENT +10 and the coupon's transaction, and assigns yfinance; the
    adjustment is now an acquisition of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots).

    Contract: leaving a parametric provider deletes the events of its assignment as a change of its params does, so it is
    refused the same way. As user A, the plan's asset assigned yfinance under a ticker: refused with
    PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST, its details exactly ``{"asset_id": the plan's asset, "item_index": 0,
    "splits": [{event_id, date (day 10), transaction_ids [the adjustment], hidden_transactions_count 0}]}``, its message
    the totals only (1 SPLIT, 1 adjustment); nothing written: the assignment still the plan, code and params, the price,
    both events and both links as they were.
    """
    case = await _plan_split(owned)
    item = _online_item(owned.plan_asset_id, f"{owned.ticker}.P", None)
    await _barrier_change(item, same=False, story="leaving the plan for yfinance")
    before = await _committed(owned)
    story = f"user A assigning yfinance ({item.identifier}) to the asset {owned.plan_asset_id}, leaving its plan, whose SPLIT {case.split_id} of {_day(SPLIT_DAY)} the costless adjustment {case.adjustment_id} (broker A, theirs) links to, beside the plan's coupon {case.coupon.event_id} and a price"

    refusal, seen_by_its_session = await _refused_assign(owned, [item], before, story, current_user_id=owned.user_a_id)

    _assert_refused(refusal, _details(owned.plan_asset_id, 0, [_entry(case.split_id, SPLIT_DAY, [case.adjustment_id], 0)]), story)
    _assert_totals_only(refusal.message, story, splits=1, adjustments=1, ids=case.ids, item=(owned.plan_asset_id, 0))
    await _assert_nothing_written(owned, before, seen_by_its_session, story)


@pytest.mark.asyncio
async def test_a_refused_item_refuses_the_whole_request_the_items_before_it_included(owned):
    """Red today (X-R49): the save takes no ``current_user_id`` (TypeError). Called without one, as the route calls it,
    both items go through: the sibling plan's price and coupon wiped, its coupon's transaction disconnected and its rate
    changed; then the plan's SPLIT deleted and the costless ADJUSTMENT +10 disconnected, now an acquisition of unknown
    cost.

    Contract: all or nothing. A request of two items, as user A: first a valid change of the sibling plan's rate (its asset
    holds a price and its coupon, linked to an INTEREST transaction, and no SPLIT), then the plan's rate change, whose
    SPLIT the costless adjustment links to: refused, its details naming the plan's asset and ``item_index`` 1, the SPLIT
    with the adjustment and 0 hidden; its message the totals only (1 SPLIT, 1 adjustment). Nothing of the request
    written, the first item included: the sibling's price, coupon, transaction link and params as they were, in the
    refused call's own session too (a caller committing after the refusal would otherwise store them), nothing committed.
    """
    sibling = await _coupon(owned, owned.sibling_asset_id, owned.sibling_assignment_id)
    await _barrier_costless([sibling.event_id], {}, "the sibling plan's coupon, its asset without a SPLIT")
    case = await _plan_split(owned)
    first, second = _plan_item(owned.sibling_asset_id, NEW_RATE, split=False), _plan_item(owned.plan_asset_id, NEW_RATE)
    await _barrier_change(first, same=False, story="the sibling plan's rate change")
    await _barrier_change(second, same=False, story="the plan's rate change")
    before = await _committed(owned)
    story = f"user A sending, first, the sibling plan's rate change (the asset {owned.sibling_asset_id}: the price {sibling.price_id}, the coupon {sibling.event_id} linked to the transaction {sibling.tx_id}, no SPLIT), then the plan's (the asset {owned.plan_asset_id}), whose SPLIT {case.split_id} the costless adjustment {case.adjustment_id} (broker A) links to"

    refusal, seen_by_its_session = await _refused_assign(owned, [first, second], before, story, current_user_id=owned.user_a_id)

    _assert_refused(refusal, _details(owned.plan_asset_id, 1, [_entry(case.split_id, SPLIT_DAY, [case.adjustment_id], 0)]), story)
    _assert_totals_only(refusal.message, story, splits=1, adjustments=1, ids=[*case.ids, sibling.event_id, sibling.tx_id], item=(owned.plan_asset_id, 1))
    await _assert_nothing_written(owned, before, seen_by_its_session, story)


@pytest.mark.asyncio
async def test_the_refusal_shows_each_caller_only_the_adjustments_on_their_brokers(owned):
    """Red today (X-R49): the save takes no ``current_user_id`` (TypeError). Called without one, as the route calls it, it
    disconnects both adjustments whoever asks: user A, who cannot see broker B, turns user B's adjustment into an
    acquisition of unknown cost.

    Contract (R13-SEC7's rule, as P-10 and X-R48): the plan's SPLIT of 2 (day 10) with a costless ADJUSTMENT +10 on broker
    B, written first so that a positional filter would show it, and one on broker A; a rate change. As user A the
    refusal's one entry shows [broker A's] and counts 1 hidden; as user B, [broker B's] and 1 hidden; without a caller
    (fail closed, as X-R47b), none named and 2 hidden. The message is the same for the three: the totals only (1 SPLIT, 2
    adjustments). None of the three writes anything.
    """
    case = await _plan_split_on_two_brokers(owned)
    item = _plan_item(owned.plan_asset_id, NEW_RATE)
    await _barrier_change(item, same=False, story="the plan's rate change")
    before = await _committed(owned)
    story = f"changing the rate of the plan of the asset {owned.plan_asset_id}, whose SPLIT {case.split_id} of {_day(SPLIT_DAY)} the costless adjustments {case.on_b} (broker B, written first) and {case.on_a} (broker A) link to"

    as_a, seen_a = await _refused_assign(owned, [item], before, f"user A {story}", current_user_id=owned.user_a_id)
    _assert_refused(as_a, _details(owned.plan_asset_id, 0, [_entry(case.split_id, SPLIT_DAY, [case.on_a], 1)]), f"user A {story}")
    await _assert_nothing_written(owned, before, seen_a, f"user A {story}")
    as_b, seen_b = await _refused_assign(owned, [item], before, f"user B {story}", current_user_id=owned.user_b_id)
    _assert_refused(as_b, _details(owned.plan_asset_id, 0, [_entry(case.split_id, SPLIT_DAY, [case.on_b], 1)]), f"user B {story}")
    await _assert_nothing_written(owned, before, seen_b, f"user B {story}")
    unknown, seen_unknown = await _refused_assign(owned, [item], before, f"a call without a caller {story}")
    _assert_refused(unknown, _details(owned.plan_asset_id, 0, [_entry(case.split_id, SPLIT_DAY, [], 2)]), f"a call without a caller {story}")
    await _assert_nothing_written(owned, before, seen_unknown, f"a call without a caller {story}")

    messages = {"user A": as_a.message, "user B": as_b.message, "no caller": unknown.message}
    assert len(set(messages.values())) == 1, f"{story}: the message depends on who asks: {messages} (X-R49: the totals only, whoever asks)"
    _assert_totals_only(as_a.message, story, splits=1, adjustments=2, ids=case.ids, item=(owned.plan_asset_id, 0))


@pytest.mark.asyncio
async def test_the_assignment_endpoint_answers_409_with_the_callers_view_and_writes_nothing(owned):
    """Red today (X-R49): 200, the save done. As user A: the plan's price, SPLIT and coupon deleted, both costless
    adjustments disconnected, user B's too, on a broker user A cannot see: each now an acquisition of unknown cost.

    Contract: ``POST /assets/provider`` as user A (in process), one item changing the plan's rate, the plan's SPLIT of 2
    (day 10) linked to a costless ADJUSTMENT +10 on broker B, then one on broker A, beside the plan's coupon, its
    transaction and a price: 409, ``detail`` exactly {``error_code`` PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST,
    ``message`` (the totals only: 1 SPLIT, 2 adjustments), ``params`` {"asset_id": the plan's asset, "item_index": 0,
    "splits": [{event_id, date, transaction_ids [broker A's], hidden_transactions_count 1}]}}, user A's view; nothing
    written.
    """
    case = await _plan_split_on_two_brokers(owned)
    coupon = await _coupon(owned, owned.plan_asset_id, owned.plan_assignment_id)
    item = _plan_item(owned.plan_asset_id, NEW_RATE)
    await _barrier_change(item, same=False, story="the plan's rate change")
    before = await _committed(owned)
    story = f"POST /assets/provider as user A, changing the rate of the plan of the asset {owned.plan_asset_id}, its SPLIT {case.split_id} of {_day(SPLIT_DAY)} linked to the costless adjustments {case.on_b} (broker B, user B's) and {case.on_a} (broker A, theirs), beside its coupon {coupon.event_id} and a price"

    response = await _route(owned.user_a_id, [item])

    if response.status_code == 200:
        pytest.fail(
            f"{story} answered 200 {response.text} and wiped: {_changes(before, await _committed(owned))}. User B's adjustment {case.on_b}, on a broker user A cannot see, and user A's {case.on_a} are now acquisitions of unknown cost (MISSING_COST_BASIS on the Dashboard and in the lots); expected 409 {CODE}"
        )
    detail = _detail(response)
    assert (response.status_code, detail.get("error_code")) == (409, CODE), f"{story} answers {response.status_code} {response.text}: expected 409 {CODE}"
    assert sorted(detail) == ["error_code", "message", "params"], f"{story}: the 409's detail holds the keys {sorted(detail)}: expected exactly error_code, message and params: {detail}"
    _assert_totals_only(detail["message"], story, splits=1, adjustments=2, ids=[*case.ids, coupon.event_id, coupon.tx_id], item=(owned.plan_asset_id, 0))
    _assert_details(detail["params"], _details(owned.plan_asset_id, 0, [_entry(case.split_id, SPLIT_DAY, [case.on_a], 1)]), story, "the 409's params")
    after = await _committed(owned)
    assert after == before, f"{story} was refused, yet the database changed: {_changes(before, after)}"


# ─────────────────────────────────────────────────────────────────────────────
# Guards: green before and after the cure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("cost", [pytest.param("12.5", id="cost-12.5"), pytest.param("0", id="cost-0")])
async def test_guard_the_plans_split_whose_incoming_adjustment_has_a_cost_is_wiped_as_today(owned, cost):
    """Guard: green today and after. The plan's SPLIT of 2 (day 10) with an ADJUSTMENT +10 linked that has a cost,
    ``cost`` EUR a unit (0 is a cost, not a missing one), beside the plan's coupon, its transaction and a price: P-10's
    layer lists nothing, so the rate change goes through as today: a success; the price, the SPLIT and the coupon gone,
    the adjustment and the coupon's transaction kept and disconnected; the plan's params the new ones."""
    case = await _plan_split(owned, cost=cost)
    item = _plan_item(owned.plan_asset_id, NEW_RATE)
    await _barrier_change(item, same=False, story="the plan's rate change")
    before = await _committed(owned)
    story = f"the rate change of the plan of the asset {owned.plan_asset_id}, whose SPLIT {case.split_id} the adjustment {case.adjustment_id} (+10, {cost} EUR a unit) links to"

    answers = await _save(owned, [item], story)

    _assert_answered(answers, [item], story)
    after = await _committed(owned)
    _assert_wiped(before, after, story, asset_id=owned.plan_asset_id, assignment_id=owned.plan_assignment_id, disconnected={case.adjustment_id, case.coupon.tx_id})
    _assert_assignments(before, after, story, item)


@pytest.mark.asyncio
async def test_guard_a_manual_split_survives_the_rate_change_with_its_link(owned):
    """Guard: green today and after. On the plan's asset a manual SPLIT of 2 (day 40, no assignment: the user's own) with
    a costless ADJUSTMENT +10 linked on broker A, beside the plan's coupon (an event of its assignment), its transaction
    and a price. The rate change goes through as today: the wipe deletes the events of the plan's assignment alone, so the
    manual SPLIT stays, every column, and its adjustment stays linked; the price and the coupon gone, the coupon's
    transaction disconnected; the plan's params the new ones. The guard reads the SPLITs among the events of the item's
    assignment, not every event of the asset."""
    coupon = await _coupon(owned, owned.plan_asset_id, owned.plan_assignment_id)
    split_id = await _event(owned.plan_asset_id, MANUAL_SPLIT_DAY, AssetEventType.SPLIT, "2", notes="2-for-1")
    adjustment_id = await _adjustment(owned.plan_asset_id, owned.broker_a_id, split_id, MANUAL_SPLIT_DAY + 1)
    await _barrier_costless([split_id, coupon.event_id], {split_id: [adjustment_id]}, "a manual SPLIT with a costless adjustment, beside the plan's coupon")
    item = _plan_item(owned.plan_asset_id, NEW_RATE)
    await _barrier_change(item, same=False, story="the plan's rate change")
    before = await _committed(owned)
    story = f"the rate change of the plan of the asset {owned.plan_asset_id}, whose manual SPLIT {split_id} (no assignment) the costless adjustment {adjustment_id} links to, beside the plan's coupon {coupon.event_id} linked to the transaction {coupon.tx_id}"

    answers = await _save(owned, [item], story)

    _assert_answered(answers, [item], story)
    after = await _committed(owned)
    _assert_wiped(before, after, story, asset_id=owned.plan_asset_id, assignment_id=owned.plan_assignment_id, disconnected={coupon.tx_id})
    _assert_assignments(before, after, story, item)


@pytest.mark.asyncio
async def test_guard_the_plan_saved_with_the_same_params_wipes_nothing(owned):
    """Guard: green today and after. The plan's SPLIT of 2 (day 10) with a costless ADJUSTMENT +10 on broker A, beside the
    plan's coupon, its transaction and a price; the plan saved again with the very params it holds: no change, no wipe, a
    success; every price, event and transaction as it was, every column; the assignment's columns too (``updated_at``
    aside: today's save rewrites the row)."""
    case = await _plan_split(owned)
    item = _plan_item(owned.plan_asset_id, OLD_RATE)
    await _barrier_change(item, same=True, story="the plan saved with the params it holds")
    before = await _committed(owned)
    story = f"saving the plan of the asset {owned.plan_asset_id} with the params it holds, its SPLIT {case.split_id} linked to the costless adjustment {case.adjustment_id}"

    answers = await _save(owned, [item], story)

    _assert_answered(answers, [item], story)
    after = await _committed(owned)
    _assert_market_data_untouched(before, after, story)
    _assert_assignments(before, after, story, item)


@pytest.mark.asyncio
async def test_guard_an_online_providers_params_change_wipes_nothing(owned):
    """Guard: green today and after. The online asset, assigned to yfinance (an online provider: its history came from
    outside its params), holds a SPLIT of 2 (day 10) of its assignment with a costless ADJUSTMENT +10 on broker A, and a
    price; its params change: no wipe, a success; every price, event and transaction as it was, every column; the
    assignment's params the new ones. Only a parametric provider's change wipes, so only such a change can be refused."""
    split_id = await _event(owned.online_asset_id, SPLIT_DAY, AssetEventType.SPLIT, "2", assignment_id=owned.online_assignment_id, notes="2-for-1")
    adjustment_id = await _adjustment(owned.online_asset_id, owned.broker_a_id, split_id, SPLIT_DAY + 1)
    await _price(owned.online_asset_id, SPLIT_DAY - 1, "100")
    await _barrier_costless([split_id], {split_id: [adjustment_id]}, "the online assignment's SPLIT with a costless adjustment")
    item = _online_item(owned.online_asset_id, owned.ticker, ONLINE_PARAMS_CHANGED)
    await _barrier_change(item, same=False, story="the online assignment's params change")
    before = await _committed(owned)
    story = f"the params change of the yfinance assignment of the asset {owned.online_asset_id}, whose SPLIT {split_id} (an event of that assignment) the costless adjustment {adjustment_id} links to"

    answers = await _save(owned, [item], story)

    _assert_answered(answers, [item], story)
    after = await _committed(owned)
    _assert_market_data_untouched(before, after, story)
    _assert_assignments(before, after, story, item)


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["service", "route"])
async def test_guard_a_new_assignment_is_saved_as_today(owned, via):
    """Guard: green today and after. The fresh asset has no assignment, and a manual SPLIT of 2 (day 40) with a costless
    ADJUSTMENT +10 on broker A, and a price; assigning it the plan, through the service without a caller as the route calls
    it today, or ``POST /assets/provider`` as user A (in process): a success; the assignment written (the plan's code, a
    NULL identifier, AUTO_GENERATED, the plan's params, never fetched), every price, event and transaction as it was,
    every column. A new assignment has no events of its own: nothing to wipe, nothing to refuse; through the route, the
    answer the cure must keep."""
    split_id = await _event(owned.fresh_asset_id, MANUAL_SPLIT_DAY, AssetEventType.SPLIT, "2", notes="2-for-1")
    adjustment_id = await _adjustment(owned.fresh_asset_id, owned.broker_a_id, split_id, MANUAL_SPLIT_DAY + 1)
    await _price(owned.fresh_asset_id, MANUAL_SPLIT_DAY - 1, "1000")
    await _barrier_costless([split_id], {split_id: [adjustment_id]}, "the fresh asset's manual SPLIT with a costless adjustment")
    item = _plan_item(owned.fresh_asset_id, NEW_RATE)
    await _barrier_change(item, same=False, story="the fresh asset's first assignment")
    before = await _committed(owned)
    story = f"assigning the plan to the asset {owned.fresh_asset_id} (via the {via}), which had no assignment, its manual SPLIT {split_id} linked to the costless adjustment {adjustment_id}"

    answers = await _save(owned, [item], story, via=via)

    _assert_answered(answers, [item], story)
    after = await _committed(owned)
    _assert_market_data_untouched(before, after, story)
    _assert_assignments(before, after, story, item)
