"""X-R69 / C-65a (lot X5-1): the dry run of a provider change or removal -- ``POST /api/v1/assets/provider/impact``.

The developer's decision of 22-23/10: «togli» (remove the provider) and «cambia» (change the provider, or a parametric
provider's params) follow ONE rule. A dry run tells what would be lost; once confirmed, both UNLINK the transactions linked
to the events that disappear, and only a SPLIT among them with linked incoming ADJUSTMENTs without a purchase cost
(``split_guard.splits_with_costless_adjustments``, X-R49) refuses. This file pins the dry run; ``test_provider_removal_link_guard.py``
pins the removal, ``test_provider_wipe_split_guard.py`` the change.

The contract:

* ``ProviderManagementOperations.provider_change_impact(request, session, *, current_user_id=None) ->
  FAProviderImpactResponse`` (also on ``AssetSourceManager``, like its siblings). It WRITES NOTHING.
  ``FAProviderImpactRequest`` = ``{"assignments": [FAProviderAssignmentItem…] (default []), "removals": [asset_id…] (default
  [])}``, a ``StrictModel``. ``FAProviderImpactResponse`` = ``{"results": [FAProviderImpactResult…]}``, one per assignment
  then one per removal, in order. ``FAProviderImpactResult`` = ``{"asset_id", "action": "assign"|"remove", "reason":
  "none"|"params_changed"|"provider_changed"|"provider_removed", "prices_deleted", "events_deleted",
  "transactions_unlinked", "blocking_splits": [{"event_id", "date", "transaction_ids", "hidden_transactions_count"}…]}``.
* An assignment item: ``reason`` is ``params_changed`` / ``provider_changed`` exactly when the save would wipe (``_wipe_reason``
  of the stored code and params and the item's: a parametric provider with other params, or leaving one), else ``none``.
  When not ``none``: ``prices_deleted`` = ALL the asset's prices, ``events_deleted`` = the events of the stored assignment
  (manual events excluded), ``transactions_unlinked`` = the transactions linked to those events, visible to the caller or not
  (counted in total, never named), ``blocking_splits`` = ``splits_with_costless_adjustments`` over those events. An asset with
  no assignment, a market -> market change or the same code and params: ``none``, zeros, ``[]``.
* A removal: ``provider_removed`` when the asset has an assignment (else ``none``, zeros); ``prices_deleted`` 0 (a removal keeps
  the prices); the events, the transactions and the blocking SPLITs as above.
* PARITY: the numbers are those of the operation that follows -- the prices the save really deletes, the events that really
  go, the transactions whose ``asset_event_id`` really becomes NULL -- and a non-empty ``blocking_splits`` is the refusal the
  operation really answers.
* The route answers 200 with the response, 401 without a user, 422 for a body that is not the request (an unknown key
  included).

Names of the lot are read where a test needs them (``getattr``, the schemas through ``importlib``): until they exist the
test fails naming X-R69, and the file collects.

Isolation: WRITE-SCOPED, the services default. Every row is this unit's own, under a unique marker, dated 1983: three EUR
assets, inactive so that no scheduler of the lane refreshes them (the market asset, the plan's, the bare one), two users and
two brokers, user A holding an access to broker A alone, user B to broker B alone. Each test finds the market asset assigned
yfinance under a ticker of the unit's own, the plan's asset scheduled_investment with a plan of 1983, the bare asset without
an assignment, and no price, event or transaction. Only the rows of those assets and brokers are written, read and wiped, by
asset and broker id; nothing is fetched; nothing here counts a row it did not write.
"""

import asyncio
import importlib
import json
import sys
import uuid
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
from sqlalchemy import bindparam, delete, or_, select, text
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

#: The providers: a market one, a second market one (a market -> market change), and the parametric plan.
MARKET = "yfinance"
OTHER_MARKET = "justetf"
PLAN = "scheduled_investment"
#: The code of the one refusal left (X-R49).
CODE = "PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST"
#: The route under test, as the app mounts it.
IMPACT_PATH = "/api/v1/assets/provider/impact"
#: The unit's assets by role.
ASSET_TYPES = {"market": AssetType.STOCK, "plan": AssetType.BOND, "bare": AssetType.STOCK}
#: The keys of a result and of a blocking SPLIT, exactly: any other could carry a hidden id.
RESULT_KEYS = ["action", "asset_id", "blocking_splits", "events_deleted", "prices_deleted", "reason", "transactions_unlinked"]
SPLIT_KEYS = ["date", "event_id", "hidden_transactions_count", "transaction_ids"]
#: The stored rate of the plan and the rate a change asks for.
OLD_RATE = "0.04"
NEW_RATE = "0.05"

# A window far from the mock dataset and from the other units that write events (1984, 1986, 1988, 1990, 1991-1992,
# 1994-1995). Rows are scoped by asset and broker anyway: the dates only keep the failure output readable.
BASE_DATE = date(1983, 4, 2)
SPLIT_DAY = 20
COUPON_DAY = 28
MANUAL_DAY = 35
LATE_COUPON_DAY = 56


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


def _plan(rate: str = OLD_RATE) -> dict:
    """The plan's params (``FAScheduledInvestmentSchedule``): 1 000 EUR over 1983 at ``rate``, monthly coupons, no planned
    event. A new dict at each call."""
    period = {"start_date": "1983-01-01", "end_date": "1983-12-31", "annual_rate": rate, "maturation_frequency": "MONTHLY", "generate_interest": True}
    return {"initial_value": {"code": "EUR", "amount": "1000.00"}, "schedule": [period], "asset_events": []}


def _plan_item(asset_id: int, rate: str) -> FAProviderAssignmentItem:
    """An item assigning ``asset_id`` the plan at ``rate``, as the asset form sends it: an empty AUTO_GENERATED identifier."""
    return FAProviderAssignmentItem(asset_id=asset_id, provider_code=PLAN, identifier="", identifier_type=ProviderInputType.AUTO_GENERATED.value, provider_params=_plan(rate))


