"""
Checkpoint 6 — ``BrokerService.update_bulk`` puts a REFUSED change back, in the session itself (developer, 30/10/2026).

Module under test: ``backend/app/services/brokers/broker_service.py`` — ``BrokerService.update_bulk(items, broker_ids,
user_id, as_user_id=None)``. For each item it loads the broker and APPLIES every field of the item to the ORM object
(``name``, ``description``, ``portal_url``, ``icon_url``, ``default_import_plugin``, ``is_active``, ``opened_at``,
``allow_cash_overdraft``, ``allow_asset_shorting``, ``updated_at``); only THEN, when an overdraft/shorting flag goes
True -> False, it runs ``_validate_broker_balances(broker_id, None)``. On a ``BalanceValidationError`` it answers
``BRUpdateResult(success=False, validation_triggered=True, error=...)`` and ``continue``s, but the changed attributes stay
on the object in the session.

Today's single-item endpoint (``api/v1/brokers/crud.py::update_broker``) saves nothing because it rolls back when
``success_count == 0``; a caller that saves after a PARTIAL success (one item refused, one valid) would persist the
refused broker's turned-off flag and its other fields. The change under test: a refused item leaves the broker EXACTLY
as it was before the item, in the session, whatever the caller does next. The refusal itself (``success=False``,
``validation_triggered=True``) stays as it is.

Reds — fail today, pass after the change:

- ``TestPartialSuccessThenCommit``: two brokers in one call, A refused and B valid, then ``session.commit()``; read back
  through a FRESH session, A has its old flag AND every old field, B its new values. Red reason: A comes back with the
  flag off and the new name/description/... (the refused change was saved).
- ``TestARefusedItemIsPutBackInTheSessionItself``: the broker object, read right after ``update_bulk`` and BEFORE any
  commit or rollback, already shows the old values. Red reason: it still shows the item's values.

Guards — green before and after:

- a valid turn-off (no negative cash) is applied and saved, a rename-only item is applied, an item that is refused for a
  duplicate name (it never touched the broker), an unknown broker id, an access-denied one (a VIEWER, a stranger);
- the refusal fields (``success=False``, ``validation_triggered=True``, an error) of the refused item.

Private in-memory SQLite with the ORM schema (``create_all``), disposed at teardown: no lane database, no server, no
network. The three API tests of ``test_api/test_broker_overdraft_off_refused.py`` stay as they are: they go through the
endpoint, which rolls back, and stay green with a service that restores by itself.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.schemas.brokers import BRUpdateItem
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.utils.datetime_utils import utcnow

#: Every attribute an item can touch (and ``updated_at``, which every applied item bumps).
FIELDS = (
    "name",
    "description",
    "portal_url",
    "icon_url",
    "default_import_plugin",
    "is_active",
    "opened_at",
    "allow_cash_overdraft",
    "allow_asset_shorting",
    "updated_at",
)

OLD_OPENED = date(2019, 5, 5)
NEW_OPENED = date(2020, 1, 1)
D10 = date(2026, 10, 10)


# =============================================================================
# FIXTURES AND ROWS
# =============================================================================


@pytest_asyncio.fixture
async def engine():
    """This test's own in-memory database with the ORM schema: never the lane's database."""
    private_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with private_engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield private_engine
    finally:
        await private_engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    """The caller's session: the one ``update_bulk`` works in and the test commits (or not)."""
    async with AsyncSession(engine, expire_on_commit=False) as caller_session:
        yield caller_session


def unique() -> str:
    return uuid.uuid4().hex[:10]


