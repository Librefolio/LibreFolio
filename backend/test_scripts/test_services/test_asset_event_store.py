"""Manual asset events: the release 1.3 contract of workstream W, lot E1a (developer decisions 20-23).

Isolation: WRITE_GLOBAL. ``Asset``, ``AssetEvent``, ``AssetProviderAssignment``, ``Broker`` and
``Transaction`` carry no ``user_id``: the two assets this unit creates, and every event,
assignment and transaction written against them, are visible to every concurrent test. The
module fixture creates them under unique names and drops them in teardown; ``owned`` wipes
their events and transactions before and after each test, so no test reads another's rows.

What is pinned (W E1a is not written yet; each test says how it fails before the fix):

* Type normalisation (decision 23, I-09) -- ``FAAssetEventPoint.type``, and through it
  ``FAEventUpsertPoint``, ``FAEventUpsert`` and ``FAScheduledInvestmentSchedule.asset_events``,
  is stripped and upper-cased before validation; a value that is then not an
  ``AssetEventType`` is a ValidationError on the type field. The field stays a plain string
  in the schema. Before: the value is kept as sent, "dividend" is stored, and every later ORM
  read of the asset's events raises LookupError (HTTP 500).
* All or nothing (decision 22, I-12b) -- ``bulk_upsert_events`` writes the whole request or
  nothing of it, and every AssetSourceError says where in ``details``. A missing asset is
  EVENT_ASSET_NOT_FOUND. Before: items committed one by one, a missing asset reported as
  ``count 0`` next to saved items, ``details == {}``.
* Create mode (decision 20, V-22) -- ``FAEventUpsert.mode`` is "upsert" (default, unchanged)
  or "create": a create item carries no ids, and a (date, type) the asset already holds,
  manual or provider, is EVENT_EXISTS listing the stored events. Before: no ``mode`` field.
* event_ids (I-10 S4) -- each item result names, in request order, the row each event wrote.
  Before: no ids, so the mini modal re-reads the day and may link the provider event.
* Delete scoped by asset (decision 21, I-12a) -- ``delete_events_bulk(asset_id, event_ids,
  session, current_user)``: an id of another asset is "not_found" and stays. Before: no
  ``asset_id`` parameter.

"Nothing persisted" is read on a fresh connection (the engine has no pool) with raw SQL, so a
row stored with an invalid type cannot crash the check. A refused request runs as the
endpoint runs it: nobody commits, the session just closes. The provider refresh path
(``_upsert_asset_events`` committing per chunk) is guarded by the refresh tests, not here.
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from pydantic import BaseModel, ValidationError
from sqlalchemy import bindparam, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, Broker, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.events import FAAssetEventPoint, FAEventQueryItem, FAEventUpsert, FAEventUpsertPoint, FAEventUpsertResult
from backend.app.schemas.assets.scheduled_investment import FAScheduledInvestmentSchedule
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.provider import ProviderInputType
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.event_store import EventStoreOperations
from backend.app.services.assets.manager import AssetSourceManager
from backend.test_scripts.test_utils import unique_id

# A window far from the mock dataset and from test_asset_source_upsert_guards.py (1994-1995).
# Events are scoped by asset anyway: the dates only keep the failure output readable.
BASE_DATE = date(1992, 3, 2)


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Owned:
    """What the module created: two USD assets (the first with a provider assignment), a broker, a user."""

    asset_id: int
    other_asset_id: int
    assignment_id: int
    broker_id: int
    user_id: int

    @property
    def asset_ids(self) -> list[int]:
        return [self.asset_id, self.other_asset_id]


async def _wipe(owned: _Owned) -> None:
    """Drop the transactions (they RESTRICT their event) and every event of this unit's assets.

    Bulk deletes load no row, so a row stored with an invalid type cannot break the cleanup.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(Transaction).where(Transaction.broker_id == owned.broker_id))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)))
        await session.commit()


@pytest.fixture(scope="module")
def owned_module() -> _Owned:
    """Two assets, a provider assignment, a broker and a user, dropped in FK-safe order in teardown."""
    marker = unique_id("EventStore")

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset = Asset(display_name=f"Event Store {marker}", currency="USD", asset_type=AssetType.STOCK, active=True)
            other = Asset(display_name=f"Event Store Other {marker}", currency="USD", asset_type=AssetType.STOCK, active=True)
            broker = Broker(name=f"Event Store {marker}", allow_cash_overdraft=True)
            user = User(username=f"evstore_{marker}".lower(), email=f"evstore_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            session.add_all([asset, other, broker, user])
            await session.commit()
            assignment = AssetProviderAssignment(
                asset_id=asset.id,
                provider_code="fake_provider_for_tests",
                identifier=f"EVSTORE.{marker}",
                identifier_type=ProviderInputType.TICKER,
                provider_params="{}",
            )
            session.add(assignment)
            await session.commit()
            return _Owned(asset.id, other.id, assignment.id, broker.id, user.id)

    async def _drop(owned: _Owned) -> None:
        await _wipe(owned)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(owned.asset_ids)))
            await session.execute(delete(Broker).where(Broker.id == owned.broker_id))
            await session.execute(delete(Asset).where(Asset.id.in_(owned.asset_ids)))
            await session.execute(delete(User).where(User.id == owned.user_id))
            await session.commit()

    owned = asyncio.run(_create())
    yield owned
    asyncio.run(_drop(owned))