def _market_item(asset_id: int, code: str, identifier: str, params: dict | None = None) -> FAProviderAssignmentItem:
    """An item assigning ``asset_id`` the market provider ``code`` under ``identifier`` (a ticker, an ISIN), with ``params``."""
    kind = ProviderInputType.TICKER if code == MARKET else ProviderInputType.ISIN
    return FAProviderAssignmentItem(asset_id=asset_id, provider_code=code, identifier=identifier, identifier_type=kind.value, provider_params=params)


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Unit:
    """What this unit created once: three EUR assets, inactive, two users and two brokers, user A holding an access to broker
    A alone, user B to broker B alone; and the ticker the market asset is assigned under."""

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
    (scheduled_investment with the plan at ``OLD_RATE``), written for the test; the bare asset without one."""

    market_assignment_id: int
    plan_assignment_id: int

    @property
    def role_ids(self) -> dict[str, int]:
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
    """The market asset assigned yfinance under the unit's ticker, the plan's asset scheduled_investment with the plan at
    ``OLD_RATE``, as a save leaves them (the params as the save stores them: ``json.dumps`` of the dict), never fetched."""
    market = AssetProviderAssignment(asset_id=unit.market_asset_id, provider_code=MARKET, identifier=unit.ticker, identifier_type=ProviderInputType.TICKER, provider_params=None, last_fetch_at=None)
    plan = AssetProviderAssignment(asset_id=unit.plan_asset_id, provider_code=PLAN, identifier=None, identifier_type=ProviderInputType.AUTO_GENERATED, provider_params=json.dumps(_plan()), last_fetch_at=None)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add_all([market, plan])
        await session.commit()
    return _Owned(**asdict(unit), market_assignment_id=market.id, plan_assignment_id=plan.id)


@pytest.fixture(scope="module")
def unit() -> _Unit:
    """The assets, the users, the brokers and the accesses, under names no concurrent worker can repeat, dropped in FK-safe
    order in teardown with every assignment, price, event and transaction written against them."""
    marker = f"{unique_id('X51IMP')}_{uuid.uuid4().hex[:8]}"
    ticker = f"X51IMP.{uuid.uuid4().hex[:10].upper()}"

    async def _create() -> _Unit:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            assets = {role: Asset(display_name=f"X5-1 impact {role} {marker}", currency="EUR", asset_type=asset_type, active=False) for role, asset_type in ASSET_TYPES.items()}
            user_a = User(username=f"x51a_{marker}".lower(), email=f"x51a_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            user_b = User(username=f"x51b_{marker}".lower(), email=f"x51b_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            broker_a = Broker(name=f"X5-1 impact A {marker}")
            broker_b = Broker(name=f"X5-1 impact B {marker}")
            session.add_all([*assets.values(), user_a, user_b, broker_a, broker_b])
            await session.commit()
            session.add_all(
                [
                    BrokerUserAccess(user_id=user_a.id, broker_id=broker_a.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                    BrokerUserAccess(user_id=user_b.id, broker_id=broker_b.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                ]
            )
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
    """The unit with its two assignments written for the test, and no price, event or transaction of its assets or on its
    brokers, before and after the test."""
    await _clear(unit)
    yield await _assign(unit)
    await _clear(unit)


# --------------------------------------------------------------------------- #
# Seeding: rows written directly, as earlier refreshes, saves and imports left them
# --------------------------------------------------------------------------- #


async def _add(row: AssetEvent | PriceHistory | Transaction) -> int:
    """``row`` written and committed in a session of its own: its id."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add(row)
        await session.commit()
        return row.id


async def _event(asset_id: int, offset: int, kind: AssetEventType, amount: str, *, assignment_id: int | None = None, notes: str | None = None) -> int:
    """An event of ``asset_id`` on day ``offset``, in EUR, as a refresh under ``assignment_id`` stores it, or, without one, as
    a manual save left it: its id."""
    return await _add(AssetEvent(asset_id=asset_id, date=_day(offset), type=kind, value=Decimal(amount), currency="EUR", notes=notes, provider_assignment_id=assignment_id))


async def _price(asset_id: int, offset: int, close: str) -> int:
    """A closing price of ``asset_id`` on day ``offset``, in EUR: its id."""
    return await _add(PriceHistory(asset_id=asset_id, date=_day(offset), close=Decimal(close), currency="EUR", source_plugin_key="test"))


async def _income(asset_id: int, broker_id: int, kind: TransactionType, offset: int, amount: str, *, event_id: int | None = None) -> int:
    """A DIVIDEND or an INTEREST of ``amount`` EUR from ``asset_id`` on ``broker_id``, booked on day ``offset``, linked to
    ``event_id``: its id."""
    return await _add(Transaction(broker_id=broker_id, asset_id=asset_id, type=kind, date=_day(offset), quantity=Decimal("0"), amount=Decimal(amount), currency="EUR", asset_event_id=event_id))


async def _adjustment(asset_id: int, broker_id: int, event_id: int, offset: int, *, cost: str | None = None) -> int:
    """An ADJUSTMENT +10 of ``asset_id`` on ``broker_id``, booked on day ``offset`` and linked to ``event_id``: without a cost,
    as the Auto mode stores one linked to a SPLIT, or with ``cost`` EUR a unit. Its id."""
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


@dataclass(frozen=True)
class _Plan:
    """What a plan's asset holds, and what a wipe or a removal of its assignment takes: ``prices`` (all of the asset's),
    ``events`` (those of the assignment), ``transactions`` (those linked to them, on either broker). ``manual_event`` and its
    transaction, and a price of the market asset, are the rows that do NOT count. ``split_id`` is the plan's SPLIT,
    ``costless`` the adjustments linked to it without a cost (sorted), on broker B first when there are two."""

    prices: list[int]
    events: list[int]
    transactions: list[int]
    split_id: int
    costless: list[int]
    manual_event: int
    manual_tx: int
    market_price: int


