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
* Deletions inside the upsert (lot E1b, decision of 15/10 16:20) -- ``FAEventUpsert.delete_ids``:
  the editor saves in ONE request, deletions first, so an edit may take the key a deletion frees
  (I-10) and a refusal anywhere keeps the deletions too (decision 22). Any event of the item's
  asset can be deleted, manual or provider (correction of 15/10 17:49: the 1.2 editor deleted a
  provider event through ``DELETE``, and the next sync writes it back); an id that is not an event
  of that asset is EVENT_NOT_DELETABLE, and an event a transaction realises, provider ones
  included, is EVENT_IN_USE. Before: ``delete_ids`` is an unknown field.
* Retyping a SPLIT (workstream J, lot CP-14a, P-10, developer decision 27 option A) -- an edit
  whose stored row is a SPLIT and whose new type is not is refused while an incoming ADJUSTMENT
  (quantity > 0) without ``cost_basis_override`` is linked to the event: retyped, that row would stop
  being a split rescale and become an acquisition of unknown cost (MISSING_COST_BASIS).
  EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST, ``details`` {"event_id", "date" of the stored SPLIT,
  "transaction_ids": those the caller can see, sorted, "hidden_transactions_count": the others}, for
  the first such edit in request order, before the first write. Without a caller none is named
  (X-R47b): these refusal tests answer the holder, a second user of the module holding an access to
  the unit's broker, who sees every transaction written there, so they keep pinning which ones.
  Before: every retype is accepted.

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
from sqlalchemy import bindparam, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
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
    """What the module created: two USD assets (the first with a provider assignment), a broker, and two users: ``user_id``,
    with no access to the broker, and ``holder_id``, holding an OWNER access to it, so every transaction this unit writes
    is one the holder can see."""

    asset_id: int
    other_asset_id: int
    assignment_id: int
    broker_id: int
    user_id: int
    holder_id: int

    @property
    def asset_ids(self) -> list[int]:
        return [self.asset_id, self.other_asset_id]

    @property
    def user_ids(self) -> list[int]:
        return [self.user_id, self.holder_id]


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
    """Two assets, a provider assignment, a broker, two users and the holder's access to the broker, dropped in FK-safe
    order in teardown."""
    marker = unique_id("EventStore")

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset = Asset(display_name=f"Event Store {marker}", currency="USD", asset_type=AssetType.STOCK, active=True)
            other = Asset(display_name=f"Event Store Other {marker}", currency="USD", asset_type=AssetType.STOCK, active=True)
            broker = Broker(name=f"Event Store {marker}", allow_cash_overdraft=True)
            user = User(username=f"evstore_{marker}".lower(), email=f"evstore_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            holder = User(username=f"evholder_{marker}".lower(), email=f"evholder_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            session.add_all([asset, other, broker, user, holder])
            await session.commit()
            assignment = AssetProviderAssignment(
                asset_id=asset.id,
                provider_code="fake_provider_for_tests",
                identifier=f"EVSTORE.{marker}",
                identifier_type=ProviderInputType.TICKER,
                provider_params="{}",
            )
            access = BrokerUserAccess(user_id=holder.id, broker_id=broker.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            session.add_all([assignment, access])
            await session.commit()
            return _Owned(asset.id, other.id, assignment.id, broker.id, user.id, holder.id)

    async def _drop(owned: _Owned) -> None:
        await _wipe(owned)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(BrokerUserAccess).where(or_(BrokerUserAccess.broker_id == owned.broker_id, BrokerUserAccess.user_id.in_(owned.user_ids))))
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(owned.asset_ids)))
            await session.execute(delete(Broker).where(Broker.id == owned.broker_id))
            await session.execute(delete(Asset).where(Asset.id.in_(owned.asset_ids)))
            await session.execute(delete(User).where(User.id.in_(owned.user_ids)))
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