@pytest_asyncio.fixture
async def owned(owned_module: _Owned):
    """The module's rows, with no event and no transaction before and after the test."""
    await _wipe(owned_module)
    yield owned_module
    await _wipe(owned_module)


async def _add_manual(asset_id: int, offset: int, kind: AssetEventType, amount: str, *, notes: str | None = None) -> int:
    """A manual event written directly, as an earlier save left it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        row = AssetEvent(asset_id=asset_id, date=_day(offset), type=kind, value=Decimal(amount), currency="USD", notes=notes)
        session.add(row)
        await session.commit()
        return row.id


async def _add_provider(owned: _Owned, offset: int, kind: AssetEventType, amount: str, *, notes: str | None = None) -> int:
    """A provider event, written the way a refresh writes it: ``_upsert_asset_events`` under the assignment."""
    point = FAAssetEventPoint(date=_day(offset), type=kind.value, value=Currency(code="USD", amount=Decimal(amount)), notes=notes)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await EventStoreOperations._upsert_asset_events(session, owned.asset_id, [point], owned.assignment_id, "USD")
        await session.commit()
        stmt = select(AssetEvent.id).where(
            AssetEvent.asset_id == owned.asset_id,
            AssetEvent.provider_assignment_id == owned.assignment_id,
            AssetEvent.date == _day(offset),
            AssetEvent.type == kind,
        )
        ids = list((await session.execute(stmt)).scalars().all())
    assert len(ids) == 1, f"expected one provider {kind} on {_day(offset)}, got {ids}"
    return ids[0]


async def _link_tx(owned: _Owned, event_id: int, offset: int) -> int:
    """A DIVIDEND on this unit's broker realising ``event_id``: what pins the event under ON DELETE RESTRICT."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        tx = Transaction(
            broker_id=owned.broker_id,
            asset_id=owned.asset_id,
            type=TransactionType.DIVIDEND,
            date=_day(offset),
            quantity=Decimal("0"),
            amount=Decimal("1.00"),
            currency="USD",
            asset_event_id=event_id,
        )
        session.add(tx)
        await session.commit()
        return tx.id


async def _missing_asset_id() -> int:
    """An asset id nobody holds: ids are AUTOINCREMENT and never reused, so far above the highest is free."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        highest = (await session.execute(select(func.max(Asset.id)))).scalar_one()
    return (highest or 0) + 100_000


async def _unknown_event_id() -> int:
    """An event id nobody holds (AUTOINCREMENT, as for assets)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        highest = (await session.execute(select(func.max(AssetEvent.id)))).scalar_one()
    return (highest or 0) + 1_000_000


# --------------------------------------------------------------------------- #
# Reading back
# --------------------------------------------------------------------------- #