async def new_user(session: AsyncSession) -> int:
    name = f"cp6_{unique()}"
    user = User(username=name, email=f"{name}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    return user.id


async def new_broker(session: AsyncSession, owner_id: int, *, overdraft: bool = False, shorting: bool = False, role: UserRole = UserRole.OWNER) -> int:
    """A broker with EVERY updatable field set to an old value, and the access row of ``owner_id``."""
    broker = Broker(
        name=f"CP6 old {unique()}",
        description="old description",
        portal_url="https://old.example",
        icon_url="https://old.example/icon.png",
        default_import_plugin="old_plugin",
        is_active=True,
        opened_at=OLD_OPENED,
        allow_cash_overdraft=overdraft,
        allow_asset_shorting=shorting,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(broker)
    await session.flush()
    session.add(BrokerUserAccess(user_id=owner_id, broker_id=broker.id, role=role, share_percentage=Decimal("1"), created_at=utcnow(), updated_at=utcnow()))
    await session.flush()
    return broker.id


async def withdraw(session: AsyncSession, broker_id: int, amount: str = "-100", currency: str = "EUR") -> None:
    """A WITHDRAWAL written straight into the session, past the batch and its replay: the cash goes below zero."""
    session.add(Transaction(broker_id=broker_id, type=TransactionType.WITHDRAWAL, date=D10, quantity=Decimal("0"), amount=Decimal(amount), currency=currency, created_at=utcnow(), updated_at=utcnow()))
    await session.flush()


async def short_position(session: AsyncSession, broker_id: int, quantity: str = "-3") -> None:
    """A negative asset quantity stored (an ADJUSTMENT of ``quantity``): the shorting flag cannot be turned off."""
    asset = Asset(display_name=f"CP6 asset {unique()}", asset_type=AssetType.STOCK, currency="EUR", created_at=utcnow(), updated_at=utcnow())
    session.add(asset)
    await session.flush()
    session.add(Transaction(broker_id=broker_id, asset_id=asset.id, type=TransactionType.ADJUSTMENT, date=D10, quantity=Decimal(quantity), amount=Decimal("0"), currency=None, created_at=utcnow(), updated_at=utcnow()))
    await session.flush()


async def settle(session: AsyncSession, *broker_ids: int) -> dict[int, dict]:
    """Commit the set-up and re-read the brokers, so the session objects hold the values as the database stores them.
    Returns each broker's fields as they stand: what ``update_bulk`` must leave on a refused one."""
    await session.commit()
    snapshots: dict[int, dict] = {}
    for broker_id in broker_ids:
        broker = await session.get(Broker, broker_id)
        await session.refresh(broker)
        snapshots[broker_id] = fields_of(broker)
    return snapshots


def fields_of(broker: Broker) -> dict:
    return {name: getattr(broker, name) for name in FIELDS}


async def in_session(session: AsyncSession, broker_id: int) -> dict:
    """The broker object the session holds right now, with no query (``get`` answers from the identity map): its fields
    exactly as ``update_bulk`` left them, before any commit or rollback."""
    return fields_of(await session.get(Broker, broker_id))


async def stored(engine, broker_id: int) -> dict:
    """The broker as the database stores it, through a FRESH session on the same engine."""
    async with AsyncSession(engine, expire_on_commit=False) as fresh:
        broker = await fresh.get(Broker, broker_id)
        assert broker is not None, f"broker {broker_id} is gone"
        return fields_of(broker)


def refused_item(**flags) -> BRUpdateItem:
    """An item that changes EVERY field of the broker; ``flags`` choose which flag it turns off."""
    return BRUpdateItem(
        name=f"CP6 new {unique()}",
        description="new description",
        portal_url="https://new.example",
        icon_url="https://new.example/icon.png",
        default_import_plugin="new_plugin",
        is_active=False,
        opened_at=NEW_OPENED,
        **flags,
    )


def valid_item() -> BRUpdateItem:
    """A change broker B can take: a rename and the active flag."""
    return BRUpdateItem(name=f"CP6 renamed {unique()}", is_active=False)


def changed(before: dict, after: dict) -> list[str]:
    """The fields whose value differs, for the failure message."""
    return [f"{name}: {before[name]!r} -> {after[name]!r}" for name in FIELDS if before[name] != after[name]]


def assert_untouched(before: dict, after: dict, why: str) -> None:
    diff = changed(before, after)
    assert not diff, f"{why}; changed fields: {diff}"


# =============================================================================
# THE HEART: A REFUSED ITEM LEAVES THE BROKER AS IT WAS, IN THE SESSION
# =============================================================================

#: (the flag the item turns off, the set-up that makes turning it off refused)
REFUSAL_CASES = ["overdraft", "shorting"]


async def refused_broker(session: AsyncSession, owner_id: int, kind: str) -> tuple[int, BRUpdateItem]:
    """A broker for which turning the flag of ``kind`` off is refused, and the item that tries it (with every other field changed too)."""
    if kind == "overdraft":
        broker_id = await new_broker(session, owner_id, overdraft=True)
        await withdraw(session, broker_id)  # cash -100 EUR: turning the overdraft off is refused
        return broker_id, refused_item(allow_cash_overdraft=False)
    broker_id = await new_broker(session, owner_id, overdraft=True, shorting=True)  # overdraft stays on: only the quantity is at stake
    await short_position(session, broker_id)  # asset quantity -3: turning the shorting off is refused
    return broker_id, refused_item(allow_asset_shorting=False)


class TestPartialSuccessThenCommit:
    """RED today: one item refused and one valid in ONE call, then the caller saves (as a bulk caller does after a partial success)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", REFUSAL_CASES)
    @pytest.mark.parametrize("refused_first", [True, False])
    async def test_the_refused_broker_is_not_saved_the_valid_one_is(self, engine, session, kind, refused_first):
        owner_id = await new_user(session)
        a_id, a_item = await refused_broker(session, owner_id, kind)
        b_id = await new_broker(session, owner_id)
        b_item = valid_item()
        before = await settle(session, a_id, b_id)

        pairs = [(a_item, a_id), (b_item, b_id)] if refused_first else [(b_item, b_id), (a_item, a_id)]
        response = await BrokerService(session).update_bulk([p[0] for p in pairs], [p[1] for p in pairs], user_id=owner_id)
        by_id = {r.id: r for r in response.results}

        # the refusal itself is unchanged
        assert response.success_count == 1, response
        assert by_id[a_id].success is False and by_id[a_id].validation_triggered is True and by_id[a_id].error, by_id[a_id]
        assert by_id[b_id].success is True, by_id[b_id]

        await session.commit()  # a bulk caller saves after a partial success

        assert_untouched(before[a_id], await stored(engine, a_id), f"the refused {kind} item was saved: broker A must come back exactly as it was")
        b_after = await stored(engine, b_id)
        assert b_after["name"] == b_item.name and b_after["is_active"] is False, f"broker B's valid change was lost: {b_after}"
        assert b_after["allow_cash_overdraft"] is before[b_id]["allow_cash_overdraft"] and b_after["allow_asset_shorting"] is before[b_id]["allow_asset_shorting"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", REFUSAL_CASES)
    async def test_the_flag_that_was_refused_stays_on_after_the_commit(self, engine, session, kind):
        """The narrowest statement of the defect: the refused flag, alone, is still True after the save."""
        owner_id = await new_user(session)
        a_id, a_item = await refused_broker(session, owner_id, kind)
        b_id = await new_broker(session, owner_id)
        await settle(session, a_id, b_id)

        await BrokerService(session).update_bulk([a_item, valid_item()], [a_id, b_id], user_id=owner_id)
        await session.commit()

        flag = "allow_cash_overdraft" if kind == "overdraft" else "allow_asset_shorting"
        assert (await stored(engine, a_id))[flag] is True, f"the refused turn-off of {flag} was persisted by the caller's commit"


class TestARefusedItemIsPutBackInTheSessionItself:
    """RED today: the session object, read right after ``update_bulk`` and BEFORE any commit or rollback, already shows the old values.
    The correctness of a refusal must not depend on what the caller does next."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", REFUSAL_CASES)
    async def test_the_object_in_the_session_shows_the_old_values(self, session, kind):
        owner_id = await new_user(session)
        a_id, a_item = await refused_broker(session, owner_id, kind)
        before = await settle(session, a_id)

        response = await BrokerService(session).update_bulk([a_item], [a_id], user_id=owner_id)

        assert response.success_count == 0 and response.results[0].validation_triggered is True and response.results[0].success is False
        assert_untouched(before[a_id], await in_session(session, a_id), f"the {kind} item was refused but the broker object still carries it, before any commit or rollback")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", REFUSAL_CASES)
    async def test_the_session_has_nothing_to_flush_for_the_refused_broker(self, session, kind):
        """A refused item leaves no pending change behind: the broker is not dirty, so any later flush or commit has nothing of it to write."""
        owner_id = await new_user(session)
        a_id, a_item = await refused_broker(session, owner_id, kind)
        before = await settle(session, a_id)

        await BrokerService(session).update_bulk([a_item], [a_id], user_id=owner_id)
        await session.flush()

        assert_untouched(before[a_id], await in_session(session, a_id), "a flush after the refusal must not write the refused values")


# =============================================================================
# GUARDS: WHAT KEEPS ITS BEHAVIOUR
# =============================================================================


class TestWhatIsStillApplied:
    """Guards, green today and after."""

    @pytest.mark.asyncio
    async def test_a_valid_turn_off_is_applied_and_saved(self, engine, session):
        """No negative cash: turning the overdraft off passes the validation, ``validation_triggered`` is True, and the commit saves it."""
        owner_id = await new_user(session)
        broker_id = await new_broker(session, owner_id, overdraft=True)
        item = refused_item(allow_cash_overdraft=False)  # every field changes: nothing to refuse
        await settle(session, broker_id)

        response = await BrokerService(session).update_bulk([item], [broker_id], user_id=owner_id)
        await session.commit()

        assert response.success_count == 1
        assert response.results[0].success is True and response.results[0].validation_triggered is True
        after = await stored(engine, broker_id)
        assert after["allow_cash_overdraft"] is False
        assert (after["name"], after["description"], after["portal_url"], after["icon_url"], after["default_import_plugin"], after["is_active"], after["opened_at"]) == (
            item.name,
            "new description",
            "https://new.example",
            "https://new.example/icon.png",
            "new_plugin",
            False,
            NEW_OPENED,
        )

    @pytest.mark.asyncio
    async def test_a_valid_shorting_turn_off_is_applied_and_saved(self, engine, session):
        owner_id = await new_user(session)
        broker_id = await new_broker(session, owner_id, overdraft=True, shorting=True)
        await settle(session, broker_id)

        response = await BrokerService(session).update_bulk([BRUpdateItem(allow_asset_shorting=False)], [broker_id], user_id=owner_id)
        await session.commit()

        assert response.results[0].success is True and response.results[0].validation_triggered is True
        assert (await stored(engine, broker_id))["allow_asset_shorting"] is False

    @pytest.mark.asyncio
    async def test_a_rename_only_item_is_applied_and_triggers_no_validation(self, engine, session):
        owner_id = await new_user(session)
        broker_id = await new_broker(session, owner_id, overdraft=True)
        await withdraw(session, broker_id)  # negative cash: it would refuse a turn-off, but the item does not ask for one
        before = await settle(session, broker_id)
        item = BRUpdateItem(name=f"CP6 only a rename {unique()}")

        response = await BrokerService(session).update_bulk([item], [broker_id], user_id=owner_id)
        await session.commit()

        assert response.results[0].success is True and response.results[0].validation_triggered is False
        after = await stored(engine, broker_id)
        assert after["name"] == item.name
        assert {k: v for k, v in after.items() if k not in ("name", "updated_at")} == {k: v for k, v in before[broker_id].items() if k not in ("name", "updated_at")}

    @pytest.mark.asyncio
    async def test_turning_a_flag_on_or_leaving_it_is_never_validated(self, session):
        owner_id = await new_user(session)
        broker_id = await new_broker(session, owner_id, overdraft=False)
        await settle(session, broker_id)

        response = await BrokerService(session).update_bulk([BRUpdateItem(allow_cash_overdraft=True, allow_asset_shorting=False)], [broker_id], user_id=owner_id)

        assert response.results[0].success is True and response.results[0].validation_triggered is False


class TestRefusalsThatNeverTouchedTheBroker:
    """Guards, green today and after: the other refusals keep their results, and the broker stays as it was."""

    @pytest.mark.asyncio
    async def test_an_unknown_broker_id(self, session):
        owner_id = await new_user(session)
        missing_id = 987_654_321

        response = await BrokerService(session).update_bulk([valid_item()], [missing_id], user_id=owner_id)

        assert response.success_count == 0
        assert response.results[0].id == missing_id and response.results[0].success is False and "not found" in response.results[0].error

    @pytest.mark.asyncio
    async def test_access_denied_to_a_viewer_and_to_a_stranger(self, session):
        owner_id = await new_user(session)
        viewer_id = await new_user(session)
        stranger_id = await new_user(session)
        broker_id = await new_broker(session, owner_id)
        session.add(BrokerUserAccess(user_id=viewer_id, broker_id=broker_id, role=UserRole.VIEWER, share_percentage=Decimal("0"), created_at=utcnow(), updated_at=utcnow()))
        await session.flush()
        before = await settle(session, broker_id)

        for user_id in (viewer_id, stranger_id):
            response = await BrokerService(session).update_bulk([valid_item()], [broker_id], user_id=user_id)
            assert response.success_count == 0
            assert response.results[0].success is False and response.results[0].error == "Access denied", (user_id, response.results[0])
            assert response.results[0].validation_triggered is False

        assert_untouched(before[broker_id], await in_session(session, broker_id), "an access-denied item never touches the broker")

    @pytest.mark.asyncio
    async def test_a_duplicate_name_is_refused_and_the_broker_is_untouched(self, engine, session):
        owner_id = await new_user(session)
        broker_id = await new_broker(session, owner_id, overdraft=True)
        other_id = await new_broker(session, owner_id)
        other_name = (await session.get(Broker, other_id)).name
        before = await settle(session, broker_id, other_id)

        response = await BrokerService(session).update_bulk([BRUpdateItem(name=other_name, description="should not land")], [broker_id], user_id=owner_id)
        await session.commit()

        assert response.success_count == 0 and response.results[0].success is False and "already exists" in response.results[0].error
        assert_untouched(before[broker_id], await stored(engine, broker_id), "a duplicate-name item is checked before anything is applied")

    @pytest.mark.asyncio
    async def test_a_valid_item_after_an_unknown_id_is_still_applied(self, engine, session):
        owner_id = await new_user(session)
        broker_id = await new_broker(session, owner_id)
        await settle(session, broker_id)
        item = valid_item()

        response = await BrokerService(session).update_bulk([valid_item(), item], [987_654_321, broker_id], user_id=owner_id)
        await session.commit()

        assert [r.success for r in response.results] == [False, True]
        assert (await stored(engine, broker_id))["name"] == item.name


def test_the_fields_checked_are_the_fields_an_item_can_change() -> None:
    """Self-check (pure): the field list of this file covers every attribute ``update_bulk`` writes, so a new one cannot go unwatched."""
    item_fields = set(BRUpdateItem.model_fields)
    assert item_fields <= set(FIELDS), f"BRUpdateItem has fields this test does not compare: {sorted(item_fields - set(FIELDS))}"
    assert "updated_at" in FIELDS