async def _link_tx(owned: _Owned, event_id: int, offset: int, *, kind: TransactionType = TransactionType.DIVIDEND, quantity: str = "0", cost: str | None = None) -> int:
    """A transaction on this unit's broker realising ``event_id``: what pins the event under ON DELETE RESTRICT.

    By default a DIVIDEND of 1.00 USD. An ADJUSTMENT moves ``quantity`` units and no cash, as a split's adjustment
    does; ``cost`` is its per-unit ``cost_basis_override`` in USD, None for no cost (what Auto mode stores on a row
    linked to a SPLIT).
    """
    moves_cash = kind != TransactionType.ADJUSTMENT
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        tx = Transaction(
            broker_id=owned.broker_id,
            asset_id=owned.asset_id,
            type=kind,
            date=_day(offset),
            quantity=Decimal(quantity),
            amount=Decimal("1.00") if moves_cash else Decimal("0"),
            currency="USD" if moves_cash else None,
            cost_basis_override=None if cost is None else Decimal(cost),
            cost_basis_currency=None if cost is None else "USD",
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
_RAW_EVENTS_STAMPED = text("SELECT id, asset_id, date, type, value, currency, provider_assignment_id, notes, updated_at FROM asset_events WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))
_RAW_TRANSACTIONS = text("SELECT id, asset_id, type, date, quantity, amount, currency, cost_basis_override, cost_basis_currency, asset_event_id, updated_at FROM transactions WHERE broker_id = :broker_id ORDER BY id")


async def _snapshot(owned: _Owned, *, stamped: bool = False) -> dict[int, tuple]:
    """id -> (asset_id, date, type, value, currency, provider_assignment_id, notes) of every event of this unit's assets.

    Raw SQL on a fresh connection: what is committed, with the type as stored (no enum decoding). ``stamped`` appends
    ``updated_at``: a write that puts every value back as it was still moves it.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(_RAW_EVENTS_STAMPED if stamped else _RAW_EVENTS, {"asset_ids": owned.asset_ids})).all()
    return {row[0]: tuple(row[1:]) for row in rows}


async def _tx_snapshot(owned: _Owned) -> dict[int, tuple]:
    """id -> (asset_id, type, date, quantity, amount, currency, cost basis, its currency, asset_event_id, updated_at).

    Every transaction on this unit's broker, read as ``_snapshot`` reads the events: raw SQL on a fresh connection.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(_RAW_TRANSACTIONS, {"broker_id": owned.broker_id})).all()
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


def _item(asset_id: int, events: list[dict], *, mode: str | None = None, delete_ids: list[int] | None = None) -> FAEventUpsert:
    """An upsert item validated as the endpoint validates it.

    Called in the test body: before the fix ``mode`` (E1a) and ``delete_ids`` (E1b) are unknown
    fields, and the ValidationError fails only the tests that need them, not the whole module.
    """
    payload: dict = {"asset_id": asset_id, "events": events}
    if mode is not None:
        payload["mode"] = mode
    if delete_ids is not None:
        payload["delete_ids"] = delete_ids
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


async def _upsert_refused(data: list[FAEventUpsert], *, current_user_id: int | None = None) -> AssetSourceError:
    """``POST /assets/events`` minus HTTP, for a request that must be refused.

    ``current_user_id`` is the caller the route passes: a refusal that lists transactions names only those that user can
    see (X-R47b); None, a call without a caller, for the refusals that name none.

    As in the endpoint, nobody commits: the session closes on the error and drops whatever was
    not committed. What the service committed by itself is what "nothing persisted" then sees.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_events(data, session, current_user_id=current_user_id)
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


# ─────────────────────────────────────────────────────────────────────────────
# Deletions inside the upsert: ``delete_ids`` (lot E1b)
#
# The editor used to save in two requests, upserts then ``DELETE``: an edit could not take the
# key of an event deleted in the same save (I-10), and a refused upsert left the deletions done.
# Decided on 15/10 (16:20): ``FAEventUpsert.delete_ids``, per item, upsert mode only. In the
# item's transaction and BEFORE any check on its events, every id must be an event of that asset,
# manual or provider (else EVENT_NOT_DELETABLE, ``ids``: unknown, gone, or another asset's) that no
# transaction realises (else EVENT_IN_USE, ``events`` with ``linked_transactions``: counts, never
# transaction ids); then the rows are deleted and flushed, so the key checks and a later ``create``
# see the freed keys. Any refusal keeps the deleted events: all or nothing (decision 22). The
# result adds ``deleted_ids``, in request order. The separate ``DELETE /assets/events`` stays as it
# is (pinned above). Provider events are deletable since the correction of 15/10 17:49: the 1.2
# editor deleted them through that ``DELETE``, and the next sync writes them back.
#
# Before E1b ``delete_ids`` is an unknown field: the schema tests fail on it, and the database
# tests fail where ``_item(..., delete_ids=...)`` validates the request. Against the first cure
# (manual events only), the two provider tests are red: their provider id is EVENT_NOT_DELETABLE.
# ─────────────────────────────────────────────────────────────────────────────


def _results(result) -> list:
    """The per-item results, in request order: the only way to tell two items on one asset apart."""
    return list(result["results"] if isinstance(result, dict) else result.results)


def _not_an_unknown_field(exc: ValidationError) -> None:
    """The refusal is the new rule, not today's "unknown field ``delete_ids``" (extra_forbidden)."""
    assert not [err for err in exc.errors() if err["type"] == "extra_forbidden"], exc.errors()


def test_an_upsert_item_carries_no_deletions_by_default():
    """``delete_ids`` defaults to empty. Before: no such field (reads as None)."""
    item = FAEventUpsert.model_validate({"asset_id": 1, "events": [_ev(0, "DIVIDEND", "1.00")]})
    assert getattr(item, "delete_ids", None) == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"asset_id": 1, "delete_ids": [5, 3]}, id="no-events"),
        pytest.param({"asset_id": 1, "events": [], "delete_ids": [5, 3]}, id="empty-events"),
    ],
)
def test_an_item_may_carry_only_deletions(payload):
    """An item that only deletes is valid, its ids kept in request order. Before: ValidationError."""
    item = FAEventUpsert.model_validate(payload)
    assert list(item.delete_ids) == [5, 3]
    assert list(item.events or []) == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"asset_id": 1}, id="no-events"),
        pytest.param({"asset_id": 1, "events": []}, id="empty-events"),
    ],
)
def test_guard_an_item_with_no_events_and_no_deletions_is_still_refused(payload):
    """GUARD (green before E1b too): an item that writes nothing is malformed."""
    with pytest.raises(ValidationError):
        FAEventUpsert.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"asset_id": 1, "delete_ids": []}, id="empty-deletions"),
        pytest.param({"asset_id": 1, "events": [], "delete_ids": []}, id="empty-both"),
    ],
)
def test_an_item_with_empty_deletions_and_no_events_is_refused(payload):
    """Neither events nor deletions: a 422. Before: refused too, but for the unknown field ``delete_ids``."""
    with pytest.raises(ValidationError) as raised:
        FAEventUpsert.model_validate(payload)
    _not_an_unknown_field(raised.value)