_RAW_EVENTS = text("SELECT id, asset_id, date, type, value, currency, provider_assignment_id, notes FROM asset_events WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))


async def _snapshot(owned: _Owned) -> dict[int, tuple]:
    """id -> (asset_id, date, type, value, currency, provider_assignment_id, notes) of every event of this unit's assets.

    Raw SQL on a fresh connection: what is committed, with the type as stored (no enum decoding).
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(_RAW_EVENTS, {"asset_ids": owned.asset_ids})).all()
    return {row[0]: tuple(row[1:]) for row in rows}


async def _rows(asset_id: int) -> list[AssetEvent]:
    """Every event of the asset through the ORM, lowest id first. Decodes the type: valid rows only."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stmt = select(AssetEvent).where(AssetEvent.asset_id == asset_id).order_by(AssetEvent.id)
        return list((await session.execute(stmt)).scalars().all())


async def _row_id(asset_id: int, offset: int, kind: AssetEventType) -> int:
    """The id of the one manual event of ``kind`` on that day: fails if there is none or more than one."""
    matches = [row.id for row in await _rows(asset_id) if row.date == _day(offset) and row.type == kind and row.provider_assignment_id is None]
    assert len(matches) == 1, f"expected one manual {kind} on {_day(offset)} for asset {asset_id}, got ids {matches}"
    return matches[0]


# --------------------------------------------------------------------------- #
# Requests and results
# --------------------------------------------------------------------------- #


def _ev(offset: int, kind: str, amount: str, *, event_id: int | None = None, currency: str = "USD", notes: str | None = None) -> dict:
    """One event of an upsert item, as the editor sends it."""
    payload: dict = {"date": _day(offset).isoformat(), "type": kind, "value": {"code": currency, "amount": amount}}
    if event_id is not None:
        payload["id"] = event_id
    if notes is not None:
        payload["notes"] = notes
    return payload


def _item(asset_id: int, events: list[dict], *, mode: str | None = None) -> FAEventUpsert:
    """An upsert item validated as the endpoint validates it.

    Called in the test body: before the fix ``mode`` is an unknown field, and the ValidationError
    fails only the tests that need it, not the whole module.
    """
    payload: dict = {"asset_id": asset_id, "events": events}
    if mode is not None:
        payload["mode"] = mode
    return FAEventUpsert.model_validate(payload)


async def _upsert(data: list[FAEventUpsert]):
    """``POST /assets/events`` minus HTTP, for a request that must succeed.

    The commit after the call is what test_asset_source_upsert_guards.py does too; the endpoint
    itself does not commit, so a service forgetting its own commit is caught by the API tests.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_events(data, session)
        await session.commit()
    return result


async def _upsert_refused(data: list[FAEventUpsert]) -> AssetSourceError:
    """``POST /assets/events`` minus HTTP, for a request that must be refused.

    As in the endpoint, nobody commits: the session closes on the error and drops whatever was
    not committed. What the service committed by itself is what "nothing persisted" then sees.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_events(data, session)
        except AssetSourceError as exc:
            return exc
    pytest.fail(f"bulk_upsert_events accepted a request it must refuse: {result}")


def _field(row, name: str):
    """A field of a result row, whether the service returns dicts or models (None when absent)."""
    return row.get(name) if isinstance(row, dict) else getattr(row, name, None)


def _item_result(result, asset_id: int):
    """The result row of the item on ``asset_id``."""
    rows = result["results"] if isinstance(result, dict) else result.results
    return next(row for row in rows if _field(row, "asset_id") == asset_id)


def _amount(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _plain(value):
    """``details`` as plain data: dates as ISO strings, every ``amount`` as a Decimal, models as dicts.

    The contract fixes the shape of ``details``. Whether the service keeps a ``date`` or its ISO
    string, a Decimal or a string amount, is left to it: the HTTP detail is JSON either way, and
    the API tests pin that form.
    """
    if isinstance(value, BaseModel):
        value = value.model_dump()
    if isinstance(value, dict):
        return {key: _amount(item) if key == "amount" else _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    return value


def _existing(event_id: int, offset: int, kind: str, amount: str, *, notes: str | None = None, is_auto: bool = False, linked: int = 0) -> dict:
    """One entry of EVENT_EXISTS ``details["existing"]``, as ``_plain`` renders it."""
    return {
        "id": event_id,
        "date": _day(offset).isoformat(),
        "type": kind,
        "value": {"code": "USD", "amount": Decimal(amount)},
        "notes": notes,
        "is_auto": is_auto,
        "linked_transactions": linked,
    }


def _type_error_locs(exc: ValidationError) -> set[tuple]:
    """The locs of the validation errors raised on an event ``type`` field."""
    return {tuple(err["loc"]) for err in exc.errors() if err["loc"] and err["loc"][-1] == "type"}


# ─────────────────────────────────────────────────────────────────────────────
# Type normalisation (decision 23, I-09)
#
# The editor, the CSV import and a hand-written scheduled-investment schedule all send the
# type as text. Before the fix a lower-case or unknown type was stored as sent; the ORM then
# cannot decode the row (LookupError), and every read of that asset's events is a 500.
# ─────────────────────────────────────────────────────────────────────────────

_EVENT_POINT_MODELS = [pytest.param(FAAssetEventPoint, id="FAAssetEventPoint"), pytest.param(FAEventUpsertPoint, id="FAEventUpsertPoint")]


def _point_payload(kind: str) -> dict:
    return {"date": _day(0).isoformat(), "type": kind, "value": {"code": "USD", "amount": "1.00"}}


@pytest.mark.parametrize("model", _EVENT_POINT_MODELS)
@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        pytest.param("dividend", "DIVIDEND", id="lower"),
        pytest.param(" Split ", "SPLIT", id="padded-mixed"),
        pytest.param("price_adjustment", "PRICE_ADJUSTMENT", id="lower-underscore"),
    ],
)
def test_an_event_type_is_stripped_and_upper_cased(model, raw, canonical):
    """I-09: the type is normalised before validation.

    Before: kept as sent, so "dividend" reaches the database as "dividend".
    """
    assert model.model_validate(_point_payload(raw)).type == canonical


@pytest.mark.parametrize("model", _EVENT_POINT_MODELS)
@pytest.mark.parametrize("raw", [pytest.param("dividendo", id="italian"), pytest.param("", id="empty"), pytest.param("bonus", id="unknown")])
def test_an_unknown_event_type_is_refused_on_the_type_field(model, raw):
    """I-09: a value that is no AssetEventType once normalised is a validation error on ``type``.

    Before: accepted as sent (DID NOT RAISE).
    """
    with pytest.raises(ValidationError) as raised:
        model.model_validate(_point_payload(raw))
    assert _type_error_locs(raised.value) == {("type",)}, raised.value.errors()


@pytest.mark.parametrize("kind", [pytest.param(member.value, id=member.value) for member in AssetEventType])
def test_guard_a_canonical_event_type_is_kept(kind):
    """GUARD: every AssetEventType value validates unchanged (passes before the fix too)."""
    assert FAAssetEventPoint.model_validate(_point_payload(kind)).type == kind


def test_guard_the_type_field_stays_a_plain_string_in_the_schema():
    """GUARD (decision 23: the API does not change): the check is a validator, not an enum in the OpenAPI."""
    prop = FAAssetEventPoint.model_json_schema()["properties"]["type"]
    assert prop.get("type") == "string", prop
    assert not {"enum", "$ref", "allOf", "anyOf"} & set(prop), prop


def test_an_upsert_item_normalises_the_type_of_every_event():
    """I-09 through ``FAEventUpsert``. Before: ["interest", " DIVIDEND "] kept as sent."""
    item = FAEventUpsert.model_validate({"asset_id": 1, "events": [_ev(0, "interest", "1.00"), _ev(1, " DIVIDEND ", "2.00")]})
    assert [event.type for event in item.events] == ["INTEREST", "DIVIDEND"]


def test_an_upsert_item_refuses_an_unknown_type_on_that_event():
    """I-09 through ``FAEventUpsert``: the error names the event (``events.1.type``). Before: DID NOT RAISE."""
    with pytest.raises(ValidationError) as raised:
        FAEventUpsert.model_validate({"asset_id": 1, "events": [_ev(0, "DIVIDEND", "1.00"), _ev(1, "bonus", "2.00")]})
    assert _type_error_locs(raised.value) == {("events", 1, "type")}, raised.value.errors()


def _schedule(kind: str) -> dict:
    """A minimal scheduled-investment schedule carrying one planned event of ``kind``."""
    return {
        "initial_value": {"code": "EUR", "amount": "10000"},
        "schedule": [{"start_date": "2025-01-01", "end_date": "2025-12-31", "annual_rate": "0.05"}],
        "asset_events": [{"date": "2025-07-01", "type": kind, "value": {"code": "EUR", "amount": "250"}}],
    }


def test_a_scheduled_investment_event_type_is_normalised():
    """I-09 through ``FAScheduledInvestmentSchedule.asset_events``. Before: " interest " kept as sent."""
    schedule = FAScheduledInvestmentSchedule.model_validate(_schedule(" interest "))
    assert [event.type for event in schedule.asset_events] == ["INTEREST"]


def test_a_scheduled_investment_event_type_must_be_known():
    """I-09 through ``FAScheduledInvestmentSchedule.asset_events``: ``asset_events.0.type``. Before: DID NOT RAISE."""
    with pytest.raises(ValidationError) as raised:
        FAScheduledInvestmentSchedule.model_validate(_schedule("coupon"))
    assert _type_error_locs(raised.value) == {("asset_events", 0, "type")}, raised.value.errors()


@pytest.mark.asyncio
async def test_a_lower_case_type_is_stored_upper_case_and_reads_back(owned):
    """I-09 at the database: an upsert of "dividend" stores DIVIDEND, and the asset's events read back.

    Before: stored as "dividend" (the raw read shows it); any ORM read of the asset's events,
    ``query_events_bulk`` included, raises LookupError -- a 500 on the API.
    Contract: stored "DIVIDEND"; the ORM decodes AssetEventType.DIVIDEND; the query answers "DIVIDEND".
    """
    await _upsert([_item(owned.asset_id, [_ev(0, "dividend", "1.10")])])

    stored = await _snapshot(owned)
    assert [(row[1], row[2]) for row in stored.values()] == [(_day(0).isoformat(), "DIVIDEND")], stored
    assert [row.type for row in await _rows(owned.asset_id)] == [AssetEventType.DIVIDEND]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        results = await AssetSourceManager.query_events_bulk([FAEventQueryItem(asset_id=owned.asset_id, date_range=DateRangeModel(start=_day(0), end=_day(0)))], session)
    queried = next(result for result in results if result.asset_id == owned.asset_id)
    assert [(event.type, event.value.amount) for event in queried.events] == [("DIVIDEND", Decimal("1.10"))]


# ─────────────────────────────────────────────────────────────────────────────
# All or nothing, and errors that say where (decision 22, I-12b)
#
# Before the fix ``bulk_upsert_events`` committed each item on its own (and
# ``_upsert_asset_events`` each chunk), so a refused item left the items before it saved.
# Within ONE item the edits by id were already validated before the first write
# (5423c334f): the single-item tests below fail on ``details`` only.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_currency_mismatch_in_a_later_item_writes_nothing_of_the_earlier_item(owned):
    """Item 0 (a new event and an in-place update by key) is not persisted when item 1 is refused.

    Before: item 0 is committed on its own, then item 1 raises EVENT_CURRENCY_MISMATCH.
    Contract: EVENT_CURRENCY_MISMATCH; nothing of the request persisted; details name item 1,
    the asset's currency and item 1's event 0.
    """
    kept_id = await _add_manual(owned.asset_id, 10, AssetEventType.INTEREST, "0.50")
    before = await _snapshot(owned)
    request = [
        _item(owned.asset_id, [_ev(11, "DIVIDEND", "1.00"), _ev(10, "INTEREST", "0.75")]),
        _item(owned.other_asset_id, [_ev(11, "DIVIDEND", "1.00", currency="EUR")]),
    ]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_CURRENCY_MISMATCH"
    assert await _snapshot(owned) == before, f"item 0 was persisted (event {kept_id} updated and/or a row added) although the request was refused"
    assert _plain(refused.details) == {
        "asset_id": owned.other_asset_id,
        "item_index": 1,
        "expected": "USD",
        "events": [{"event_index": 0, "date": _day(11).isoformat(), "type": "DIVIDEND", "currency": "EUR"}],
    }


@pytest.mark.asyncio
async def test_a_currency_mismatch_names_every_mismatched_event(owned):
    """Where: the details list each mismatched event with its index, date, type and currency.

    One item: event 0 in EUR, event 1 in USD (the asset's), event 2 in GBP.
    Before: refused before writing, but the error carries a message only (``details == {}``).
    Contract: details {"asset_id", "item_index": 0, "expected": "USD", "events": [#0 EUR, #2 GBP]}.
    """
    before = await _snapshot(owned)
    request = [_item(owned.asset_id, [_ev(15, "DIVIDEND", "1.00", currency="EUR"), _ev(15, "INTEREST", "0.50"), _ev(16, "SPLIT", "2", currency="GBP")])]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_CURRENCY_MISMATCH"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {
        "asset_id": owned.asset_id,
        "item_index": 0,
        "expected": "USD",
        "events": [
            {"event_index": 0, "date": _day(15).isoformat(), "type": "DIVIDEND", "currency": "EUR"},
            {"event_index": 2, "date": _day(16).isoformat(), "type": "SPLIT", "currency": "GBP"},
        ],
    }