async def _plan_world(owned: _Owned, *, split: str) -> _Plan:
    """On the plan's asset: three prices; a coupon (day 28) linked to an INTEREST on broker B, written first, and one on
    broker A; a coupon (day 56) linked to nothing; the plan's SPLIT of 2 (day 20) with, as ``split`` says, one ADJUSTMENT
    +10 on broker A "with-cost" (12.5 EUR a unit), or two "costless" ones (broker B first, then broker A); a manual DIVIDEND
    (day 35) linked to an INTEREST on broker A. On the market asset: one price. Barriers: who sees what; P-10's layer lists
    the costless adjustments, and only them."""
    assert split in ("with-cost", "costless")
    asset_id, assignment_id = owned.plan_asset_id, owned.plan_assignment_id
    prices = [await _price(asset_id, offset, "1000") for offset in (1, 2, 3)]
    market_price = await _price(owned.market_asset_id, 9, "10")
    coupon = await _event(asset_id, COUPON_DAY, AssetEventType.INTEREST, "3.33", assignment_id=assignment_id)
    on_b = await _income(asset_id, owned.broker_b_id, TransactionType.INTEREST, COUPON_DAY, "3.33", event_id=coupon)
    on_a = await _income(asset_id, owned.broker_a_id, TransactionType.INTEREST, COUPON_DAY, "3.33", event_id=coupon)
    late = await _event(asset_id, LATE_COUPON_DAY, AssetEventType.INTEREST, "3.33", assignment_id=assignment_id)
    split_id = await _event(asset_id, SPLIT_DAY, AssetEventType.SPLIT, "2", assignment_id=assignment_id, notes="2-for-1")
    if split == "with-cost":
        adjustments = [await _adjustment(asset_id, owned.broker_a_id, split_id, SPLIT_DAY + 1, cost="12.5")]
        costless: list[int] = []
    else:
        adjustments = [await _adjustment(asset_id, owned.broker_b_id, split_id, SPLIT_DAY + 1), await _adjustment(asset_id, owned.broker_a_id, split_id, SPLIT_DAY + 1)]
        costless = sorted(adjustments)
    manual = await _event(asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
    manual_tx = await _income(asset_id, owned.broker_a_id, TransactionType.INTEREST, MANUAL_DAY, "4.50", event_id=manual)
    await _barrier_who_sees_what(owned)
    await _barrier_costless([split_id], {split_id: costless} if costless else {}, f"the plan's SPLIT with its adjustments {split}")
    return _Plan(prices=prices, events=[coupon, late, split_id], transactions=[on_b, on_a, *adjustments], split_id=split_id, costless=costless, manual_event=manual, manual_tx=manual_tx, market_price=market_price)


@dataclass(frozen=True)
class _Market:
    """What the market asset holds: two prices, the provider's DIVIDEND linked to a transaction on broker A and its
    PRICE_ADJUSTMENT linked to nothing, a manual DIVIDEND linked to a transaction on broker A."""

    prices: list[int]
    events: list[int]
    transactions: list[int]
    manual_event: int
    manual_tx: int


async def _market_world(owned: _Owned) -> _Market:
    asset_id, assignment_id = owned.market_asset_id, owned.market_assignment_id
    prices = [await _price(asset_id, offset, "10") for offset in (1, 2)]
    dividend = await _event(asset_id, SPLIT_DAY, AssetEventType.DIVIDEND, "0.50", assignment_id=assignment_id)
    paid = await _income(asset_id, owned.broker_a_id, TransactionType.DIVIDEND, SPLIT_DAY, "5.00", event_id=dividend)
    adjusted = await _event(asset_id, 5, AssetEventType.PRICE_ADJUSTMENT, "-0.10", assignment_id=assignment_id)
    manual = await _event(asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
    manual_tx = await _income(asset_id, owned.broker_a_id, TransactionType.DIVIDEND, MANUAL_DAY, "4.50", event_id=manual)
    return _Market(prices=prices, events=[dividend, adjusted], transactions=[paid], manual_event=manual, manual_tx=manual_tx)


# --------------------------------------------------------------------------- #
# Barriers: the case is the one the test names
# --------------------------------------------------------------------------- #


async def _barrier_who_sees_what(owned: _Owned) -> None:
    """Barrier: of the unit's brokers, user A holds an access to broker A alone and user B to broker B alone, so a dry run
    naming one adjustment and counting another is about who sees what."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(select(BrokerUserAccess.user_id, BrokerUserAccess.broker_id).where(BrokerUserAccess.broker_id.in_(owned.broker_ids)))).all()
    held = sorted((user_id, broker_id) for user_id, broker_id in rows)
    expected = sorted([(owned.user_a_id, owned.broker_a_id), (owned.user_b_id, owned.broker_b_id)])
    assert held == expected, f"barrier: the accesses to the unit's brokers are {held} as (user, broker): expected {expected}, user A on broker A alone, user B on broker B alone"


async def _barrier_costless(event_ids: list[int], expected: dict[int, list[int]], story: str) -> None:
    """Barrier: among ``event_ids``, P-10's layer (``costless_incoming_split_adjustments``) lists exactly ``expected``."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        costless = await costless_incoming_split_adjustments(session, event_ids)
    assert costless == expected, f"barrier: {story}: the layer lists {costless} as the costless incoming adjustments of the SPLITs among the events {event_ids}, not {expected}"


def _barrier_kinds() -> None:
    """Barrier: scheduled_investment generates its series from its params (PARAMETRIC_GENERATION), the market providers do
    not, as the wipe's rule reads them from the registry."""
    kinds = {code: getattr(AssetProviderRegistry.get_provider_instance(code), "provider_kind", None) for code in (PLAN, MARKET, OTHER_MARKET)}
    assert kinds[PLAN] == FAProviderKind.PARAMETRIC_GENERATION, f"barrier: the providers' kinds are {kinds}: expected {PLAN} parametric"
    assert all(kinds[code] not in (None, FAProviderKind.PARAMETRIC_GENERATION) for code in (MARKET, OTHER_MARKET)), f"barrier: the providers' kinds are {kinds}: expected {MARKET} and {OTHER_MARKET} registered and not parametric"


# --------------------------------------------------------------------------- #
# Reading back: raw SQL, every column
# --------------------------------------------------------------------------- #

_RAW = {
    "prices": text("SELECT * FROM price_history WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True)),
    "events": text("SELECT * FROM asset_events WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True)),
    "transactions": text("SELECT * FROM transactions WHERE broker_id IN :broker_ids ORDER BY id").bindparams(bindparam("broker_ids", expanding=True)),
    "assignments": text("SELECT * FROM asset_provider_assignments WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True)),
}


async def _snapshot(session: AsyncSession, owned: _Owned) -> dict[str, dict[int, dict]]:
    """Every price, event and assignment of the unit's assets and every transaction on its brokers, every column, by table
    and id, through ``session`` (a session that wrote reads its own writes, committed or not)."""
    snapshot = {}
    for name, statement in _RAW.items():
        params = {"broker_ids": owned.broker_ids} if name == "transactions" else {"asset_ids": owned.asset_ids}
        snapshot[name] = {row["id"]: dict(row) for row in (await session.execute(statement, params)).mappings().all()}
    return snapshot


async def _committed(owned: _Owned) -> dict[str, dict[int, dict]]:
    """What is committed: the snapshot read on a fresh connection."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await _snapshot(session, owned)


def _moved(before: dict[str, dict[int, dict]], after: dict[str, dict[int, dict]]) -> str:
    """For a failure message: what differs between two snapshots, table by table."""
    return (
        "; ".join(f"{name}: gone {sorted(set(before[name]) - set(after[name]))}, added {sorted(set(after[name]) - set(before[name]))}, changed {sorted(i for i in before[name] if i in after[name] and before[name][i] != after[name][i])}" for name in before if before[name] != after[name]) or "nothing"
    )


# --------------------------------------------------------------------------- #
# The lot's names, read where a test needs them
# --------------------------------------------------------------------------- #


def _schema(name: str):
    """The schema ``name`` of the lot: the test that needs it fails naming X-R69 until it exists."""
    for module in ("backend.app.schemas.provider", "backend.app.schemas"):
        found = getattr(importlib.import_module(module), name, None)
        if found is not None:
            return found
    pytest.fail(f"X-R69: backend.app.schemas.provider has no {name}: the dry run of a provider change has no request or response to speak")


def _service():
    """``AssetSourceManager.provider_change_impact``: the test that needs it fails naming X-R69 until it exists."""
    found = getattr(AssetSourceManager, "provider_change_impact", None)
    if found is None:
        pytest.fail("X-R69: AssetSourceManager has no provider_change_impact: nothing tells, before it is confirmed, what a provider change or removal would delete and unlink")
    return found


def _request(assignments: list[FAProviderAssignmentItem], removals: list[int]) -> object:
    return _schema("FAProviderImpactRequest").model_validate({"assignments": [item.model_dump(mode="json") for item in assignments], "removals": removals})


# --------------------------------------------------------------------------- #
# The dry run, called as the route calls it
# --------------------------------------------------------------------------- #


async def _dry_run(owned: _Owned, assignments: list[FAProviderAssignmentItem], removals: list[int], story: str, **caller: int) -> list[dict]:
    """``provider_change_impact`` of the request, ``caller`` the ``current_user_id`` it is given if any: its ``results`` as
    JSON. It WRITES NOTHING, proved at every call: nothing pending in the call's own session, which reads the rows as they
    were (committed or not), and, once it is closed, a fresh connection reads them as they were, every column."""
    service = _service()
    request = _request(assignments, removals)
    before = await _committed(owned)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            answer = await service(request, session, **caller)
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story} raised {exc!r}")
        pending = {"new": list(session.new), "dirty": list(session.dirty), "deleted": list(session.deleted)}
        seen = await _snapshot(session, owned)
    assert not any(pending.values()), f"{story} left changes pending in its session: {pending}: a dry run writes nothing"
    assert seen == before, f"{story} wrote, its own session reads {_moved(before, seen)}: a dry run writes nothing"
    after = await _committed(owned)
    assert after == before, f"{story} changed the database: {_moved(before, after)}: a dry run writes nothing"
    body = answer.model_dump(mode="json")
    assert list(body) == ["results"], f"{story} answered the keys {sorted(body)}: expected exactly results"
    return body["results"]


def _split_entry(event_id: int, offset: int, seen: list[int], hidden: int) -> dict:
    """One blocking SPLIT as ``split_guard`` gives it: the event, its date (ISO), the costless adjustments the caller sees
    (sorted), how many it does not."""
    return {"event_id": event_id, "date": _day(offset).isoformat(), "transaction_ids": sorted(seen), "hidden_transactions_count": hidden}


def _result(asset_id: int, action: str, reason: str, prices: int, events: int, transactions: int, splits: list[dict] | None = None) -> dict:
    """One result, as the contract gives it."""
    return {"asset_id": asset_id, "action": action, "reason": reason, "prices_deleted": prices, "events_deleted": events, "transactions_unlinked": transactions, "blocking_splits": splits or []}


def _nothing(asset_id: int, action: str) -> dict:
    return _result(asset_id, action, "none", 0, 0, 0)


def _assert_results(found: list[dict], expected: list[dict], story: str) -> None:
    """``found`` is exactly ``expected``: one result per item in order, each with exactly the contract's keys, and its blocking
    SPLITs with exactly theirs (no other key, which could carry a hidden id)."""
    for result in found:
        assert sorted(result) == RESULT_KEYS, f"{story}: a result holds the keys {sorted(result)}: expected exactly {RESULT_KEYS}: {result}"
        for split in result["blocking_splits"]:
            assert sorted(split) == SPLIT_KEYS, f"{story}: a blocking SPLIT holds the keys {sorted(split)}: expected exactly {SPLIT_KEYS}: {split}"
    assert found == expected, f"{story} answered {found}: expected {expected}"


# --------------------------------------------------------------------------- #
# Reds: an assignment item
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("caller", [pytest.param({"current_user_id": "user_a_id"}, id="user-a"), pytest.param({}, id="no-caller")])
async def test_new_params_of_the_plan_would_wipe_its_series_its_events_and_unlink_their_transactions(owned, caller):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: the plan's asset holds three prices, the plan's events (two coupons, one linked to an INTEREST on broker B and
    one on broker A, and a SPLIT linked to an adjustment with a cost on broker A), a manual DIVIDEND linked to an INTEREST on
    broker A, and a price of the market asset. An item sending the plan at another rate: ``params_changed``, ``prices_deleted``
    3 (all of the asset's, the market asset's not counted), ``events_deleted`` 3 (the manual event not counted),
    ``transactions_unlinked`` 3 (broker B's included, hidden to user A, counted all the same; the manual event's not), no
    blocking SPLIT (the adjustment has a cost). The same for a caller and for none: counting is not a view.
    """
    _barrier_kinds()
    world = await _plan_world(owned, split="with-cost")
    item = _plan_item(owned.plan_asset_id, NEW_RATE)
    keyword = {key: getattr(owned, value) for key, value in caller.items()}
    story = f"the dry run of the plan's asset {owned.plan_asset_id} at rate {NEW_RATE} (stored {OLD_RATE}), {'as user A' if keyword else 'without a caller'}"

    found = await _dry_run(owned, [item], [], story, **keyword)

    _assert_results(found, [_result(owned.plan_asset_id, "assign", "params_changed", len(world.prices), len(world.events), len(world.transactions))], story)


@pytest.mark.asyncio
async def test_leaving_the_plan_for_a_market_provider_would_wipe_the_same_and_say_provider_changed(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: the same plan asset, an item assigning it yfinance: leaving a parametric provider is ``provider_changed``, the
    numbers those of a change of its params (all prices, the assignment's events, their transactions).
    """
    _barrier_kinds()
    world = await _plan_world(owned, split="with-cost")
    item = _market_item(owned.plan_asset_id, MARKET, owned.ticker)
    story = f"the dry run of the plan's asset {owned.plan_asset_id} leaving {PLAN} for {MARKET}"

    found = await _dry_run(owned, [item], [], story, current_user_id=owned.user_a_id)

    _assert_results(found, [_result(owned.plan_asset_id, "assign", "provider_changed", len(world.prices), len(world.events), len(world.transactions))], story)


@pytest.mark.asyncio
async def test_a_costless_split_is_listed_as_blocking_with_each_callers_view_and_the_totals_count_everything(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract (R13-SEC7's rule): the plan's SPLIT linked to a costless adjustment on broker B, written first, and one on
    broker A. A change of the plan's rate: ``params_changed``, ``blocking_splits`` the SPLIT (day 20) alone, as user A its
    adjustment on broker A and 1 hidden; as user B broker B's and 1 hidden; without a caller none named and 2 hidden. The
    manual events are not read. ``transactions_unlinked`` counts every linked transaction whoever asks.
    """
    world = await _plan_world(owned, split="costless")
    on_b, on_a = world.costless
    views = {
        "user A": ({"current_user_id": owned.user_a_id}, _split_entry(world.split_id, SPLIT_DAY, [on_a], 1)),
        "user B": ({"current_user_id": owned.user_b_id}, _split_entry(world.split_id, SPLIT_DAY, [on_b], 1)),
        "no caller": ({}, _split_entry(world.split_id, SPLIT_DAY, [], 2)),
    }
    item = _plan_item(owned.plan_asset_id, NEW_RATE)

    for caller, (keyword, entry) in views.items():
        story = f"the dry run, {caller}, of the plan's asset {owned.plan_asset_id} at rate {NEW_RATE}, its SPLIT {world.split_id} linked to the costless adjustments {world.costless}"
        found = await _dry_run(owned, [item], [], story, **keyword)
        _assert_results(found, [_result(owned.plan_asset_id, "assign", "params_changed", len(world.prices), len(world.events), len(world.transactions), [entry])], story)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["market-to-market", "same-code-and-params", "market-params", "no-assignment"])
async def test_a_save_that_wipes_nothing_says_none_with_zeros(owned, change):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: every row of the plan's and of the market's worlds is there (prices, events, links), and still the save of the
    item wipes nothing, so the answer is ``none``, every count 0, no blocking SPLIT: yfinance -> justetf (market -> market);
    the plan with the very params it holds; yfinance with other params (not parametric); an item for an asset that holds no
    assignment (the bare one, which has prices, a manual event and a link of its own).
    """
    _barrier_kinds()
    await _plan_world(owned, split="costless")
    await _market_world(owned)
    if change == "no-assignment":
        await _price(owned.bare_asset_id, 1, "5")
        bare_event = await _event(owned.bare_asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
        await _income(owned.bare_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, MANUAL_DAY, "4.50", event_id=bare_event)
    items = {
        "market-to-market": _market_item(owned.market_asset_id, OTHER_MARKET, "IE00B4L5Y983"),
        "same-code-and-params": _plan_item(owned.plan_asset_id, OLD_RATE),
        "market-params": _market_item(owned.market_asset_id, MARKET, owned.ticker, {"note": "X5-1 other params"}),
        "no-assignment": _plan_item(owned.bare_asset_id, NEW_RATE),
    }
    item = items[change]
    story = f"the dry run of the save {change} for the asset {item.asset_id}"

    found = await _dry_run(owned, [item], [], story, current_user_id=owned.user_a_id)

    _assert_results(found, [_nothing(item.asset_id, "assign")], story)


# --------------------------------------------------------------------------- #
# Reds: a removal
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_removing_the_plan_would_keep_its_prices_delete_its_events_and_unlink_their_transactions(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: the plan's world (three prices, three events with their transactions on both brokers, a manual event linked).
    A removal of the plan's asset: ``provider_removed``, ``prices_deleted`` 0 (a removal keeps the prices), ``events_deleted``
    3, ``transactions_unlinked`` 3, no blocking SPLIT (the adjustment has a cost).
    """
    world = await _plan_world(owned, split="with-cost")
    story = f"the dry run of the removal of the plan of the asset {owned.plan_asset_id}"

    found = await _dry_run(owned, [], [owned.plan_asset_id], story, current_user_id=owned.user_a_id)

    _assert_results(found, [_result(owned.plan_asset_id, "remove", "provider_removed", 0, len(world.events), len(world.transactions))], story)


@pytest.mark.asyncio
async def test_removing_a_market_provider_counts_its_generated_events_alone(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: the market asset holds two prices, the provider's DIVIDEND linked to a DIVIDEND on broker A, its
    PRICE_ADJUSTMENT linked to nothing, and a manual DIVIDEND linked to a DIVIDEND on broker A. Removing its provider:
    ``provider_removed``, 0 prices, 2 events (the manual one stays), 1 transaction (the manual event's stays linked).
    """
    world = await _market_world(owned)
    story = f"the dry run of the removal of the provider of the asset {owned.market_asset_id}"

    found = await _dry_run(owned, [], [owned.market_asset_id], story, current_user_id=owned.user_a_id)

    _assert_results(found, [_result(owned.market_asset_id, "remove", "provider_removed", 0, len(world.events), len(world.transactions))], story)


@pytest.mark.asyncio
async def test_removing_a_provider_that_generated_nothing_is_still_a_removal_with_zero_counts(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: the market asset holds a manual DIVIDEND linked to a transaction and no event of its assignment. The asset has an
    assignment, so removing it is ``provider_removed``, whatever it would take: 0 prices, 0 events, 0 transactions.
    """
    manual = await _event(owned.market_asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
    await _income(owned.market_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, MANUAL_DAY, "4.50", event_id=manual)
    story = f"the dry run of the removal of the provider of the asset {owned.market_asset_id}, which generated no event"

    found = await _dry_run(owned, [], [owned.market_asset_id], story, current_user_id=owned.user_a_id)

    _assert_results(found, [_result(owned.market_asset_id, "remove", "provider_removed", 0, 0, 0)], story)


@pytest.mark.asyncio
async def test_removing_the_provider_of_an_asset_without_one_is_none(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: the bare asset holds a price, a manual event and a link, and no assignment: its removal is ``none``, zeros.
    """
    await _price(owned.bare_asset_id, 1, "5")
    manual = await _event(owned.bare_asset_id, MANUAL_DAY, AssetEventType.DIVIDEND, "0.45", notes="manual")
    await _income(owned.bare_asset_id, owned.broker_a_id, TransactionType.DIVIDEND, MANUAL_DAY, "4.50", event_id=manual)
    story = f"the dry run of the removal of the provider of the asset {owned.bare_asset_id}, which holds none"

    found = await _dry_run(owned, [], [owned.bare_asset_id], story, current_user_id=owned.user_a_id)

    _assert_results(found, [_nothing(owned.bare_asset_id, "remove")], story)


@pytest.mark.asyncio
async def test_removing_a_plan_with_a_costless_split_lists_it_as_blocking_with_each_callers_view(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: the plan's SPLIT linked to a costless adjustment on broker B, written first, and one on broker A. Removing the
    plan: ``provider_removed``, the SPLIT blocking with the caller's view (user A: broker A's and 1 hidden; user B: broker B's
    and 1 hidden; no caller: none named and 2 hidden), the counts the whole world's.
    """
    world = await _plan_world(owned, split="costless")
    on_b, on_a = world.costless
    views = {
        "user A": ({"current_user_id": owned.user_a_id}, _split_entry(world.split_id, SPLIT_DAY, [on_a], 1)),
        "user B": ({"current_user_id": owned.user_b_id}, _split_entry(world.split_id, SPLIT_DAY, [on_b], 1)),
        "no caller": ({}, _split_entry(world.split_id, SPLIT_DAY, [], 2)),
    }

    for caller, (keyword, entry) in views.items():
        story = f"the dry run, {caller}, of the removal of the plan of the asset {owned.plan_asset_id}, its SPLIT {world.split_id} linked to the costless adjustments {world.costless}"
        found = await _dry_run(owned, [], [owned.plan_asset_id], story, **keyword)
        _assert_results(found, [_result(owned.plan_asset_id, "remove", "provider_removed", 0, len(world.events), len(world.transactions), [entry])], story)


# --------------------------------------------------------------------------- #
# Reds: the request as a whole
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_mixed_request_answers_one_result_per_item_assignments_first_in_order(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist.

    Contract: two assignments (the plan's new rate, then the market asset's yfinance -> justetf) and three removals (the market
    asset, the bare asset, the plan's), in that order: five results, assignments first, then removals, each in its item's order
    with its own action, asset and reason; nothing written.
    """
    plan = await _plan_world(owned, split="with-cost")
    market = await _market_world(owned)
    story = "the dry run of two assignments and three removals"

    found = await _dry_run(
        owned,
        [_plan_item(owned.plan_asset_id, NEW_RATE), _market_item(owned.market_asset_id, OTHER_MARKET, "IE00B4L5Y983")],
        [owned.market_asset_id, owned.bare_asset_id, owned.plan_asset_id],
        story,
        current_user_id=owned.user_a_id,
    )

    expected = [
        _result(owned.plan_asset_id, "assign", "params_changed", len(plan.prices), len(plan.events), len(plan.transactions)),
        _nothing(owned.market_asset_id, "assign"),
        _result(owned.market_asset_id, "remove", "provider_removed", 0, len(market.events), len(market.transactions)),
        _nothing(owned.bare_asset_id, "remove"),
        _result(owned.plan_asset_id, "remove", "provider_removed", 0, len(plan.events), len(plan.transactions)),
    ]
    _assert_results(found, expected, story)


@pytest.mark.asyncio
async def test_an_empty_request_answers_no_result(owned):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist. Contract: no assignment, no removal:
    ``results`` is ``[]``."""
    await _plan_world(owned, split="with-cost")

    found = await _dry_run(owned, [], [], "the dry run of an empty request", current_user_id=owned.user_a_id)

    assert found == [], f"the dry run of an empty request answered {found}: expected no result"


# --------------------------------------------------------------------------- #
# Reds: parity -- the dry run's numbers are what the operation then does
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Done:
    """What an operation really did, read from two snapshots of the unit's rows."""

    prices: int
    events: int
    unlinked: int


def _done(before: dict[str, dict[int, dict]], after: dict[str, dict[int, dict]], asset_id: int, assignment_id: int) -> _Done:
    """What really happened to the asset ``asset_id`` between two snapshots: its price rows gone; the events of the assignment
    ``assignment_id`` gone; the transactions whose ``asset_event_id`` was set and became NULL."""
    prices = {row_id for row_id, row in before["prices"].items() if row["asset_id"] == asset_id} - set(after["prices"])
    events = {row_id for row_id, row in before["events"].items() if row["provider_assignment_id"] == assignment_id} - set(after["events"])
    unlinked = {row_id for row_id, row in before["transactions"].items() if row["asset_event_id"] is not None and row_id in after["transactions"] and after["transactions"][row_id]["asset_event_id"] is None}
    gone = {row_id for row_id, row in before["transactions"].items() if row_id not in after["transactions"]}
    assert not gone, f"the operation deleted the transactions {sorted(gone)}: it must keep every one"
    linked_to_gone_events = {row_id for row_id, row in before["transactions"].items() if row["asset_event_id"] in events}
    assert unlinked == linked_to_gone_events, f"the operation unlinked {sorted(unlinked)} but the transactions linked to the events that went are {sorted(linked_to_gone_events)}"
    return _Done(prices=len(prices), events=len(events), unlinked=len(unlinked))


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["plan-params", "plan-to-market", "market-to-market", "plan-removal", "market-removal"])
async def test_parity_the_dry_runs_numbers_are_what_the_operation_then_does(owned, change):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist (and the removals are refused).

    Contract: the dry run of a request, then the very operation (``bulk_assign_providers`` or ``bulk_remove_providers`` as user
    A), then a count of the rows that really went: the prices deleted of the asset, the events of its assignment deleted, the
    transactions whose ``asset_event_id`` became NULL -- each equal to the dry run's number. A market -> market change really
    deletes nothing, as the dry run said (0, 0, 0); a removal really keeps every price, as it said.
    """
    plan_cases = {"plan-params", "plan-to-market", "plan-removal"}
    if change in plan_cases:
        world = await _plan_world(owned, split="with-cost")
        asset_id, assignment_id = owned.plan_asset_id, owned.plan_assignment_id
        expected_nonzero = (len(world.prices) if change != "plan-removal" else 0, len(world.events), len(world.transactions))
    else:
        world = await _market_world(owned)
        asset_id, assignment_id = owned.market_asset_id, owned.market_assignment_id
        expected_nonzero = (0, len(world.events), len(world.transactions)) if change == "market-removal" else (0, 0, 0)
    items = {
        "plan-params": _plan_item(asset_id, NEW_RATE),
        "plan-to-market": _market_item(asset_id, MARKET, owned.ticker),
        "market-to-market": _market_item(asset_id, OTHER_MARKET, "IE00B4L5Y983"),
    }
    removal = change.endswith("removal")
    story = f"the dry run then the real {change} of the asset {asset_id}"

    found = await _dry_run(owned, [] if removal else [items[change]], [asset_id] if removal else [], story, current_user_id=owned.user_a_id)

    assert len(found) == 1, f"{story} answered {found}: expected one result"
    said = (found[0]["prices_deleted"], found[0]["events_deleted"], found[0]["transactions_unlinked"])
    assert said == expected_nonzero, f"{story} said {said} as (prices, events, transactions): expected {expected_nonzero}, the rows the world holds"
    before = await _committed(owned)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        if removal:
            answer = await AssetSourceManager.bulk_remove_providers([asset_id], session, current_user_id=owned.user_a_id)
            assert answer.success_count == 1, f"{story}: the removal answered {answer.model_dump(mode='json')}: expected one success"
        else:
            await AssetSourceManager.bulk_assign_providers([items[change]], session, current_user_id=owned.user_a_id)
    done = _done(before, await _committed(owned), asset_id, assignment_id)

    assert (done.prices, done.events, done.unlinked) == said, f"{story}: the dry run said {said} as (prices, events, transactions) and the operation really deleted {done.prices} prices, {done.events} events and unlinked {done.unlinked} transactions"


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["assign", "remove"])
async def test_parity_a_blocking_split_is_the_refusal_the_operation_answers(owned, operation):
    """Red today (X-R69): ``AssetSourceManager.provider_change_impact`` does not exist (and a removal does not answer X-R49's
    code).

    Contract: the plan's SPLIT linked to a costless adjustment on broker B, then on broker A. As user A the dry run of a
    change of the plan's rate, or of its removal, lists the SPLIT as blocking; the very operation, as user A, is then refused
    with PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST whose ``details.splits`` are exactly the dry run's ``blocking_splits``;
    nothing written.
    """
    world = await _plan_world(owned, split="costless")
    item = _plan_item(owned.plan_asset_id, NEW_RATE)
    story = f"the dry run then the real {operation} of the plan of the asset {owned.plan_asset_id}, its SPLIT {world.split_id} linked to the costless adjustments {world.costless}"

    found = await _dry_run(owned, [item] if operation == "assign" else [], [] if operation == "assign" else [owned.plan_asset_id], story, current_user_id=owned.user_a_id)

    blocking = found[0]["blocking_splits"]
    assert [split["event_id"] for split in blocking] == [world.split_id], f"{story} listed the blocking SPLITs {blocking}: expected the SPLIT {world.split_id}"
    before = await _committed(owned)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            if operation == "assign":
                await AssetSourceManager.bulk_assign_providers([item], session, current_user_id=owned.user_a_id)
            else:
                await AssetSourceManager.bulk_remove_providers([owned.plan_asset_id], session, current_user_id=owned.user_a_id)
        except AssetSourceError as refusal:
            assert refusal.error_code == CODE, f"{story}: the operation was refused with {refusal.error_code} ({refusal.message}): expected {CODE}"
            assert refusal.details["splits"] == blocking, f"{story}: the refusal names the SPLITs {refusal.details['splits']}: expected exactly the dry run's {blocking}"
        else:
            pytest.fail(f"{story}: the operation went through, yet the dry run said it was blocked by {blocking}: {_moved(before, await _committed(owned))}")
    after = await _committed(owned)
    assert after == before, f"{story}: the operation was refused, yet the database changed: {_moved(before, after)}"


# --------------------------------------------------------------------------- #
# The route, in process
# --------------------------------------------------------------------------- #


async def _caller(user_id: int) -> User:
    """The user ``user_id`` as ``get_current_user`` hands it to a route: the row, loaded and detached."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None, f"barrier: the unit's user {user_id} is gone"
    return user


async def _route(user_id: int | None, body: object) -> httpx.Response:
    """``POST /api/v1/assets/provider/impact`` in process with ``body`` as the JSON, as the user ``user_id`` -- or with no user
    at all (``None``: the real ``get_current_user`` meets a request without a session). The provider router is mounted at
    ``/api/v1/assets`` as the app mounts it, on an app of the call's own, so ``get_current_user`` is overridden there, never
    on the shared app, with the session the real dependency opens on the lane's database."""
    app = FastAPI()
    app.include_router(providers_api.provider_router, prefix="/api/v1/assets")
    if user_id is not None:
        caller = await _caller(user_id)
        app.dependency_overrides[get_current_user] = lambda: caller
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(IMPACT_PATH, json=body)


def _json(response: httpx.Response) -> object:
    try:
        return response.json()
    except ValueError:
        return None


@pytest.mark.asyncio
async def test_the_impact_endpoint_answers_200_with_the_callers_view_and_writes_nothing(owned):
    """Red today (X-R69): 404, the route does not exist.

    Contract: ``POST /assets/provider/impact`` as user A (in process), the plan's world with a costless SPLIT: an assignment (the
    plan's new rate) and two removals (the market asset, the bare one): 200, the body exactly ``{"results": [three results]}``
    in order, each with exactly the contract's keys, the blocking SPLIT with user A's adjustment and 1 hidden (no id of broker B
    anywhere); nothing written.
    """
    world = await _plan_world(owned, split="costless")
    market = await _market_world(owned)
    on_b, on_a = world.costless
    body = {"assignments": [_plan_item(owned.plan_asset_id, NEW_RATE).model_dump(mode="json")], "removals": [owned.market_asset_id, owned.bare_asset_id]}
    before = await _committed(owned)
    story = "POST /assets/provider/impact as user A"

    response = await _route(owned.user_a_id, body)

    assert response.status_code == 200, f"{story} answers {response.status_code} {response.text}: expected 200"
    answer = _json(response)
    assert isinstance(answer, dict) and list(answer) == ["results"], f"{story} answers {response.text}: expected exactly {{'results': […]}}"
    expected = [
        _result(owned.plan_asset_id, "assign", "params_changed", len(world.prices), len(world.events), len(world.transactions), [_split_entry(world.split_id, SPLIT_DAY, [on_a], 1)]),
        _result(owned.market_asset_id, "remove", "provider_removed", 0, len(market.events), len(market.transactions)),
        _nothing(owned.bare_asset_id, "remove"),
    ]
    _assert_results(answer["results"], expected, story)
    assert on_b not in {tx_id for result in answer["results"] for split in result["blocking_splits"] for tx_id in split["transaction_ids"]}, f"{story} names the transaction {on_b} of broker B, which user A cannot see"
    after = await _committed(owned)
    assert after == before, f"{story} changed the database: {_moved(before, after)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("body", "expected"), [pytest.param({}, [], id="empty-body"), pytest.param({"assignments": []}, [], id="empty-assignments"), pytest.param({"removals": ["bare"]}, ["bare"], id="removals-alone")])
async def test_the_impact_endpoint_defaults_a_missing_list_to_empty(owned, body, expected):
    """Red today (X-R69): the route does not exist. Contract: ``assignments`` and ``removals`` default to ``[]``: ``{}`` answers
    200 and no result; a body with the bare asset's removal alone answers its one result (``none``, zeros)."""
    sent = {key: [owned.bare_asset_id if value == "bare" else value for value in values] for key, values in body.items()}
    story = f"POST /assets/provider/impact with {sent}"

    response = await _route(owned.user_a_id, sent)

    assert response.status_code == 200, f"{story} answers {response.status_code} {response.text}: expected 200"
    answer = _json(response)
    results = answer.get("results") if isinstance(answer, dict) else None
    _assert_results(results if isinstance(results, list) else [], [_nothing(owned.bare_asset_id, "remove") for _ in expected], story)


@pytest.mark.asyncio
async def test_the_impact_endpoint_answers_401_without_a_user(owned):
    """Red today (X-R69): 404, the route does not exist. Contract: authenticated like the assignment: a request with no
    session answers 401 (the real ``get_current_user``), and reads nothing."""
    story = "POST /assets/provider/impact without a user"

    response = await _route(None, {"assignments": [], "removals": [owned.plan_asset_id]})

    assert response.status_code == 401, f"{story} answers {response.status_code} {response.text}: expected 401"


@pytest.mark.asyncio
@pytest.mark.parametrize("junk", ["unknown-key", "removals-not-ids", "assignments-not-a-list", "assignment-unknown-key", "assignment-unknown-provider"])
async def test_the_impact_endpoint_answers_422_for_a_body_that_is_not_the_request(owned, junk):
    """Red today (X-R69): 404, the route does not exist. Contract: the request is a ``StrictModel``: an unknown key, ids
    that are not integers, a list that is not a list, an item with an unknown key or with an unknown provider answer 422, and
    write nothing."""
    item = _plan_item(owned.plan_asset_id, NEW_RATE).model_dump(mode="json")
    bodies = {
        "unknown-key": {"assignments": [], "removals": [], "bogus": 1},
        "removals-not-ids": {"removals": ["not-an-id"]},
        "assignments-not-a-list": {"assignments": "no"},
        "assignment-unknown-key": {"assignments": [{**item, "bogus": 1}]},
        "assignment-unknown-provider": {"assignments": [{**item, "provider_code": "no_such_provider"}]},
    }
    before = await _committed(owned)
    story = f"POST /assets/provider/impact with {junk}: {bodies[junk]}"

    response = await _route(owned.user_a_id, bodies[junk])

    assert response.status_code == 422, f"{story} answers {response.status_code} {response.text}: expected 422"
    after = await _committed(owned)
    assert after == before, f"{story} changed the database: {_moved(before, after)}"