def test_deletions_are_refused_in_a_create_item():
    """«+ New event» only creates: a create item deleting events is malformed. Before: the field is unknown."""
    with pytest.raises(ValidationError) as raised:
        FAEventUpsert.model_validate({"asset_id": 1, "mode": "create", "events": [_ev(0, "DIVIDEND", "1.00")], "delete_ids": [5]})
    _not_an_unknown_field(raised.value)


def test_an_id_both_deleted_and_edited_in_one_item_is_refused():
    """An event cannot be edited and deleted at once. Before: the field is unknown."""
    with pytest.raises(ValidationError) as raised:
        FAEventUpsert.model_validate({"asset_id": 1, "events": [_ev(0, "DIVIDEND", "1.00", event_id=5)], "delete_ids": [5]})
    _not_an_unknown_field(raised.value)


def test_the_upsert_result_carries_the_deleted_ids():
    """``FAEventUpsertResult.deleted_ids`` exists, in the order given. Before: an unknown field."""
    result = FAEventUpsertResult.model_validate({"asset_id": 1, "count": 0, "message": "Deleted 2 events", "event_ids": [], "deleted_ids": [7, 3]})
    assert result.deleted_ids == [7, 3]


@pytest.mark.asyncio
async def test_one_item_deletes_an_event_and_moves_another_onto_its_key(owned):
    """I-10 inside one request: B, edited by id, takes the (date, type) the deletion of A frees.

    A = (D1, DIVIDEND), B = (D2, DIVIDEND), both manual. One item: ``delete_ids=[A]`` and B moved
    to D1. Before E1b: ``delete_ids`` is unknown; through two requests the move came first and was
    refused (EVENT_KEY_CONFLICT) while A still held D1.
    Contract: A gone, B on D1 under its own id; ``deleted_ids == [A]``, ``event_ids == [B]``.
    """
    a_id = await _add_manual(owned.asset_id, 110, AssetEventType.DIVIDEND, "1.00", notes="A")
    b_id = await _add_manual(owned.asset_id, 111, AssetEventType.DIVIDEND, "2.00", notes="B")
    request = [_item(owned.asset_id, [_ev(110, "DIVIDEND", "2.50", event_id=b_id, notes="B moved")], delete_ids=[a_id])]

    result = await _upsert(request)

    row = _item_result(result, owned.asset_id)
    assert _field(row, "deleted_ids") == [a_id]
    assert _field(row, "event_ids") == [b_id]
    assert [(r.id, r.date, r.type, r.value, r.notes) for r in await _rows(owned.asset_id)] == [(b_id, _day(110), AssetEventType.DIVIDEND, Decimal("2.50"), "B moved")]


@pytest.mark.asyncio
async def test_an_item_of_deletions_only_deletes_them_and_names_them_in_request_order(owned):
    """An item may only delete. ``deleted_ids`` follows the request, not the ids' order.

    Before E1b: ``delete_ids`` is unknown (and an item needs events).
    """
    a_id = await _add_manual(owned.asset_id, 115, AssetEventType.DIVIDEND, "1.00")
    b_id = await _add_manual(owned.asset_id, 116, AssetEventType.INTEREST, "0.50")
    assert a_id < b_id
    request = [FAEventUpsert.model_validate({"asset_id": owned.asset_id, "delete_ids": [b_id, a_id]})]

    result = await _upsert(request)

    row = _item_result(result, owned.asset_id)
    assert _field(row, "deleted_ids") == [b_id, a_id]
    assert _field(row, "event_ids") == []
    assert await _snapshot(owned) == {}