@pytest.mark.asyncio
async def test_a_missing_asset_fails_the_whole_request(owned):
    """An item naming a missing asset is EVENT_ASSET_NOT_FOUND, and nothing is persisted.

    Items: a valid one, the missing asset, another valid one.
    Before: no error; the missing item answers count 0 "Asset N not found" and both valid items
    are committed.
    Contract: EVENT_ASSET_NOT_FOUND, details {"asset_id": the missing id, "item_index": 1};
    neither valid item persisted.
    """
    missing_id = await _missing_asset_id()
    before = await _snapshot(owned)
    request = [
        _item(owned.asset_id, [_ev(20, "DIVIDEND", "1.00")]),
        _item(missing_id, [_ev(20, "DIVIDEND", "1.00")]),
        _item(owned.other_asset_id, [_ev(20, "DIVIDEND", "1.00")]),
    ]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_ASSET_NOT_FOUND"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {"asset_id": missing_id, "item_index": 1}


@pytest.mark.asyncio
async def test_a_refused_id_in_a_later_item_writes_nothing_of_the_request(owned):
    """The second event of item 1 names an id nobody may edit: nothing of the request persists.

    Item 0 (other asset): one new event. Item 1: a valid edit by id, an unknown id, the id of a
    provider event, and a new event without id.
    Before: item 0 committed on its own; then EVENT_NOT_EDITABLE with ``details == {}``.
    Contract: EVENT_NOT_EDITABLE; item 0's event, the edit and item 1's new event all absent;
    details {"asset_id", "item_index": 1, "ids": the two refused ids}.
    """
    manual_id = await _add_manual(owned.asset_id, 30, AssetEventType.DIVIDEND, "1.00")
    provider_id = await _add_provider(owned, 31, AssetEventType.DIVIDEND, "1.50")
    unknown_id = await _unknown_event_id()
    before = await _snapshot(owned)
    request = [
        _item(owned.other_asset_id, [_ev(30, "DIVIDEND", "1.00")]),
        _item(
            owned.asset_id,
            [
                _ev(30, "DIVIDEND", "5.00", event_id=manual_id),
                _ev(32, "DIVIDEND", "2.00", event_id=unknown_id),
                _ev(31, "DIVIDEND", "9.99", event_id=provider_id),
                _ev(33, "INTEREST", "0.40"),
            ],
        ),
    ]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_NOT_EDITABLE"
    assert await _snapshot(owned) == before
    details = _plain(refused.details)
    assert {**details, "ids": sorted(details.get("ids") or [])} == {"asset_id": owned.asset_id, "item_index": 1, "ids": sorted([unknown_id, provider_id])}


@pytest.mark.asyncio
async def test_a_key_conflict_in_the_second_event_writes_nothing_of_the_item(owned):
    """Within one item: event 1 conflicts, so the edit, the in-place update and the new event stay unwritten.

    Stored manual events: E1 (D, DIVIDEND), E2 (D, INTEREST), E3 (D', DIVIDEND), E4 (D'', PRICE_ADJUSTMENT).
    Item: 0 changes E3's amount, 1 retypes E1 onto E2's key (the conflict), 2 updates E4 in place
    by key, 3 is a new SPLIT.
    Before: already refused before the first write, but ``details == {}``.
    Contract: EVENT_KEY_CONFLICT; nothing persisted; details {"asset_id", "item_index": 0,
    "date": D, "type": "INTEREST"} -- the key event 1 would have taken.
    """
    e1 = await _add_manual(owned.asset_id, 40, AssetEventType.DIVIDEND, "1.00")
    await _add_manual(owned.asset_id, 40, AssetEventType.INTEREST, "0.50")
    e3 = await _add_manual(owned.asset_id, 41, AssetEventType.DIVIDEND, "2.00")
    await _add_manual(owned.asset_id, 42, AssetEventType.PRICE_ADJUSTMENT, "0.10")
    before = await _snapshot(owned)
    request = [
        _item(
            owned.asset_id,
            [
                _ev(41, "DIVIDEND", "2.75", event_id=e3),
                _ev(40, "INTEREST", "1.00", event_id=e1),
                _ev(42, "PRICE_ADJUSTMENT", "0.20"),
                _ev(43, "SPLIT", "2"),
            ],
        )
    ]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_KEY_CONFLICT"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {"asset_id": owned.asset_id, "item_index": 0, "date": _day(40).isoformat(), "type": "INTEREST"}