@pytest.mark.asyncio
async def test_an_id_that_is_not_an_event_of_the_asset_is_not_deletable(owned):
    """Only events of the item's asset can be deleted; an id that is not there is not ignored.

    delete_ids: the asset's own event (deletable), an unknown id (never there, or gone), and an
    event of another asset.
    Before E1b: ``delete_ids`` is unknown.
    Contract: EVENT_NOT_DELETABLE, ``details`` {"asset_id", "item_index", "ids": the two refused};
    nothing deleted, the deletable one included.
    """
    own_id = await _add_manual(owned.asset_id, 120, AssetEventType.DIVIDEND, "1.00")
    foreign_id = await _add_manual(owned.other_asset_id, 120, AssetEventType.DIVIDEND, "1.00")
    unknown_id = await _unknown_event_id()
    before = await _snapshot(owned)

    refused = await _upsert_refused([_item(owned.asset_id, [], delete_ids=[own_id, unknown_id, foreign_id])])

    assert refused.error_code == "EVENT_NOT_DELETABLE"
    assert await _snapshot(owned) == before
    details = _plain(refused.details)
    assert {**details, "ids": sorted(details.get("ids") or [])} == {"asset_id": owned.asset_id, "item_index": 0, "ids": sorted([unknown_id, foreign_id])}


@pytest.mark.asyncio
async def test_a_provider_event_of_the_asset_is_deleted_like_a_manual_one(owned):
    """``delete_ids`` takes any event of the item's asset, manual or provider (correction of 15/10 17:49).

    The 1.2 editor deleted a provider event through ``DELETE /assets/events``, which still allows it;
    the next sync writes it back. P (provider), M1 and M2 (manual); one item deletes P and M1.
    Before the correction: EVENT_NOT_DELETABLE naming P, nothing deleted.
    Contract: ``deleted_ids == [P, M1]`` (request order), ``event_ids == []``; only M2 left.
    """
    provider_id = await _add_provider(owned, 121, AssetEventType.DIVIDEND, "1.50")
    deleted_manual_id = await _add_manual(owned.asset_id, 122, AssetEventType.DIVIDEND, "1.00")
    kept_manual_id = await _add_manual(owned.asset_id, 123, AssetEventType.INTEREST, "0.50")

    result = await _upsert([_item(owned.asset_id, [], delete_ids=[provider_id, deleted_manual_id])])

    row = _item_result(result, owned.asset_id)
    assert _field(row, "deleted_ids") == [provider_id, deleted_manual_id]
    assert _field(row, "event_ids") == []
    assert [r.id for r in await _rows(owned.asset_id)] == [kept_manual_id]


@pytest.mark.asyncio
async def test_a_provider_event_in_use_is_not_deleted(owned):
    """A provider event a transaction realises is in use, like a manual one: EVENT_IN_USE.

    Before the correction: EVENT_NOT_DELETABLE (the provider id is refused before its links are read).
    Contract: EVENT_IN_USE, ``details`` {"asset_id", "item_index": 0, "events": [{"id": P, "date",
    "type", "linked_transactions": 1}]}; nothing deleted.
    """
    provider_id = await _add_provider(owned, 124, AssetEventType.DIVIDEND, "1.50")
    await _link_tx(owned, provider_id, 124)
    before = await _snapshot(owned)

    refused = await _upsert_refused([_item(owned.asset_id, [], delete_ids=[provider_id])])

    assert refused.error_code == "EVENT_IN_USE"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {
        "asset_id": owned.asset_id,
        "item_index": 0,
        "events": [{"id": provider_id, "date": _day(124).isoformat(), "type": "DIVIDEND", "linked_transactions": 1}],
    }