# ─────────────────────────────────────────────────────────────────────────────
# Create mode (decision 20, V-22)
#
# "+ New event" means create. In the default "upsert" mode an event without id updates the
# MANUAL event on its (date, type) in place and never touches a provider event (unchanged,
# pinned by test_assets_events.py and test_asset_source_upsert_guards.py). In "create" mode
# a key the asset already holds -- manual or provider -- refuses the item, and the error
# lists the stored events so the modal can offer "use this one".
# ─────────────────────────────────────────────────────────────────────────────


def test_the_mode_defaults_to_upsert_and_accepts_create():
    """``mode`` is "upsert" by default, "create" on request, and refuses anything else as a value.

    Before: no ``mode`` field (the default reads as None; "replace" is an unknown field).
    """
    default = FAEventUpsert.model_validate({"asset_id": 1, "events": [_ev(0, "DIVIDEND", "1.00", event_id=7)]})
    assert getattr(default, "mode", None) == "upsert"
    assert _item(1, [_ev(0, "DIVIDEND", "1.00")], mode="create").mode == "create"
    with pytest.raises(ValidationError) as raised:
        _item(1, [_ev(0, "DIVIDEND", "1.00")], mode="replace")
    assert [(tuple(err["loc"]), err["type"] == "extra_forbidden") for err in raised.value.errors()] == [(("mode",), False)], raised.value.errors()


def test_a_create_item_refuses_an_event_with_an_id():
    """A create item only creates: an event naming a stored row by id is a validation error.

    Before: ``mode`` is an unknown field, so even the create item without id is refused.
    Contract: without id it validates; with an id it is a ValidationError that is not about ``mode``.
    """
    plain = _item(1, [_ev(0, "DIVIDEND", "1.00")], mode="create")
    assert [event.id for event in plain.events] == [None]
    with pytest.raises(ValidationError) as raised:
        _item(1, [_ev(0, "DIVIDEND", "1.00"), _ev(1, "INTEREST", "0.50", event_id=7)], mode="create")
    assert not [err for err in raised.value.errors() if err["loc"] and err["loc"][-1] == "mode"], raised.value.errors()


@pytest.mark.asyncio
async def test_create_on_a_manual_key_is_refused_with_the_stored_event(owned):
    """A create item on a (date, type) held by a manual event is EVENT_EXISTS, and nothing is written.

    Item 0 (other asset) is a valid upsert; item 1 creates on the key of a manual DIVIDEND
    that a transaction realises.
    Before: ValidationError in the test body (``mode`` is an unknown field).
    Contract: EVENT_EXISTS; nothing of the request persisted; details {"asset_id", "item_index": 1,
    "existing": [the stored event, its value and notes, is_auto false, linked_transactions 1]}.
    """
    stored_id = await _add_manual(owned.asset_id, 60, AssetEventType.DIVIDEND, "1.25", notes="seeded")
    await _link_tx(owned, stored_id, 60)
    before = await _snapshot(owned)
    request = [
        _item(owned.other_asset_id, [_ev(60, "DIVIDEND", "1.00")]),
        _item(owned.asset_id, [_ev(60, "DIVIDEND", "3.00")], mode="create"),
    ]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_EXISTS"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {"asset_id": owned.asset_id, "item_index": 1, "existing": [_existing(stored_id, 60, "DIVIDEND", "1.25", notes="seeded", linked=1)]}


@pytest.mark.asyncio
async def test_create_on_a_provider_key_is_refused_with_is_auto(owned):
    """A provider event blocks a create as well, although the default upsert would never touch it.

    Before: ValidationError in the test body (``mode`` is an unknown field).
    Contract: EVENT_EXISTS; nothing written; details existing == [the provider event, is_auto true, linked 0].
    """
    provider_id = await _add_provider(owned, 61, AssetEventType.DIVIDEND, "1.50", notes="from provider")
    before = await _snapshot(owned)
    request = [_item(owned.asset_id, [_ev(61, "DIVIDEND", "1.50")], mode="create")]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_EXISTS"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {"asset_id": owned.asset_id, "item_index": 0, "existing": [_existing(provider_id, 61, "DIVIDEND", "1.50", notes="from provider", is_auto=True)]}


@pytest.mark.asyncio
async def test_create_writes_nothing_when_only_the_second_event_conflicts(owned):
    """The free first event of a create item is not created when the second one conflicts.

    Before: ValidationError in the test body (``mode`` is an unknown field).
    Contract: EVENT_EXISTS listing only the second event's key; the first event absent.
    """
    stored_id = await _add_manual(owned.asset_id, 62, AssetEventType.INTEREST, "0.30")
    before = await _snapshot(owned)
    request = [_item(owned.asset_id, [_ev(63, "DIVIDEND", "1.00"), _ev(62, "INTEREST", "0.35")], mode="create")]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_EXISTS"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {"asset_id": owned.asset_id, "item_index": 0, "existing": [_existing(stored_id, 62, "INTEREST", "0.30")]}


@pytest.mark.asyncio
async def test_event_exists_lists_every_stored_event_of_every_conflicting_key_in_order(owned):
    """``existing`` holds every stored event on every conflicting key of the item, by (date, type, id).

    Stored: on D1 a manual and a provider DIVIDEND; on D0 an INTEREST, a DIVIDEND realised by a
    transaction, and a PRICE_ADJUSTMENT the item does not touch. The item, in this order:
    D1 DIVIDEND, D0 INTEREST, D0 SPLIT (free), D0 DIVIDEND.
    Before: ValidationError in the test body (``mode`` is an unknown field).
    Contract: existing == [D0 DIVIDEND, D0 INTEREST, D1 DIVIDEND manual, D1 DIVIDEND provider];
    the PRICE_ADJUSTMENT is not listed, the SPLIT is not created.
    """
    d1_manual = await _add_manual(owned.asset_id, 71, AssetEventType.DIVIDEND, "1.00", notes="manual")
    d1_provider = await _add_provider(owned, 71, AssetEventType.DIVIDEND, "1.50", notes="provider")
    assert d1_manual < d1_provider, "precondition: the manual D1 DIVIDEND is the older row"
    d0_interest = await _add_manual(owned.asset_id, 70, AssetEventType.INTEREST, "0.25")
    d0_dividend = await _add_manual(owned.asset_id, 70, AssetEventType.DIVIDEND, "0.75")
    await _add_manual(owned.asset_id, 70, AssetEventType.PRICE_ADJUSTMENT, "0.10")
    await _link_tx(owned, d0_dividend, 70)
    before = await _snapshot(owned)
    request = [_item(owned.asset_id, [_ev(71, "DIVIDEND", "9.99"), _ev(70, "INTEREST", "0.30"), _ev(70, "SPLIT", "2"), _ev(70, "DIVIDEND", "0.80")], mode="create")]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_EXISTS"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {
        "asset_id": owned.asset_id,
        "item_index": 0,
        "existing": [
            _existing(d0_dividend, 70, "DIVIDEND", "0.75", linked=1),
            _existing(d0_interest, 70, "INTEREST", "0.25"),
            _existing(d1_manual, 71, "DIVIDEND", "1.00", notes="manual"),
            _existing(d1_provider, 71, "DIVIDEND", "1.50", notes="provider", is_auto=True),
        ],
    }


@pytest.mark.asyncio
async def test_create_without_conflict_creates_the_events_and_returns_their_ids(owned):
    """On keys the asset does not hold, a create item creates its events, as an upsert does today.

    The asset holds a SPLIT on the day; the item creates a DIVIDEND and an INTEREST there.
    Before: ValidationError in the test body (``mode`` is an unknown field).
    Contract: both created; ``event_ids`` == [the DIVIDEND row, the INTEREST row]; the SPLIT untouched.
    """
    split_id = await _add_manual(owned.asset_id, 80, AssetEventType.SPLIT, "2")
    request = [_item(owned.asset_id, [_ev(80, "DIVIDEND", "1.00"), _ev(80, "INTEREST", "0.50")], mode="create")]

    result = await _upsert(request)

    dividend_id = await _row_id(owned.asset_id, 80, AssetEventType.DIVIDEND)
    interest_id = await _row_id(owned.asset_id, 80, AssetEventType.INTEREST)
    assert _field(_item_result(result, owned.asset_id), "event_ids") == [dividend_id, interest_id]
    assert [(row.id, row.value) for row in await _rows(owned.asset_id) if row.type == AssetEventType.SPLIT] == [(split_id, Decimal("2"))]


# ─────────────────────────────────────────────────────────────────────────────
# Ids in the result (I-10 S4)
#
# ``EventCreateMiniModal.svelte`` re-reads the day after saving to find the event it just
# wrote, and may pick the provider event on the same key. The result now names the rows.
# ─────────────────────────────────────────────────────────────────────────────


def test_the_upsert_result_carries_the_event_ids():
    """``FAEventUpsertResult.event_ids`` exists. Before: an unknown field (ValidationError)."""
    result = FAEventUpsertResult.model_validate({"asset_id": 1, "count": 2, "message": "Upserted 2 manual events", "event_ids": [11, 12]})
    assert result.event_ids == [11, 12]