@pytest.mark.asyncio
async def test_an_event_in_use_is_not_deleted_and_nothing_of_the_request_is_saved(owned):
    """An event a transaction realises cannot go; the whole request is refused (decision 22).

    Item 0 (other asset) adds an event. Item 1 deletes D (free) and L (realised by two
    transactions) and edits E.
    Before E1b: ``delete_ids`` is unknown; the separate DELETE answers ``in_use`` for L per row
    and deletes D anyway.
    Contract: EVENT_IN_USE, ``details`` {"asset_id", "item_index": 1, "events": [{"id", "date",
    "type", "linked_transactions": 2}]} — counts only, no transaction ids; nothing saved.
    """
    free_id = await _add_manual(owned.asset_id, 125, AssetEventType.DIVIDEND, "1.00")
    linked_id = await _add_manual(owned.asset_id, 126, AssetEventType.DIVIDEND, "1.00")
    edited_id = await _add_manual(owned.asset_id, 127, AssetEventType.INTEREST, "0.50")
    await _link_tx(owned, linked_id, 126)
    await _link_tx(owned, linked_id, 126)
    before = await _snapshot(owned)
    request = [
        _item(owned.other_asset_id, [_ev(125, "DIVIDEND", "3.00")]),
        _item(owned.asset_id, [_ev(127, "INTEREST", "0.75", event_id=edited_id)], delete_ids=[free_id, linked_id]),
    ]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_IN_USE"
    assert await _snapshot(owned) == before
    assert _plain(refused.details) == {
        "asset_id": owned.asset_id,
        "item_index": 1,
        "events": [{"id": linked_id, "date": _day(126).isoformat(), "type": "DIVIDEND", "linked_transactions": 2}],
    }


@pytest.mark.asyncio
async def test_the_deletions_of_an_item_are_checked_before_its_events(owned):
    """An undeletable id is the refusal, even when an event of the same item is wrong as well.

    Before E1b: ``delete_ids`` is unknown.
    Contract: EVENT_NOT_DELETABLE, not EVENT_CURRENCY_MISMATCH; nothing saved.
    """
    unknown_id = await _unknown_event_id()
    before = await _snapshot(owned)

    refused = await _upsert_refused([_item(owned.asset_id, [_ev(130, "DIVIDEND", "1.00", currency="EUR")], delete_ids=[unknown_id])])

    assert refused.error_code == "EVENT_NOT_DELETABLE"
    assert await _snapshot(owned) == before


@pytest.mark.asyncio
async def test_a_currency_mismatch_keeps_the_events_its_item_deletes(owned):
    """All or nothing inside one item: a refused event leaves the deletion undone.

    Before E1b: ``delete_ids`` is unknown.
    Contract: EVENT_CURRENCY_MISMATCH naming item 0 and its event 0; A still stored.
    """
    a_id = await _add_manual(owned.asset_id, 135, AssetEventType.DIVIDEND, "1.00")
    before = await _snapshot(owned)

    refused = await _upsert_refused([_item(owned.asset_id, [_ev(136, "DIVIDEND", "1.00", currency="EUR")], delete_ids=[a_id])])

    assert refused.error_code == "EVENT_CURRENCY_MISMATCH"
    assert await _snapshot(owned) == before, f"event {a_id} was deleted although its item was refused"
    assert _plain(refused.details) == {
        "asset_id": owned.asset_id,
        "item_index": 0,
        "expected": "USD",
        "events": [{"event_index": 0, "date": _day(136).isoformat(), "type": "DIVIDEND", "currency": "EUR"}],
    }


@pytest.mark.asyncio
async def test_a_key_conflict_keeps_the_events_its_item_deletes(owned):
    """The key checks run after the deletion, and a conflict they find undoes it.

    A (D, INTEREST) is deleted; B moves onto (D', DIVIDEND), which C — kept — holds.
    Before E1b: ``delete_ids`` is unknown.
    Contract: EVENT_KEY_CONFLICT on (D', DIVIDEND); A, B and C as they were.
    """
    a_id = await _add_manual(owned.asset_id, 140, AssetEventType.INTEREST, "0.50")
    b_id = await _add_manual(owned.asset_id, 141, AssetEventType.DIVIDEND, "1.00")
    await _add_manual(owned.asset_id, 142, AssetEventType.DIVIDEND, "2.00")
    before = await _snapshot(owned)

    refused = await _upsert_refused([_item(owned.asset_id, [_ev(142, "DIVIDEND", "1.00", event_id=b_id)], delete_ids=[a_id])])

    assert refused.error_code == "EVENT_KEY_CONFLICT"
    assert await _snapshot(owned) == before, f"event {a_id} was deleted although its item was refused"
    assert _plain(refused.details) == {"asset_id": owned.asset_id, "item_index": 0, "date": _day(142).isoformat(), "type": "DIVIDEND"}


@pytest.mark.asyncio
async def test_a_refused_later_item_keeps_the_events_an_earlier_item_deletes(owned):
    """All or nothing across items: item 1 refused, item 0's deletion undone.

    Before E1b: ``delete_ids`` is unknown.
    Contract: EVENT_CURRENCY_MISMATCH naming item 1; A still stored.
    """
    a_id = await _add_manual(owned.asset_id, 145, AssetEventType.DIVIDEND, "1.00")
    before = await _snapshot(owned)
    request = [
        _item(owned.asset_id, [], delete_ids=[a_id]),
        _item(owned.other_asset_id, [_ev(146, "DIVIDEND", "1.00", currency="EUR")]),
    ]

    refused = await _upsert_refused(request)

    assert refused.error_code == "EVENT_CURRENCY_MISMATCH"
    assert _plain(refused.details)["item_index"] == 1
    assert await _snapshot(owned) == before, f"event {a_id} was deleted although the request was refused"


@pytest.mark.asyncio
async def test_a_create_item_sees_the_key_an_earlier_item_freed(owned):
    """The deletions are flushed before the next item is checked: a create may take the freed key.

    Item 0 (upsert) deletes A = (D, DIVIDEND); item 1 (create) adds a DIVIDEND on D.
    Before E1b: ``delete_ids`` is unknown.
    Contract: no EVENT_EXISTS; A gone, one new row on D; per item, in request order, item 0
    ``deleted_ids == [A]`` and item 1 ``event_ids == [the new row]``.
    """
    a_id = await _add_manual(owned.asset_id, 150, AssetEventType.DIVIDEND, "1.00")
    request = [
        _item(owned.asset_id, [], delete_ids=[a_id]),
        _item(owned.asset_id, [_ev(150, "DIVIDEND", "1.20", notes="created")], mode="create"),
    ]

    result = await _upsert(request)

    new_id = await _row_id(owned.asset_id, 150, AssetEventType.DIVIDEND)
    assert new_id != a_id
    first, second = _results(result)
    assert (_field(first, "deleted_ids"), _field(second, "event_ids")) == ([a_id], [new_id])
    assert [(r.id, r.notes) for r in await _rows(owned.asset_id)] == [(new_id, "created")]


# ─────────────────────────────────────────────────────────────────────────────
# Retyping a SPLIT whose incoming adjustments have no cost (workstream J, lot CP-14a, P-10,
# developer decision 27 option A)
#
# An ADJUSTMENT +q linked to a SPLIT (``Transaction.asset_event_id``) and saved in Auto stores no cost:
# while the event is a SPLIT, the row only rescales the pool. Once the event is retyped (to a
# PRICE_ADJUSTMENT, say) the row is no longer a split rescale but an acquisition of UNKNOWN cost:
# MISSING_COST_BASIS on the Dashboard and in the lots. So ``_apply_manual_event_edits`` refuses an edit
# whose STORED row is a SPLIT and whose NEW type is not, when at least one transaction linked to that
# event is an ADJUSTMENT with quantity > 0 and ``cost_basis_override IS NULL``. The check runs before
# the first write: the request writes nothing. Code EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST; ``details``
# {"event_id", "date" of the stored SPLIT, "transaction_ids": those adjustments the caller can see, sorted,
# "hidden_transactions_count": the others}, for the first such edit in request order (``_write_manual_item``
# adds ``asset_id`` and ``item_index``, as for every refusal). Without a caller none is named (X-R47b, fail
# closed: ``transaction_ids`` [], all of them counted hidden), so the refusal tests answer the module's
# holder (``holder_id``, an OWNER access to the unit's broker), who sees every adjustment written here:
# they keep pinning WHICH transactions, none hidden.
#
# Allowed, before and after P-10 (the GUARD tests): an incoming adjustment with a known cost, 0
# included; a reverse split's outgoing row, which never carries a cost and, retyped, becomes a plain
# reduction at average cost (test A4 of test_portfolio_wac.py); a SPLIT nothing links to; an edit that
# keeps the type SPLIT.
#
# Before P-10 every retype is accepted: the reds fail in ``_upsert_refused`` («accepted a request it
# must refuse») with the retype committed, which ``owned`` wipes.
# ─────────────────────────────────────────────────────────────────────────────


async def _add_split(owned: _Owned, offset: int, ratio: str, *, notes: str | None = None) -> int:
    """A manual SPLIT of this unit's asset: its value is the ratio ("2" a 2-for-1, "0.5" a reverse 1-for-2)."""
    return await _add_manual(owned.asset_id, offset, AssetEventType.SPLIT, ratio, notes=notes)


async def _link_adjustment(owned: _Owned, split_id: int, offset: int, quantity: str, *, cost: str | None = None) -> int:
    """An ADJUSTMENT of ``quantity`` units linked to ``split_id``; ``cost`` per unit in USD, None for none (Auto's way)."""
    return await _link_tx(owned, split_id, offset, kind=TransactionType.ADJUSTMENT, quantity=quantity, cost=cost)


def _split_refusal(owned: _Owned, split_id: int, offset: int, transaction_ids: list[int]) -> dict:
    """The ``details`` of EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST for a one-item request asked by the holder, as ``_plain``
    renders them: every adjustment named, none hidden."""
    return {"asset_id": owned.asset_id, "item_index": 0, "event_id": split_id, "date": _day(offset).isoformat(), "transaction_ids": sorted(transaction_ids), "hidden_transactions_count": 0}