@pytest.mark.asyncio
async def test_event_ids_name_the_row_each_event_wrote(owned):
    """In request order: a new row's id, the id of the manual row updated in place, the edited id.

    Item: 0 a new DIVIDEND, 1 a no-id event on the key of a stored manual DIVIDEND, 2 an edit
    by id that moves a stored INTEREST to another day.
    Before: the result row carries no ``event_ids``.
    Contract: event_ids == [new row, the stored DIVIDEND, the moved INTEREST]; the rows hold the sent values.
    """
    kept_id = await _add_manual(owned.asset_id, 90, AssetEventType.DIVIDEND, "1.00")
    moved_id = await _add_manual(owned.asset_id, 91, AssetEventType.INTEREST, "0.50")
    request = [_item(owned.asset_id, [_ev(92, "DIVIDEND", "2.00"), _ev(90, "DIVIDEND", "1.10"), _ev(93, "INTEREST", "0.60", event_id=moved_id)])]

    result = await _upsert(request)

    new_id = await _row_id(owned.asset_id, 92, AssetEventType.DIVIDEND)
    assert _field(_item_result(result, owned.asset_id), "event_ids") == [new_id, kept_id, moved_id]
    assert {row.id: (row.date, row.type, row.value) for row in await _rows(owned.asset_id)} == {
        kept_id: (_day(90), AssetEventType.DIVIDEND, Decimal("1.10")),
        moved_id: (_day(93), AssetEventType.INTEREST, Decimal("0.60")),
        new_id: (_day(92), AssetEventType.DIVIDEND, Decimal("2.00")),
    }


@pytest.mark.asyncio
async def test_event_ids_never_name_the_provider_event_on_the_same_key(owned):
    """A no-id upsert on a key held only by a provider event creates a manual row, and names that row.

    The case the mini modal gets wrong today: re-reading the day, it can link the provider event.
    Before: no ``event_ids``.
    Contract: event_ids == [the new manual row]; the provider row is neither named nor changed.
    """
    provider_id = await _add_provider(owned, 95, AssetEventType.DIVIDEND, "1.50")
    request = [_item(owned.asset_id, [_ev(95, "DIVIDEND", "1.50")])]

    result = await _upsert(request)

    manual_id = await _row_id(owned.asset_id, 95, AssetEventType.DIVIDEND)
    assert manual_id != provider_id
    assert _field(_item_result(result, owned.asset_id), "event_ids") == [manual_id]
    assert [(row.id, row.value) for row in await _rows(owned.asset_id) if row.provider_assignment_id is not None] == [(provider_id, Decimal("1.50"))]


# ─────────────────────────────────────────────────────────────────────────────
# Delete scoped by asset (decision 21, I-12a)
#
# The delete names the asset, and only that asset's events can go. Own ids behave as
# before: deleted, not_found, or in_use with the accessible/hidden breakdown, and no
# rollback of the deletions that succeeded (decision 22 is about upserts).
# ─────────────────────────────────────────────────────────────────────────────


async def _delete(owned: _Owned, asset_id: int, event_ids: list[int]):
    """``DELETE /assets/events?asset_id=...&ids=...`` minus HTTP, as this unit's user."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await session.get(User, owned.user_id)
        return await AssetSourceManager.delete_events_bulk(asset_id=asset_id, event_ids=event_ids, session=session, current_user=user)


@pytest.mark.asyncio
async def test_delete_is_scoped_to_the_asset(owned):
    """An id of another asset is "not_found" for this asset, and that event stays.

    Before: TypeError -- ``delete_events_bulk`` takes no ``asset_id``, and deletes any id it is given.
    Contract: own id deleted; the other asset's id not_found and still stored; an unknown id not_found.
    """
    own_id = await _add_manual(owned.asset_id, 100, AssetEventType.DIVIDEND, "1.00")
    foreign_id = await _add_manual(owned.other_asset_id, 100, AssetEventType.DIVIDEND, "1.00")
    unknown_id = await _unknown_event_id()

    response = await _delete(owned, owned.asset_id, [own_id, foreign_id, unknown_id])

    assert {item.event_id: item.status for item in response.results} == {own_id: "deleted", foreign_id: "not_found", unknown_id: "not_found"}
    assert (response.deleted_count, response.not_found_count, response.in_use_count) == (1, 2, 0)
    stored = await _snapshot(owned)
    assert own_id not in stored
    assert foreign_id in stored, f"event {foreign_id} of asset {owned.other_asset_id} was deleted through asset {owned.asset_id}"


@pytest.mark.asyncio
async def test_delete_keeps_the_in_use_breakdown_of_its_own_events(owned):
    """Scoping changes nothing for the asset's own ids: a linked event stays, with its breakdown.

    This unit's user has no access to the broker of the transaction, so the link counts as hidden.
    Before: TypeError (no ``asset_id`` parameter).
    Contract: in_use, accessible [] and hidden 1; the event still stored.
    """
    linked_id = await _add_manual(owned.asset_id, 101, AssetEventType.DIVIDEND, "1.00")
    await _link_tx(owned, linked_id, 101)

    response = await _delete(owned, owned.asset_id, [linked_id])

    assert [(item.event_id, item.status, item.accessible_transactions, item.hidden_transactions_count) for item in response.results] == [(linked_id, "in_use", [], 1)]
    assert linked_id in await _snapshot(owned)