@pytest.mark.asyncio
async def test_retyping_a_split_with_an_incoming_adjustment_without_cost_is_refused(owned):
    """A forward SPLIT and an ADJUSTMENT +10 linked to it with no cost: the SPLIT cannot become a PRICE_ADJUSTMENT.

    Before: accepted — the event becomes a PRICE_ADJUSTMENT, and the +10 an acquisition of unknown cost.
    Contract, asked by the holder: EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST; details {"asset_id", "item_index": 0,
    "event_id": the SPLIT, "date": its date, "transaction_ids": [the ADJUSTMENT], "hidden_transactions_count": 0}; the
    event (type, value, date, notes, updated_at) and the transaction as they were.
    """
    split_id = await _add_split(owned, 200, "2", notes="2-for-1")
    adjustment_id = await _link_adjustment(owned, split_id, 200, "10")
    events_before = await _snapshot(owned, stamped=True)
    transactions_before = await _tx_snapshot(owned)

    refused = await _upsert_refused([_item(owned.asset_id, [_ev(200, "PRICE_ADJUSTMENT", "2", event_id=split_id, notes="relabelled")])], current_user_id=owned.holder_id)

    assert refused.error_code == "EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST", (refused.error_code, refused.details)
    assert _plain(refused.details) == _split_refusal(owned, split_id, 200, [adjustment_id])
    assert await _snapshot(owned, stamped=True) == events_before, f"SPLIT {split_id} was written although its retype was refused"
    assert await _tx_snapshot(owned) == transactions_before, f"ADJUSTMENT {adjustment_id} changed although the retype was refused"


@pytest.mark.asyncio
async def test_a_refused_split_retype_writes_nothing_of_its_item(owned):
    """All or nothing: the valid edit before the refused retype, in the same item, is not written either.

    Item: 0 changes a DIVIDEND's amount and notes (valid on its own), 1 retypes a SPLIT that has an incoming
    ADJUSTMENT without cost.
    Before: both edits accepted and written.
    Contract, asked by the holder: EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST naming the SPLIT and its ADJUSTMENT, none
    hidden; neither event written (updated_at included); the transaction as it was.
    """
    dividend_id = await _add_manual(owned.asset_id, 210, AssetEventType.DIVIDEND, "1.00", notes="before")
    split_id = await _add_split(owned, 211, "2")
    adjustment_id = await _link_adjustment(owned, split_id, 211, "10")
    events_before = await _snapshot(owned, stamped=True)
    transactions_before = await _tx_snapshot(owned)
    request = [_item(owned.asset_id, [_ev(210, "DIVIDEND", "1.25", event_id=dividend_id, notes="after"), _ev(211, "PRICE_ADJUSTMENT", "2", event_id=split_id)])]

    refused = await _upsert_refused(request, current_user_id=owned.holder_id)

    assert refused.error_code == "EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST", (refused.error_code, refused.details)
    assert _plain(refused.details) == _split_refusal(owned, split_id, 211, [adjustment_id])
    assert await _snapshot(owned, stamped=True) == events_before, f"DIVIDEND {dividend_id} or SPLIT {split_id} was written although the item was refused"
    assert await _tx_snapshot(owned) == transactions_before


@pytest.mark.asyncio
async def test_a_refused_split_retype_names_the_first_offending_edit_and_only_its_costless_incoming_adjustments(owned):
    """The details follow the contract to the letter: which SPLIT, which date, which transactions.

    Two SPLITs, A then B (B has the higher id); the item retypes B (and moves it two days later), then A.
    Linked to B: two ADJUSTMENTs in without cost, the first created dated a day after the second (their dates do not
    give the order of their ids), one in with a cost of 0 and one out without cost. Linked to A: one ADJUSTMENT in
    without cost.
    Before: accepted, both SPLITs retyped.
    Contract, asked by the holder: details name B, the first offending edit in request order, with B's STORED date,
    and only B's two costless incoming ADJUSTMENTs, sorted by id, none hidden; nothing written.
    """
    split_a = await _add_split(owned, 220, "2")
    split_b = await _add_split(owned, 222, "3")
    assert split_a < split_b, "precondition: B is the newer row, so request order and id order disagree"
    await _link_adjustment(owned, split_a, 220, "10")
    later_costless = await _link_adjustment(owned, split_b, 223, "20")
    earlier_costless = await _link_adjustment(owned, split_b, 222, "5")
    await _link_adjustment(owned, split_b, 222, "7", cost="0")
    await _link_adjustment(owned, split_b, 222, "-4")
    events_before = await _snapshot(owned, stamped=True)
    transactions_before = await _tx_snapshot(owned)
    request = [_item(owned.asset_id, [_ev(224, "PRICE_ADJUSTMENT", "3", event_id=split_b), _ev(220, "PRICE_ADJUSTMENT", "2", event_id=split_a)])]

    refused = await _upsert_refused(request, current_user_id=owned.holder_id)

    assert refused.error_code == "EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST", (refused.error_code, refused.details)
    assert _plain(refused.details) == _split_refusal(owned, split_b, 222, [later_costless, earlier_costless])
    assert await _snapshot(owned, stamped=True) == events_before
    assert await _tx_snapshot(owned) == transactions_before


@pytest.mark.asyncio
@pytest.mark.parametrize("cost", [pytest.param("12.5", id="cost"), pytest.param("0", id="zero-cost")])
async def test_guard_a_split_whose_incoming_adjustment_has_a_cost_can_be_retyped(owned, cost):
    """GUARD (green before and after P-10): a known cost — 0 is one — leaves nothing unknown after the retype.

    Contract: accepted; the event, under its id, is a PRICE_ADJUSTMENT; the ADJUSTMENT still linked, its cost as it was.
    """
    split_id = await _add_split(owned, 230, "2")
    await _link_adjustment(owned, split_id, 230, "10", cost=cost)
    transactions_before = await _tx_snapshot(owned)

    await _upsert([_item(owned.asset_id, [_ev(230, "PRICE_ADJUSTMENT", "2", event_id=split_id)])])

    assert [(row.id, row.date, row.type, row.value) for row in await _rows(owned.asset_id)] == [(split_id, _day(230), AssetEventType.PRICE_ADJUSTMENT, Decimal("2"))]
    assert await _tx_snapshot(owned) == transactions_before


@pytest.mark.asyncio
async def test_guard_a_reverse_split_whose_outgoing_adjustment_has_no_cost_can_be_retyped(owned):
    """GUARD (green before and after P-10): a reverse split's −q row never carries a cost, and retyped it becomes a plain
    reduction at average cost — intended (test A4 of test_portfolio_wac.py).

    Contract: accepted; the event, under its id, is a PRICE_ADJUSTMENT; the ADJUSTMENT as it was.
    """
    split_id = await _add_split(owned, 240, "0.5")
    await _link_adjustment(owned, split_id, 240, "-10")
    transactions_before = await _tx_snapshot(owned)

    await _upsert([_item(owned.asset_id, [_ev(240, "PRICE_ADJUSTMENT", "0.5", event_id=split_id)])])

    assert [(row.id, row.date, row.type, row.value) for row in await _rows(owned.asset_id)] == [(split_id, _day(240), AssetEventType.PRICE_ADJUSTMENT, Decimal("0.5"))]
    assert await _tx_snapshot(owned) == transactions_before


@pytest.mark.asyncio
async def test_guard_a_split_nothing_links_to_can_be_retyped(owned):
    """GUARD (green before and after P-10): without linked rows there is no cost to lose.

    Contract: accepted; the event, under its id, is a PRICE_ADJUSTMENT.
    """
    split_id = await _add_split(owned, 245, "2")

    await _upsert([_item(owned.asset_id, [_ev(245, "PRICE_ADJUSTMENT", "2", event_id=split_id)])])

    assert [(row.id, row.date, row.type, row.value) for row in await _rows(owned.asset_id)] == [(split_id, _day(245), AssetEventType.PRICE_ADJUSTMENT, Decimal("2"))]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offset", "ratio", "notes"),
    [
        pytest.param(250, "3", None, id="ratio"),
        pytest.param(250, "2", "ratio checked", id="notes"),
        pytest.param(251, "2", None, id="date"),
    ],
)
async def test_guard_editing_a_split_without_changing_its_type_is_allowed(owned, offset, ratio, notes):
    """GUARD (green before and after P-10): an edit that keeps the type SPLIT — its ratio, its notes, even its date —
    is allowed with an incoming ADJUSTMENT without cost linked: the row stays a split rescale.

    Contract: accepted; the SPLIT, under its id, holds the sent values; the ADJUSTMENT as it was.
    """
    split_id = await _add_split(owned, 250, "2")
    await _link_adjustment(owned, split_id, 250, "10")
    transactions_before = await _tx_snapshot(owned)

    await _upsert([_item(owned.asset_id, [_ev(offset, "SPLIT", ratio, event_id=split_id, notes=notes)])])

    assert [(row.id, row.date, row.type, row.value, row.notes) for row in await _rows(owned.asset_id)] == [(split_id, _day(offset), AssetEventType.SPLIT, Decimal(ratio), notes)]
    assert await _tx_snapshot(owned) == transactions_before
