"""X-R47 (workstream X): a SPLIT asset event's ratio is checked when it is written; and R13-SEC7 with X-R47b: the P-10
refusal shows only the caller's transactions, and none without a caller.

Measured before the cure: a SPLIT's ratio is its ``value.amount`` (``FAAssetEventPoint.value``), and nothing checks it on
the way in. ``FAEventUpsert`` (``POST /assets/events``) accepts a SPLIT of 0 or below, and ``bulk_upsert_events`` writes
it in every way a manual event is written: created (``mode`` "upsert" or "create"), upserted on the key of a stored
manual SPLIT, edited in place by ``id``, or turned into a SPLIT by such an edit. A provider refresh
(``_upsert_asset_events``) writes one as it comes. Stored, nothing shows yet; as soon as a transaction links that SPLIT,
the portfolio engine raises ``ValueError("SPLIT AssetEvent … must have a positive finite ratio")``
(``financial_math/portfolio/engine.py``) and the Dashboard report answers 500.

The cure's contract:

* a manual SPLIT whose ratio is not valid — 0 or below: ``financial_math.splits.is_valid_split_ratio``, the engine's
  rule — is refused before anything of the request is written, in each of those ways: ``AssetSourceError``
  ``EVENT_INVALID_SPLIT_RATIO``, its ``details`` naming the item (``asset_id``, ``item_index``, as every refusal of
  ``bulk_upsert_events``) and, in ``events``, every offending event in request order, each with its ``event_index``,
  ``date`` and ``type`` (as ``EVENT_TOO_MANY_DIGITS`` does). All or nothing: the valid events, edits and deletions of
  the request are not written either, and an edited row keeps its stored values;
* ``POST /assets/events`` answers it 400 (``_REFUSAL_STATUS``), ``params.events`` giving each SPLIT's ``ratio`` as sent,
  a string: what the event editor's message quotes (the X-R47 case of ``eventSaveError.test.ts``);
* a provider's SPLIT whose ratio is not valid is dropped by ``_upsert_asset_events`` — not inserted, and a stored SPLIT
  on its key keeps its ratio — the provider's other events are written, nothing raises, and one warning names it: its
  date, the word split and the asset;
* guards, green before and after: a SPLIT of 2, 0.5 (a reverse split), 1.5 or 0.000001 is stored, manual in every way
  or from a provider, and a provider's valid SPLIT is not logged; another type of value 0 is not concerned, nor a SPLIT
  edited into a DIVIDEND of 0: the rule reads the type an event ends with.

The ratios refused are 0, -2 and -0.000001; -0.000001 and 0.000001 are derived: one unit of the last decimal place
``AssetEvent.value`` keeps (6), each side of 0. Every ratio here fits the column (a guard checks it), so a refusal or a
drop seen here is about the ratio alone. A NaN or infinite ratio is refused earlier, with ``EVENT_TOO_MANY_DIGITS``
(W-B58): not this lot's; a ratio already stored is MF-D4's.

X-R47's layer fix (rule d of ``test_layer_boundaries.py``: ``AssetEventType.SPLIT`` is named only in the split loader):
the event store asks ``financial_math.splits.is_split_event_type`` whether an event is a SPLIT — True for text that
reads SPLIT once stripped and upper-cased, an ``AssetEventType`` member included (a StrEnum), False for anything else,
never raising — and the ``type`` in EVENT_INVALID_SPLIT_RATIO's details is the event's own, normalised: still "SPLIT".
Its tests read the name when they run, so before the fix they alone are red and the rest of the unit runs.

R13-SEC7 (E's security review of 17/10, LOW): J's P-10 refusal, ``EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST``
(``_reject_split_retype_without_costs``), names in ``details["transaction_ids"]`` every costless incoming ADJUSTMENT
linked to the SPLIT, whoever's broker it is on, and any user can trigger it on an asset, which is global: against the
file's own rule (``_delete_item_events`` answers counts, never transaction ids: they may belong to other users). The
cure's contract: ``bulk_upsert_events(data, session, *, current_user_id=None)``, and ``POST /assets/events`` passes the
caller. With a ``current_user_id``, ``transaction_ids`` keeps the transactions that user can see — a ``BrokerUserAccess``
row for the transaction's broker, as ``delete_events_bulk`` decides ``accessible_transactions`` — sorted, and a new key,
``hidden_transactions_count``, counts the others; the message keeps the total count only. X-R47b (E's security review
of 5f68a8db0: fail closed, where R13-SEC7's cure still named every id without a caller): the details always carry both
keys, and without a ``current_user_id`` no transaction is named — ``transaction_ids`` is [] and
``hidden_transactions_count`` counts them all — while the route always passes its caller (``_current_user.id``, no
fallback). The case: a SPLIT with a costless incoming ADJUSTMENT on each of two brokers of the unit's own, user A
holding an access to broker A alone, user B to broker B.

A refusal is looked for as the router meets it: nobody commits after a refused call, the session just closes, so
"nothing written" sees exactly what the service committed by itself — read with raw SQL on a fresh connection, every
column and ``updated_at`` included. A call that raises today where the contract refuses or drops fails its test naming
the exception, never as an error. The warning is looked for in a ``structlog`` capture that a barrier event, sent
through ``event_store``'s own logger, proves live. The route tests post to ``POST /assets/events`` in process: the
events router mounted as the app mounts it, on an app of the test's own, ``get_current_user`` overridden there to the
unit's user, the session the real dependency opens; the answer read as the client reads it, JSON. Each red says what the
user faces before its lot's cure («Red today» is that state, for X-R47, R13-SEC7 and X-R47b alike); a guard passes
before and after it.

Isolation: WRITE-SCOPED, the services default (as ``asset-digit-limits``). Every row is this unit's own: two EUR STOCK
assets created under a unique name, the first assigned to a provider code of the unit's own that no provider has (a
provenance tag: nothing is fetched); two users and two brokers under the same unique marker, each user holding an access
to one broker; and only the events of those assets and the transactions on those brokers are written, read and wiped,
by asset and broker id. Nothing here counts or reads a row it did not write.
"""

import asyncio
import importlib
import inspect
import re
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

import pytest
import pytest_asyncio
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

import httpx
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import bindparam, delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.assets import events as events_api
from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    Broker,
    BrokerUserAccess,
    ProviderInputType,
    Transaction,
    TransactionType,
    User,
    UserRole,
)
from backend.app.db.precision import decimal_limit_issue, get_model_column_precision, integer_digits_issue
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.events import FAEventUpsert
from backend.app.services.assets import event_store
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.event_store import EventStoreOperations
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.financial_math.splits import costless_incoming_split_adjustments, is_valid_split_ratio
from backend.test_scripts.test_utils import unique_id

# A window far from the mock dataset and from the other event units (1991-1992, 1994-1995). Rows are scoped by asset
# anyway: the dates only keep the failure output readable.
BASE_DATE = date(1990, 9, 3)


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


# One unit of the last decimal place AssetEvent.value keeps (6 places: 0.000001), each side of 0.
_SCALE = get_model_column_precision(AssetEvent, "value")[1]
_ONE_UNIT = Decimal(1).scaleb(-_SCALE)

#: The ratios the contract refuses, 0 and below, as (value, test id).
_INVALID = [("0", "0"), ("-2", "minus-2"), (str(-_ONE_UNIT), f"derived-minus-{_ONE_UNIT}")]
#: The ratios it accepts: a 2-for-1, a reverse 1-for-2, a 3-for-2, and the smallest the column keeps.
_VALID = [("2", "2"), ("0.5", "0.5-reverse"), ("1.5", "1.5"), (str(_ONE_UNIT), f"derived-{_ONE_UNIT}")]
_INVALID_RATIOS = [pytest.param(value, id=name) for value, name in _INVALID]
_VALID_RATIOS = [pytest.param(value, id=name) for value, name in _VALID]
_OTHER_TYPES = [pytest.param(kind.value, id=kind.value) for kind in AssetEventType if kind is not AssetEventType.SPLIT]

#: An event sent through event_store.py's own logger inside every capture of this unit, then looked for.
_XR47_BARRIER = "X-R47 capture barrier"


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Owned:
    """What this unit created: the two EUR STOCK assets — the one the stories are about, assigned to a provider code of
    the unit's own, and another one saved in the same request — and that assignment; two users and two brokers, user A
    holding an access to broker A alone, user B to broker B alone."""

    asset_id: int
    other_asset_id: int
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


async def _wipe(owned: _Owned) -> None:
    """Drop the transactions on this unit's brokers (they RESTRICT the event they link to), then every event of its
    assets. Bulk deletes: no row is loaded."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(Transaction).where(Transaction.broker_id.in_(owned.broker_ids)))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)))
        await session.commit()


@pytest.fixture(scope="module")
def owned_module() -> _Owned:
    """The assets, the assignment, the users, the brokers and the accesses, under names no concurrent worker can repeat,
    dropped in FK-safe order in teardown with every event and transaction written against them. The provider code is no
    provider's: nothing is ever fetched for it."""
    marker = f"{unique_id('XR47')}_{uuid.uuid4().hex[:8]}"

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            split = Asset(display_name=f"X-R47 Split {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            other = Asset(display_name=f"X-R47 Other {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True)
            user_a = User(username=f"xr47a_{marker}".lower(), email=f"xr47a_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            user_b = User(username=f"xr47b_{marker}".lower(), email=f"xr47b_{marker}@example.test".lower(), hashed_password="not-a-real-hash")
            broker_a = Broker(name=f"X-R47 A {marker}")
            broker_b = Broker(name=f"X-R47 B {marker}")
            session.add_all([split, other, user_a, user_b, broker_a, broker_b])
            await session.commit()
            assignment = AssetProviderAssignment(asset_id=split.id, provider_code=f"xr47_{uuid.uuid4().hex[:12]}", identifier=f"XR47.{marker}", identifier_type=ProviderInputType.TICKER)
            access_a = BrokerUserAccess(user_id=user_a.id, broker_id=broker_a.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            access_b = BrokerUserAccess(user_id=user_b.id, broker_id=broker_b.id, role=UserRole.OWNER, share_percentage=Decimal("1"))
            session.add_all([assignment, access_a, access_b])
            await session.commit()
            return _Owned(
                asset_id=split.id,
                other_asset_id=other.id,
                assignment_id=assignment.id,
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                broker_a_id=broker_a.id,
                broker_b_id=broker_b.id,
            )

    async def _drop(owned: _Owned) -> None:
        await _wipe(owned)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(BrokerUserAccess).where(or_(BrokerUserAccess.broker_id.in_(owned.broker_ids), BrokerUserAccess.user_id.in_(owned.user_ids))))
            await session.execute(delete(Broker).where(Broker.id.in_(owned.broker_ids)))
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.id == owned.assignment_id))
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


async def _seed(owned: _Owned, offset: int, kind: AssetEventType, amount: str, *, notes: str | None = None, provider: bool = False) -> int:
    """An event of the unit's asset written directly, as an earlier save left it — or a refresh, under the assignment, with
    ``provider`` — in EUR: its id."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        row = AssetEvent(asset_id=owned.asset_id, date=_day(offset), type=kind, value=Decimal(amount), currency="EUR", notes=notes, provider_assignment_id=owned.assignment_id if provider else None)
        session.add(row)
        await session.commit()
        return row.id


# --------------------------------------------------------------------------- #
# Reading back
# --------------------------------------------------------------------------- #

_RAW_EVENTS = text("SELECT id, asset_id, date, type, value, currency, provider_assignment_id, notes, updated_at FROM asset_events WHERE asset_id IN :asset_ids ORDER BY id").bindparams(bindparam("asset_ids", expanding=True))


async def _snapshot(owned: _Owned) -> dict[int, tuple]:
    """id -> (asset_id, date, type, value, currency, provider_assignment_id, notes, updated_at) of every event of this
    unit's assets: what is committed, read with raw SQL on a fresh connection. ``updated_at`` included: a write that puts
    every value back as it was still moves it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(_RAW_EVENTS, {"asset_ids": owned.asset_ids})).all()
    return {row[0]: tuple(row[1:]) for row in rows}


async def _rows(owned: _Owned) -> list[AssetEvent]:
    """Every event of this unit's assets through the ORM, lowest id first."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stmt = select(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)).order_by(AssetEvent.id)
        return list((await session.execute(stmt)).scalars().all())


def _describe(rows: list[AssetEvent]) -> list[str]:
    return [f"#{row.id} asset {row.asset_id} {row.type} {row.date.isoformat()}: {row.value} {row.currency}" + (" (provider)" if row.provider_assignment_id is not None else "") for row in rows]


# --------------------------------------------------------------------------- #
# Manual events: requests, refusals
# --------------------------------------------------------------------------- #


def _ev(offset: int, kind: str, amount: str, *, event_id: int | None = None, notes: str | None = None) -> dict:
    """One event of a manual upsert item, as the event editor sends it, in the asset's currency."""
    payload: dict = {"date": _day(offset).isoformat(), "type": kind, "value": {"code": "EUR", "amount": amount}}
    if event_id is not None:
        payload["id"] = event_id
    if notes is not None:
        payload["notes"] = notes
    return payload


def _item(asset_id: int, events: list[dict], *, mode: str = "upsert", delete_ids: list[int] | None = None) -> FAEventUpsert:
    """A manual upsert item, validated as the endpoint validates it. A refusal there fails the test, naming it: the
    endpoint would answer 422, without the contract's code and details."""
    payload: dict = {"asset_id": asset_id, "mode": mode, "events": events}
    if delete_ids:
        payload["delete_ids"] = delete_ids
    try:
        return FAEventUpsert.model_validate(payload)
    except ValidationError as exc:
        pytest.fail(f"the request schema refuses the item {payload}: POST /assets/events answers 422 {exc.errors()} (X-R47: the service refuses a SPLIT ratio of 0 or below, 400 EVENT_INVALID_SPLIT_RATIO naming each event, and accepts every other ratio)")


async def _upsert(data: list[FAEventUpsert], story: str) -> dict:
    """``POST /assets/events`` minus HTTP, for a request that must succeed (the service commits it); a refusal fails the
    test, naming it."""
    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            return await AssetSourceManager.bulk_upsert_events(data, session)
    except AssetSourceError as refusal:
        pytest.fail(f"{story} was refused: {refusal.error_code} {refusal.message} {refusal.details}")


async def _upsert_refused(owned: _Owned, data: list[FAEventUpsert], story: str) -> AssetSourceError:
    """``POST /assets/events`` minus HTTP, for a request that must be refused; any exception but the refusal fails the
    test, naming it (the endpoint answers 500 to it). As in the endpoint, nobody commits: the session closes on the
    error, so what the service committed by itself is what "nothing written" then sees."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_events(data, session)
        except AssetSourceError as refusal:
            return refusal
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            pytest.fail(f"{story} raised {exc!r} instead of an AssetSourceError: POST /assets/events answers 500")
    messages = [row["message"] for row in result["results"]]
    pytest.fail(f"{story} was accepted ({messages}) and reads back as {_describe(await _rows(owned))}, instead of being refused with EVENT_INVALID_SPLIT_RATIO (X-R47): once a transaction links that SPLIT, the Dashboard answers 500 (the portfolio engine's ValueError)")


def _assert_refused_for_the_ratio(refusal: AssetSourceError, story: str, *, asset_id: int, item_index: int, splits: list[tuple[int, int]]) -> None:
    """The refusal is ``EVENT_INVALID_SPLIT_RATIO``; its details name the item and, in ``events``, exactly the SPLITs given
    as (event_index, day offset), in request order, each with its date and type."""
    assert refusal.error_code == "EVENT_INVALID_SPLIT_RATIO", f"{story} was refused with {refusal.error_code} ({refusal.message}), not EVENT_INVALID_SPLIT_RATIO: {refusal.details}"
    details = refusal.details or {}
    item = (details.get("asset_id"), details.get("item_index"))
    assert item == (asset_id, item_index), f"the refusal of {story} names the item {item}: expected asset {asset_id} at index {item_index}, so the editor can point at it (decision 22): {details}"
    named = [(entry.get("event_index"), str(entry.get("date")), str(entry.get("type"))) for entry in details.get("events") or []]
    expected = [(event_index, _day(offset).isoformat(), "SPLIT") for event_index, offset in splits]
    assert named == expected, f"the refusal of {story} names the events {named} as (event_index, date, type): expected {expected}, one entry per SPLIT whose ratio is not valid, so the editor can point at each: {details}"


# --------------------------------------------------------------------------- #
# The route, in process
# --------------------------------------------------------------------------- #


async def _caller(user_id: int) -> User:
    """The user ``user_id`` as ``get_current_user`` hands it to a route: the row, loaded and detached."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await session.get(User, user_id)
    assert user is not None, f"barrier: the unit's user {user_id} is gone"
    return user


async def _post_events(user_id: int, items: list[dict]) -> httpx.Response:
    """``POST /assets/events`` in process, as the user ``user_id``: the events router mounted at ``/api/v1/assets`` as the
    app mounts it, on an app of the call's own — so ``get_current_user`` is overridden there, never on the shared app —
    with the session the real dependency opens on the lane's database. Nothing is mocked behind the route."""
    caller = await _caller(user_id)
    app = FastAPI()
    app.include_router(events_api.event_router, prefix="/api/v1/assets")
    app.dependency_overrides[get_current_user] = lambda: caller
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/v1/assets/events", json=items)


def _detail(response: httpx.Response) -> dict:
    """The ``detail`` of a refusal as the client reads it: {} when the body holds none (a 200, or a 500's text)."""
    try:
        body = response.json()
    except ValueError:
        return {}
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, dict) else {}


# --------------------------------------------------------------------------- #
# Provider events: the refresh's write, its log
# --------------------------------------------------------------------------- #


def _provider_event(offset: int, kind: str, amount: str) -> dict:
    """One event as a provider delivers it to a refresh (``FAHistoricalData.events``), in the asset's currency."""
    return {"date": _day(offset), "type": kind, "value": {"code": "EUR", "amount": amount}}


def _assert_the_capture_saw(captured: list[dict]) -> None:
    """Barrier: an event sent through event_store.py's own logger inside the capture is there, so a missing warning is a
    warning not logged, never a blind capture."""
    assert any(event.get("event") == _XR47_BARRIER for event in captured), f"barrier: the log capture saw no event of event_store.py's logger: {captured}"


async def _provider_upsert(owned: _Owned, events: list[dict], story: str) -> list[dict]:
    """What a refresh does with the events its provider delivered (``refresh.py``: ``_upsert_asset_events`` under the
    assignment, committed slice by slice), its log events captured: those events. An exception fails the test, naming it:
    the refresh would report «Event upsert failed» and keep none of the provider's events."""
    with capture_logs() as captured:
        event_store.logger.warning(_XR47_BARRIER)
        try:
            async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
                await EventStoreOperations._upsert_asset_events(session, owned.asset_id, events, owned.assignment_id, "EUR")
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story}: _upsert_asset_events raised {exc!r}: the refresh reports «Event upsert failed» and keeps none of the provider's events (X-R47: drop that SPLIT, write the others)")
    _assert_the_capture_saw(captured)
    return captured


def _text(value: object) -> str:
    """A log event as plain text — a date in its ISO form, an enum as its value, containers flattened — so what it names
    is found whatever form the logger was given it in."""
    if isinstance(value, dict):
        return " ".join(f"{key}={_text(item)}" for key, item in value.items())
    if isinstance(value, list | tuple | set):
        return " ".join(_text(item) for item in value)
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _split_warnings(captured: list[dict], offset: int) -> list[dict]:
    """The warnings, and worse, among ``captured`` that name the SPLIT of day ``offset`` — its date and the word split —
    whichever module logs them and whatever their text; the barrier left out."""
    day = _day(offset).isoformat()
    return [event for event in captured if event.get("log_level") in ("warning", "error", "critical") and event.get("event") != _XR47_BARRIER and day in _text(event) and "split" in _text(event).lower()]


def _names_the_asset(event: dict, asset_id: int) -> bool:
    """Whether a log event names asset ``asset_id``: its id as a whole number anywhere in the event, a field's value or the
    text. The digits of a date or of a ratio are no name."""
    return re.search(rf"(?<![\w.+-]){asset_id}(?![\w.+-])", _text(event)) is not None


def _assert_one_warning_names_the_split(captured: list[dict], owned: _Owned, offset: int, story: str) -> None:
    """One warning, or worse, names the dropped SPLIT of day ``offset``, and it names the asset."""
    warnings = _split_warnings(captured, offset)
    assert len(warnings) == 1, f"{story} logged {len(warnings)} warning(s) naming the SPLIT of {_day(offset)}: expected one, so the operator learns the provider's split was dropped (X-R47): {warnings}"
    assert _names_the_asset(warnings[0], owned.asset_id), f"{story}: the warning about the dropped SPLIT of {_day(offset)} does not name asset {owned.asset_id}, so the operator cannot tell whose split it was: {warnings[0]}"


# ─────────────────────────────────────────────────────────────────────────────
# Manual SPLITs whose ratio is not valid: refused, nothing of the request written
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _INVALID_RATIOS)
@pytest.mark.parametrize("mode", ["upsert", "create"])
async def test_a_new_manual_split_with_an_invalid_ratio_is_refused_and_nothing_is_written(owned, mode, ratio):
    """Red today: accepted, the SPLIT of ``ratio`` stored beside the dividend; once a transaction links it, the Dashboard
    answers 500.

    Contract (X-R47): ``EVENT_INVALID_SPLIT_RATIO``, naming item 0 of the asset and its event 1, the SPLIT (day 1);
    nothing written, the valid dividend of the same item (day 0) included.
    """
    before = await _snapshot(owned)
    data = [_item(owned.asset_id, [_ev(0, "DIVIDEND", "1.5"), _ev(1, "SPLIT", ratio)], mode=mode)]
    story = f"a new SPLIT of ratio {ratio} ({mode} mode) saved beside a dividend of 1.5 EUR"

    refusal = await _upsert_refused(owned, data, story)

    _assert_refused_for_the_ratio(refusal, story, asset_id=owned.asset_id, item_index=0, splits=[(1, 1)])
    after = await _snapshot(owned)
    assert after == before, f"{story} was refused, yet events were written: {_describe(await _rows(owned))}"


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _INVALID_RATIOS)
async def test_an_upsert_giving_a_stored_split_an_invalid_ratio_is_refused_and_the_split_keeps_its_ratio(owned, ratio):
    """Red today: accepted, the stored manual SPLIT of 2 updated in place on its key to ``ratio`` — the transactions
    already linked to it take the Dashboard down at once (500) — and the interest of the same item stored.

    Contract (X-R47): ``EVENT_INVALID_SPLIT_RATIO`` naming event 0, the SPLIT (day 10); the stored SPLIT keeps every
    column, ``updated_at`` included; the interest (day 11) is not written.
    """
    split_id = await _seed(owned, 10, AssetEventType.SPLIT, "2", notes="2-for-1")
    before = await _snapshot(owned)
    data = [_item(owned.asset_id, [_ev(10, "SPLIT", ratio), _ev(11, "INTEREST", "2.25")])]
    story = f"an upsert on the key of the SPLIT {split_id} of {_day(10)} (ratio 2) to ratio {ratio}, with an interest"

    refusal = await _upsert_refused(owned, data, story)

    _assert_refused_for_the_ratio(refusal, story, asset_id=owned.asset_id, item_index=0, splits=[(0, 10)])
    after = await _snapshot(owned)
    assert after == before, f"{story} was refused, yet it wrote: before {before}, after {after}"


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _INVALID_RATIOS)
async def test_an_edit_giving_a_split_an_invalid_ratio_is_refused_and_writes_nothing_of_its_item(owned, ratio):
    """Red today: accepted; the SPLIT of 2, edited by id, holds ``ratio`` — the transactions already linked to it take the
    Dashboard down at once (500) — the new dividend is stored and the interest deleted.

    Contract (X-R47): ``EVENT_INVALID_SPLIT_RATIO`` naming event 1, the edit (day 20); all or nothing: the SPLIT keeps its
    stored values (ratio, notes, ``updated_at``), the dividend (event 0, day 22) is not written, and the interest the
    item deletes (``delete_ids``, day 21) is still there.
    """
    split_id = await _seed(owned, 20, AssetEventType.SPLIT, "2", notes="2-for-1")
    interest_id = await _seed(owned, 21, AssetEventType.INTEREST, "0.75")
    before = await _snapshot(owned)
    data = [_item(owned.asset_id, [_ev(22, "DIVIDEND", "1.5"), _ev(20, "SPLIT", ratio, event_id=split_id, notes="corrected")], delete_ids=[interest_id])]
    story = f"an edit of the SPLIT {split_id} (ratio 2) to ratio {ratio}, saved with a new dividend and the deletion of the interest {interest_id}"

    refusal = await _upsert_refused(owned, data, story)

    _assert_refused_for_the_ratio(refusal, story, asset_id=owned.asset_id, item_index=0, splits=[(1, 20)])
    after = await _snapshot(owned)
    assert after == before, f"{story} was refused, yet it wrote: before {before}, after {after}"


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _INVALID_RATIOS)
async def test_an_edit_turning_a_dividend_into_a_split_with_an_invalid_ratio_is_refused_and_the_dividend_is_kept(owned, ratio):
    """Red today: accepted; the DIVIDEND, edited by id, becomes a SPLIT of ``ratio`` under its id.

    Contract (X-R47): the rule reads the type the edit ends with: ``EVENT_INVALID_SPLIT_RATIO`` naming event 0 (day 30);
    the row is still the DIVIDEND of 1.25 EUR it was, every column, ``updated_at`` included.
    """
    dividend_id = await _seed(owned, 30, AssetEventType.DIVIDEND, "1.25", notes="Q3")
    before = await _snapshot(owned)
    data = [_item(owned.asset_id, [_ev(30, "SPLIT", ratio, event_id=dividend_id)])]
    story = f"an edit turning the DIVIDEND {dividend_id} of 1.25 EUR into a SPLIT of ratio {ratio}"

    refusal = await _upsert_refused(owned, data, story)

    _assert_refused_for_the_ratio(refusal, story, asset_id=owned.asset_id, item_index=0, splits=[(0, 30)])
    after = await _snapshot(owned)
    assert after == before, f"{story} was refused, yet it wrote: before {before}, after {after}"


@pytest.mark.asyncio
async def test_an_invalid_split_in_a_later_item_writes_nothing_of_the_earlier_one(owned):
    """Red today: accepted, both items stored.

    Contract (X-R47): the request is all or nothing; ``EVENT_INVALID_SPLIT_RATIO`` names item 1, the asset of the SPLIT,
    and its event 0 (day 40); the interest of item 0, on the other asset, is not written.
    """
    before = await _snapshot(owned)
    data = [_item(owned.other_asset_id, [_ev(40, "INTEREST", "1.50")]), _item(owned.asset_id, [_ev(40, "SPLIT", "0")])]
    story = "a SPLIT of ratio 0 in item 1, saved after another asset's interest in item 0"

    refusal = await _upsert_refused(owned, data, story)

    _assert_refused_for_the_ratio(refusal, story, asset_id=owned.asset_id, item_index=1, splits=[(0, 40)])
    after = await _snapshot(owned)
    assert after == before, f"{story} was refused, yet events were written: {_describe(await _rows(owned))}"


@pytest.mark.asyncio
async def test_the_refusal_names_every_split_with_an_invalid_ratio_in_request_order(owned):
    """Red today: accepted, every event of the item written, the stored SPLIT of 2 edited to -2.

    Contract (X-R47): one item holds a new SPLIT of 0 (event 0, day 50), a dividend (1, day 51), an edit by id of a
    stored SPLIT of 2 to -2 (2, day 52), a new SPLIT of 1.5 (3, day 53) and a new SPLIT of -0.000001 (4, day 54).
    ``EVENT_INVALID_SPLIT_RATIO`` names events 0, 2 and 4 — new events and edits alike, the valid SPLIT not — and
    nothing is written.
    """
    split_id = await _seed(owned, 52, AssetEventType.SPLIT, "2")
    before = await _snapshot(owned)
    data = [_item(owned.asset_id, [_ev(50, "SPLIT", "0"), _ev(51, "DIVIDEND", "1.5"), _ev(52, "SPLIT", "-2", event_id=split_id), _ev(53, "SPLIT", "1.5"), _ev(54, "SPLIT", str(-_ONE_UNIT))])]
    story = f"an item with a new SPLIT of 0, a dividend, an edit of the SPLIT {split_id} to -2, a new SPLIT of 1.5 and a new SPLIT of {-_ONE_UNIT}"

    refusal = await _upsert_refused(owned, data, story)

    _assert_refused_for_the_ratio(refusal, story, asset_id=owned.asset_id, item_index=0, splits=[(0, 50), (2, 52), (4, 54)])
    after = await _snapshot(owned)
    assert after == before, f"{story} was refused, yet it wrote: before {before}, after {after}"


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _INVALID_RATIOS)
async def test_the_events_endpoint_answers_400_event_invalid_split_ratio(owned, ratio):
    """Red today: 200, the SPLIT of ``ratio`` stored. With the service refusing but no entry in ``_REFUSAL_STATUS``: 500.

    Contract (X-R47): 400, ``detail.error_code`` EVENT_INVALID_SPLIT_RATIO, ``detail.params.events`` naming event 0 (its
    date, SPLIT) and giving its ``ratio`` as sent, a string — what the event editor's message shows (the X-R47 case of
    ``eventSaveError.test.ts``): a Decimal there would reach the JSON as a number, -0.000001 as -1e-06 — nothing
    written. Posted in process as user A (``_post_events``): the route reads its caller since R13-SEC7.
    """
    before = await _snapshot(owned)

    response = await _post_events(owned.user_a_id, [{"asset_id": owned.asset_id, "events": [_ev(60, "SPLIT", ratio)]}])

    if response.status_code == 200:
        pytest.fail(f"POST /assets/events saved a SPLIT of ratio {ratio} (200): it reads back as {_describe(await _rows(owned))}, instead of answering 400 EVENT_INVALID_SPLIT_RATIO; once a transaction links it, the Dashboard answers 500")
    detail = _detail(response)
    assert (response.status_code, detail.get("error_code")) == (400, "EVENT_INVALID_SPLIT_RATIO"), f"POST /assets/events answers {response.status_code} {response.text} to a SPLIT of ratio {ratio}: expected 400 EVENT_INVALID_SPLIT_RATIO"
    entries = (detail.get("params") or {}).get("events") or []
    named = [(entry.get("event_index"), entry.get("date"), entry.get("type")) for entry in entries]
    assert named == [(0, _day(60).isoformat(), "SPLIT")], f"the 400 does not name the SPLIT of {_day(60)} as event 0 in params.events, so the editor cannot point at it: {detail}"
    assert entries[0].get("ratio") == ratio, f"the 400 gives the SPLIT's ratio as {entries[0].get('ratio')!r}: expected {ratio!r}, the string as sent, which the editor's message quotes: {detail}"
    after = await _snapshot(owned)
    assert after == before, f"the request was refused, yet events were written: {_describe(await _rows(owned))}"


def test_the_events_endpoint_maps_event_invalid_split_ratio_to_400():
    """Red today: ``_REFUSAL_STATUS`` has no ``EVENT_INVALID_SPLIT_RATIO``: once the service refuses with it, the router
    finds no status for the code and answers the user's mistake with a 500.

    Contract (X-R47): ``_REFUSAL_STATUS["EVENT_INVALID_SPLIT_RATIO"] == 400``, the client's mistake, as
    ``EVENT_TOO_MANY_DIGITS``.
    """
    statuses = events_api._REFUSAL_STATUS
    assert "EVENT_INVALID_SPLIT_RATIO" in statuses, f"POST /assets/events has no status for EVENT_INVALID_SPLIT_RATIO: the refusal of a SPLIT of ratio 0 would answer 500, not 400 (the codes it maps: {sorted(statuses)})"
    assert statuses["EVENT_INVALID_SPLIT_RATIO"] == 400, f"POST /assets/events answers EVENT_INVALID_SPLIT_RATIO with {statuses['EVENT_INVALID_SPLIT_RATIO']}: expected 400, the client's mistake"


# ─────────────────────────────────────────────────────────────────────────────
# Provider SPLITs whose ratio is not valid: dropped, the others written, one warning
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _INVALID_RATIOS)
async def test_a_provider_split_with_an_invalid_ratio_is_dropped_the_others_written_and_one_warning_names_it(owned, ratio):
    """Red today: ``_upsert_asset_events`` checks no ratio: the SPLIT of ``ratio`` is written under the assignment beside
    the others, and nothing is logged; the first transaction linked to it takes the Dashboard down (500).

    Contract (X-R47): of a refresh's events — a dividend (day 70), a SPLIT of ``ratio`` (day 71), an interest (day 72), a
    SPLIT of 2 (day 73) — the SPLIT of day 71 is dropped, the three others are written under the assignment, nothing
    raises; one warning (or worse) names it, its date and the word split, and names the asset.
    """
    events = [_provider_event(70, "DIVIDEND", "1.5"), _provider_event(71, "SPLIT", ratio), _provider_event(72, "INTEREST", "2.25"), _provider_event(73, "SPLIT", "2")]
    story = f"a refresh delivering a SPLIT of ratio {ratio} on {_day(71)} beside a dividend, an interest and a SPLIT of 2"

    captured = await _provider_upsert(owned, events, story)

    rows = await _rows(owned)
    written = sorted((row.date, str(row.type), row.value, row.provider_assignment_id) for row in rows)
    expected = [(_day(70), "DIVIDEND", Decimal("1.5"), owned.assignment_id), (_day(72), "INTEREST", Decimal("2.25"), owned.assignment_id), (_day(73), "SPLIT", Decimal("2"), owned.assignment_id)]
    assert written == expected, f"{story} wrote {_describe(rows)}: expected the three others alone (X-R47: drop the SPLIT of ratio {ratio}, which takes the Dashboard down, 500, once a transaction links it)"
    _assert_one_warning_names_the_split(captured, owned, 71, story)


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _INVALID_RATIOS)
async def test_a_provider_split_with_an_invalid_ratio_leaves_the_stored_split_of_its_key_as_it_was(owned, ratio):
    """Red today: the refresh updates the stored provider SPLIT of 2 in place to ``ratio``: a split the user's
    transactions may already link to, so the Dashboard answers 500 at once.

    Contract (X-R47): the SPLIT of ``ratio`` is dropped, so the stored SPLIT of its key (day 80) keeps every column,
    ``updated_at`` included; the dividend of the same refresh (day 81) is written; one warning names the SPLIT of day 80
    and the asset.
    """
    split_id = await _seed(owned, 80, AssetEventType.SPLIT, "2", provider=True)
    stored = (await _snapshot(owned)).get(split_id)
    events = [_provider_event(80, "SPLIT", ratio), _provider_event(81, "DIVIDEND", "1.5")]
    story = f"a refresh delivering ratio {ratio} for the SPLIT {split_id} of {_day(80)} it stored with ratio 2"

    captured = await _provider_upsert(owned, events, story)

    after = (await _snapshot(owned)).get(split_id)
    assert after == stored, f"{story} rewrote it: before {stored}, after {after} (X-R47: drop the SPLIT of ratio {ratio}; the transactions linked to the stored split would take the Dashboard down, 500)"
    others = sorted((row.date, str(row.type), row.value, row.provider_assignment_id) for row in await _rows(owned) if row.id != split_id)
    assert others == [(_day(81), "DIVIDEND", Decimal("1.5"), owned.assignment_id)], f"{story}: besides the SPLIT {split_id}, the events of the asset are {others}: expected the refresh's dividend alone"
    _assert_one_warning_names_the_split(captured, owned, 80, story)


# ─────────────────────────────────────────────────────────────────────────────
# Guards: green before and after the cure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("ratio", "valid"),
    [
        *(pytest.param(value, False, id=f"invalid-{name}") for value, name in _INVALID),
        *(pytest.param(value, True, id=f"valid-{name}") for value, name in _VALID),
    ],
)
def test_guard_the_ratios_here_are_judged_by_the_engines_rule_and_fit_the_event_column(ratio, valid):
    """Guard: green today and after. What this unit calls an invalid ratio, ``is_valid_split_ratio`` — the portfolio
    engine's rule — refuses, and the valid ones it accepts; and every one fits ``AssetEvent.value`` (6 decimal places, 15
    significant digits, 12 integer digits), so ``EVENT_TOO_MANY_DIGITS`` never refuses it first and W-B58 never drops a
    provider's: a refusal or a drop seen here is about the ratio alone."""
    amount = Decimal(ratio)
    assert is_valid_split_ratio(amount) is valid, f"is_valid_split_ratio({ratio}) is {is_valid_split_ratio(amount)}: this unit takes {ratio} as {'valid' if valid else 'invalid'}"
    assert decimal_limit_issue(amount, AssetEvent, "value") is None, f"barrier: a ratio of {ratio} breaks the event value's digit limits ({decimal_limit_issue(amount, AssetEvent, 'value')}): EVENT_TOO_MANY_DIGITS would refuse it before any ratio rule"
    assert integer_digits_issue(amount, AssetEvent, "value") is None, f"barrier: a ratio of {ratio} has more integer digits than the event value keeps: W-B58 would drop a provider's before any ratio rule"


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _VALID_RATIOS)
async def test_guard_every_way_of_writing_a_manual_split_accepts_a_valid_ratio(owned, ratio):
    """Guard: green today and after. One upsert item writes a SPLIT of ``ratio`` in each way a manual event is written: a
    new event (day 100), an upsert on the key of a stored SPLIT of 3 (day 101), an edit by id of a stored SPLIT of 3 (day
    102), an edit by id turning a stored DIVIDEND of 1.25 into a SPLIT (day 103). Accepted: each reads back a SPLIT of
    ``ratio``, the stored rows under their ids."""
    by_key = await _seed(owned, 101, AssetEventType.SPLIT, "3")
    by_id = await _seed(owned, 102, AssetEventType.SPLIT, "3")
    retyped = await _seed(owned, 103, AssetEventType.DIVIDEND, "1.25")
    story = f"an item writing a SPLIT of ratio {ratio} as a new event, on the key of the SPLIT {by_key}, over the SPLIT {by_id} and over the DIVIDEND {retyped}"

    await _upsert([_item(owned.asset_id, [_ev(100, "SPLIT", ratio), _ev(101, "SPLIT", ratio), _ev(102, "SPLIT", ratio, event_id=by_id), _ev(103, "SPLIT", ratio, event_id=retyped)])], story)

    rows = await _rows(owned)
    by_row = {row.id: (row.date, row.type, row.value) for row in rows}
    added = sorted(set(by_row) - {by_key, by_id, retyped})
    found = [by_row.get(by_key), by_row.get(by_id), by_row.get(retyped), *(by_row[event_id] for event_id in added)]
    expected = [(_day(offset), AssetEventType.SPLIT, Decimal(ratio)) for offset in (101, 102, 103, 100)]
    assert found == expected, f"{story} reads back as {_describe(rows)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _VALID_RATIOS)
async def test_guard_a_new_split_with_a_valid_ratio_is_created(owned, ratio):
    """Guard: green today and after. «+ New event» (``mode`` "create"): a SPLIT of ``ratio`` is stored and reads back."""
    story = f"a new SPLIT of ratio {ratio} (create mode)"

    await _upsert([_item(owned.asset_id, [_ev(110, "SPLIT", ratio)], mode="create")], story)

    rows = await _rows(owned)
    found = [(row.asset_id, row.date, row.type, row.value, row.provider_assignment_id) for row in rows]
    assert found == [(owned.asset_id, _day(110), AssetEventType.SPLIT, Decimal(ratio), None)], f"{story} reads back as {_describe(rows)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", _OTHER_TYPES)
async def test_guard_another_event_type_of_0_is_stored(owned, kind):
    """Guard: green today and after. The ratio rule is the SPLIT's: a ``kind`` of 0 EUR is stored and reads back 0."""
    story = f"a {kind} of 0 EUR"

    await _upsert([_item(owned.asset_id, [_ev(120, kind, "0")])], story)

    rows = await _rows(owned)
    found = [(row.date, str(row.type), row.value) for row in rows]
    assert found == [(_day(120), kind, Decimal("0"))], f"{story} reads back as {_describe(rows)}"


@pytest.mark.asyncio
async def test_guard_a_split_edited_into_a_dividend_of_0_is_stored(owned):
    """Guard: green today and after. The rule reads the type an event ends with: a SPLIT of 2 nothing links to, edited by
    id into a DIVIDEND of 0, is accepted and reads back a DIVIDEND of 0 under its id."""
    split_id = await _seed(owned, 130, AssetEventType.SPLIT, "2")
    story = f"an edit of the SPLIT {split_id} (ratio 2) into a DIVIDEND of 0 EUR"

    await _upsert([_item(owned.asset_id, [_ev(130, "DIVIDEND", "0", event_id=split_id)])], story)

    rows = await _rows(owned)
    found = [(row.id, row.date, row.type, row.value) for row in rows]
    assert found == [(split_id, _day(130), AssetEventType.DIVIDEND, Decimal("0"))], f"{story} reads back as {_describe(rows)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", _VALID_RATIOS)
async def test_guard_a_provider_split_with_a_valid_ratio_is_written_and_not_logged(owned, ratio):
    """Guard: green today and after. A refresh delivering a dividend (day 90), a SPLIT of ``ratio`` (day 91) and an
    interest (day 92) writes all three under the assignment, and no warning names the SPLIT."""
    events = [_provider_event(90, "DIVIDEND", "1.5"), _provider_event(91, "SPLIT", ratio), _provider_event(92, "INTEREST", "2.25")]
    story = f"a refresh delivering a SPLIT of ratio {ratio} beside a dividend and an interest"

    captured = await _provider_upsert(owned, events, story)

    rows = await _rows(owned)
    written = sorted((row.date, str(row.type), row.value, row.provider_assignment_id) for row in rows)
    expected = [(_day(90), "DIVIDEND", Decimal("1.5"), owned.assignment_id), (_day(91), "SPLIT", Decimal(ratio), owned.assignment_id), (_day(92), "INTEREST", Decimal("2.25"), owned.assignment_id)]
    assert written == expected, f"{story} wrote {_describe(rows)}: expected all three"
    warnings = _split_warnings(captured, 91)
    assert not warnings, f"{story} logged {warnings}: nothing was dropped"


# ─────────────────────────────────────────────────────────────────────────────
# The split predicate: how the event store asks for a SPLIT without naming the member (rule d of the layer boundaries)
#
# Rule d of test_layer_boundaries.py: ``AssetEventType.SPLIT`` is named only in the split loader,
# ``financial_math/splits.py``. The event store's two checks — ``_reject_invalid_split_ratios`` for a manual event,
# ``_storable_events`` for a provider's — ask it instead: ``is_split_event_type(value)``, True for text that reads SPLIT
# once stripped and upper-cased (an ``AssetEventType`` member is text: a StrEnum), False for anything else, and never an
# exception. Red today by absence: the name is read when a test runs, never at import, so the rest of the unit runs.
# ─────────────────────────────────────────────────────────────────────────────


def _is_split_event_type() -> Callable[[object], bool]:
    """``financial_math.splits.is_split_event_type``, read when the test runs; missing, the test fails naming it."""
    predicate = getattr(importlib.import_module("backend.app.services.financial_math.splits"), "is_split_event_type", None)
    if predicate is None:
        pytest.fail("backend.app.services.financial_math.splits has no is_split_event_type (X-R47 layer fix, rule d of test_layer_boundaries.py): the event store still names AssetEventType.SPLIT to tell a SPLIT, outside the split loader, instead of asking the layer")
    return predicate


def _split_predicate_answer(value: object) -> object:
    """``is_split_event_type(value)``, asked as the event store asks it. An exception fails the test, naming it: the
    predicate never raises."""
    predicate = _is_split_event_type()
    try:
        return predicate(value)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"is_split_event_type({value!r}) raised {exc!r}: it never raises — asked by the event store, it would answer a save with a 500 (POST /assets/events) and make a refresh keep none of the provider's events («Event upsert failed»)")


class _ReadsSplit:
    """Not text, though its ``str()`` reads SPLIT: no event type, so no SPLIT."""

    def __str__(self) -> str:
        return "SPLIT"

    def __repr__(self) -> str:
        return "<an object whose str() is 'SPLIT'>"


class _CannotBeRead:
    """An object whose ``str()`` raises: the predicate answers it False, never with an exception."""

    def __str__(self) -> str:
        raise RuntimeError("this object has no text")

    def __repr__(self) -> str:
        return "<an object whose str() raises>"


#: What is_split_event_type takes for a SPLIT: the member, and text that reads SPLIT once stripped and upper-cased.
_SPLIT_TYPE_VALUES = [
    pytest.param(AssetEventType.SPLIT, id="member-SPLIT"),
    pytest.param("SPLIT", id="text-SPLIT"),
    pytest.param("split", id="text-split"),
    pytest.param("Split", id="text-Split"),
    pytest.param(" SPLIT ", id="text-space-padded"),
    pytest.param("\tsplit\n", id="text-tab-newline-padded"),
]
#: What it takes for no SPLIT: no value, blank text, another type (the text of one, and every other member, so a new
#: one is covered), near misses, and what is not text — even an object whose str() reads SPLIT, or one whose str() raises.
_NOT_SPLIT_TYPE_VALUES = [
    pytest.param(None, id="None"),
    pytest.param("", id="text-empty"),
    pytest.param("   ", id="text-blank"),
    pytest.param("DIVIDEND", id="text-DIVIDEND"),
    *(pytest.param(kind, id=f"member-{kind.name}") for kind in AssetEventType if kind is not AssetEventType.SPLIT),
    pytest.param("SPLITS", id="text-SPLITS"),
    pytest.param("SPLIT_ADJUSTMENT", id="text-SPLIT_ADJUSTMENT"),
    pytest.param("S PLIT", id="text-S-space-PLIT"),
    pytest.param(5, id="int-5"),
    pytest.param(0, id="int-0"),
    pytest.param(b"SPLIT", id="bytes-SPLIT"),
    pytest.param(["SPLIT"], id="list-SPLIT"),
    pytest.param(_ReadsSplit(), id="object-whose-str-is-SPLIT"),
    pytest.param(_CannotBeRead(), id="object-whose-str-raises"),
]


@pytest.mark.parametrize("value", _SPLIT_TYPE_VALUES)
def test_the_split_predicate_takes_the_member_and_text_reading_split_for_a_split(value):
    """Red today: ``financial_math.splits`` has no ``is_split_event_type``: the event store tells a SPLIT by naming
    ``AssetEventType.SPLIT`` itself, which rule d of the layer boundaries forbids outside the split loader.

    Contract (X-R47 layer fix): ``is_split_event_type(value)`` is True — the bool, not a truthy value — for the member and
    for text that reads SPLIT once stripped and upper-cased, as ``_reject_invalid_split_ratios`` reads a type today.
    """
    answer = _split_predicate_answer(value)

    assert answer is True, f"is_split_event_type({value!r}) answers {answer!r}: expected True — the event store would not take this SPLIT for one and would let a ratio of 0 through, which takes the Dashboard down (500) once a transaction links it"


@pytest.mark.parametrize("value", _NOT_SPLIT_TYPE_VALUES)
def test_the_split_predicate_takes_nothing_else_for_a_split_and_never_raises(value):
    """Red today: ``financial_math.splits`` has no ``is_split_event_type`` (rule d of the layer boundaries).

    Contract (X-R47 layer fix): ``is_split_event_type(value)`` is False — the bool — and raises nothing, for no value,
    blank text, every other event type, a near miss, and anything that is not text: an object whose ``str()`` reads
    SPLIT is still no event type, and one whose ``str()`` raises gets an answer, not an exception.
    """
    answer = _split_predicate_answer(value)

    assert answer is False, f"is_split_event_type({value!r}) answers {answer!r}: expected False — taken for a SPLIT, its value would be judged as a ratio: a manual event of 0 refused with EVENT_INVALID_SPLIT_RATIO, a provider's dropped"


def test_the_split_predicate_is_a_plain_function():
    """Red today: ``financial_math.splits`` has no ``is_split_event_type`` (rule d of the layer boundaries).

    Contract (X-R47 layer fix): a plain function — callable, not a coroutine function: the event store's checks are
    synchronous and ask it in an ``if``, where a coroutine is always truthy.
    """
    predicate = _is_split_event_type()

    assert callable(predicate), f"financial_math.splits.is_split_event_type is {predicate!r}, which the event store cannot call: every save and every refresh would raise"
    assert not inspect.iscoroutinefunction(predicate), "financial_math.splits.is_split_event_type is a coroutine function: the event store's checks are synchronous, and a coroutine in their if is always truthy — every event, a dividend of 0 included, would be taken for a SPLIT"


# ─────────────────────────────────────────────────────────────────────────────
# R13-SEC7 and X-R47b: the P-10 refusal shows only the caller's transactions, none without a caller
#
# J's P-10 refusal (EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST) lists in ``details["transaction_ids"]`` every costless incoming
# ADJUSTMENT linked to the SPLIT, on any user's broker, and any user can trigger it: an asset is global. With the caller
# given (``current_user_id``, which POST /assets/events passes), ``transaction_ids`` keeps the ones on a broker the
# caller holds an access to, sorted, and ``hidden_transactions_count`` counts the others; without one, none is named
# (X-R47b, E's security review of 5f68a8db0: fail closed): ``transaction_ids`` [] and ``hidden_transactions_count`` all
# of them — the route always passes its caller. The case: a manual SPLIT of 2 with a costless ADJUSTMENT +10 linked on
# each of the unit's brokers — broker B's created first, so the hidden one has the lower id and a positional filter
# shows the wrong one — user A holding an access to broker A alone, user B to broker B alone (so broker B is another
# user's, not nobody's).
# ─────────────────────────────────────────────────────────────────────────────

_RAW_TRANSACTIONS = text("SELECT id, broker_id, asset_id, type, date, quantity, amount, currency, cost_basis_override, cost_basis_currency, asset_event_id, updated_at FROM transactions WHERE broker_id IN :broker_ids ORDER BY id").bindparams(bindparam("broker_ids", expanding=True))


async def _tx_snapshot(owned: _Owned) -> dict[int, tuple]:
    """id -> (broker_id, asset_id, type, date, quantity, amount, currency, cost basis, its currency, asset_event_id,
    updated_at) of every transaction on this unit's brokers, read as ``_snapshot`` reads the events."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(_RAW_TRANSACTIONS, {"broker_ids": owned.broker_ids})).all()
    return {row[0]: tuple(row[1:]) for row in rows}


async def _costless_adjustment(owned: _Owned, broker_id: int, split_id: int, offset: int) -> int:
    """An ADJUSTMENT +10 of the unit's asset on ``broker_id``, linked to ``split_id`` and without a cost — what Auto mode
    stores on a row linked to a SPLIT: its id."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        tx = Transaction(
            broker_id=broker_id,
            asset_id=owned.asset_id,
            type=TransactionType.ADJUSTMENT,
            date=_day(offset),
            quantity=Decimal("10"),
            amount=Decimal("0"),
            currency=None,
            cost_basis_override=None,
            cost_basis_currency=None,
            asset_event_id=split_id,
        )
        session.add(tx)
        await session.commit()
        return tx.id


@dataclass(frozen=True)
class _P10Case:
    """A SPLIT P-10 refuses to retype, and its two costless incoming adjustments."""

    split_id: int
    seen: int  # on broker A, which user A can see
    hidden: int  # on broker B, which user A cannot: user B's


async def _p10_case(owned: _Owned, offset: int) -> _P10Case:
    """A manual SPLIT of 2 on day ``offset``, a costless ADJUSTMENT +10 linked to it on broker B, then one on broker A.

    Barriers, checked, not assumed: P-10 lists both (``costless_incoming_split_adjustments``, the rows its refusal names),
    and of the unit's brokers user A holds an access to broker A alone — so a refusal naming one of them is about who
    sees what.
    """
    split_id = await _seed(owned, offset, AssetEventType.SPLIT, "2", notes="2-for-1")
    hidden = await _costless_adjustment(owned, owned.broker_b_id, split_id, offset)
    seen = await _costless_adjustment(owned, owned.broker_a_id, split_id, offset)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        costless = await costless_incoming_split_adjustments(session, [split_id])
        held = set((await session.execute(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == owned.user_a_id, BrokerUserAccess.broker_id.in_(owned.broker_ids)))).scalars().all())
    assert costless == {split_id: sorted([hidden, seen])}, f"barrier: P-10 lists {costless} as the costless incoming adjustments of the SPLIT {split_id}, not both of {sorted([hidden, seen])}"
    assert held == {owned.broker_a_id}, f"barrier: of the unit's brokers {owned.broker_ids}, user A holds an access to {held}, not to broker A ({owned.broker_a_id}) alone"
    return _P10Case(split_id=split_id, seen=seen, hidden=hidden)


def _retype(owned: _Owned, case: _P10Case, offset: int) -> dict:
    """An upsert item editing the SPLIT by id into a PRICE_ADJUSTMENT of 2 on its own day, as the event editor sends it."""
    return {"asset_id": owned.asset_id, "events": [_ev(offset, "PRICE_ADJUSTMENT", "2", event_id=case.split_id)]}


def _p10_details(owned: _Owned, case: _P10Case, offset: int, transaction_ids: list[int], **hidden: int) -> dict:
    """The details of the P-10 refusal of ``_retype``: the item, the SPLIT, its stored date, ``transaction_ids`` and, given,
    ``hidden_transactions_count``."""
    return {"asset_id": owned.asset_id, "item_index": 0, "event_id": case.split_id, "date": _day(offset).isoformat(), "transaction_ids": transaction_ids, **hidden}


async def _p10_refused(owned: _Owned, data: list[FAEventUpsert], story: str, **caller: int) -> AssetSourceError:
    """``bulk_upsert_events`` for a retype P-10 must refuse, ``caller`` the ``current_user_id`` it is given, if any (none: a
    call without a caller, to which the refusal names no transaction since X-R47b). As in the endpoint, nobody commits.
    Any exception but the refusal fails the test, naming it: before R13-SEC7, a TypeError when a caller is given."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_events(data, session, **caller)
        except AssetSourceError as refusal:
            return refusal
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            given = f" (R13-SEC7: bulk_upsert_events takes the caller as the keyword current_user_id, here {caller})" if caller else ""
            pytest.fail(f"{story} raised {exc!r} instead of the P-10 refusal EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST{given}")
    messages = [row["message"] for row in result["results"]]
    pytest.fail(f"{story} was accepted ({messages}): P-10 refuses a SPLIT's retype while a linked incoming adjustment has no cost, and the two adjustments are now acquisitions of unknown cost: {_describe(await _rows(owned))}")


@pytest.mark.asyncio
async def test_the_p10_refusal_shows_a_caller_only_the_adjustments_on_their_brokers(owned):
    """Red today: ``bulk_upsert_events`` takes no ``current_user_id``, so no caller can be given (TypeError), and the
    refusal names every user's adjustment.

    Contract (R13-SEC7): as user A, the retype of the SPLIT (day 300) is refused with EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST,
    its details exactly {asset_id, item_index 0, event_id, date, ``transaction_ids`` [broker A's adjustment],
    ``hidden_transactions_count`` 1} — no other key, which could carry the hidden id; its message the one an internal
    caller gets, the total count only, whoever asks; nothing written, events and transactions, ``updated_at`` included.
    """
    case = await _p10_case(owned, 300)
    events_before, transactions_before = await _snapshot(owned), await _tx_snapshot(owned)
    data = [_item(owned.asset_id, _retype(owned, case, 300)["events"])]
    story = f"user A retyping the SPLIT {case.split_id}, linked to a costless adjustment on broker A ({case.seen}) and to one on broker B ({case.hidden}), which only user B can see"

    refusal = await _p10_refused(owned, data, story, current_user_id=owned.user_a_id)

    assert refusal.error_code == "EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST", f"{story} was refused with {refusal.error_code} ({refusal.message}): {refusal.details}"
    details = refusal.details or {}
    shown = details.get("transaction_ids")
    assert shown == [case.seen], f"{story}: the refusal shows user A the transactions {shown}: expected [{case.seen}], theirs alone — {case.hidden} is on broker B, another user's transaction (R13-SEC7)"
    hidden = details.get("hidden_transactions_count")
    assert hidden == 1, f"{story}: the refusal counts {hidden!r} hidden adjustment(s): expected 1, the one on broker B, so user A learns the split has a link they cannot give a cost to: {details}"
    expected = _p10_details(owned, case, 300, [case.seen], hidden_transactions_count=1)
    assert details == expected, f"{story}: the refusal's details are {details}: expected exactly {expected} — no other key, which could carry the hidden id"
    internal = await _p10_refused(owned, data, f"{story}, asked by an internal caller")
    assert refusal.message == internal.message, f"{story}: the message is {refusal.message!r}, not the one an internal caller gets, {internal.message!r} (R13-SEC7: the total count only, whoever asks)"
    assert await _snapshot(owned) == events_before, f"{story} was refused, yet events were written: {_describe(await _rows(owned))}"
    assert await _tx_snapshot(owned) == transactions_before, f"{story} was refused, yet the transactions on the unit's brokers changed"


@pytest.mark.asyncio
async def test_the_events_endpoint_shows_the_caller_only_the_adjustments_on_their_brokers(owned):
    """Red today: the route passes no caller, so its 409 shows user A the id of the adjustment on broker B, another user's
    transaction, beside their own, and no ``hidden_transactions_count``.

    Contract (R13-SEC7): ``POST /assets/events`` as user A (``get_current_user`` overridden in process), retyping the SPLIT
    (day 310): 409, ``detail.error_code`` EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST, ``detail.params`` exactly {asset_id,
    item_index 0, event_id, date, ``transaction_ids`` [broker A's adjustment], ``hidden_transactions_count`` 1}; nothing
    written, events and transactions, ``updated_at`` included.
    """
    case = await _p10_case(owned, 310)
    events_before, transactions_before = await _snapshot(owned), await _tx_snapshot(owned)
    story = f"POST /assets/events as user A, retyping the SPLIT {case.split_id} linked to a costless adjustment on broker A ({case.seen}) and to one on broker B ({case.hidden}), which only user B can see"

    response = await _post_events(owned.user_a_id, [_retype(owned, case, 310)])

    detail = _detail(response)
    assert (response.status_code, detail.get("error_code")) == (409, "EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST"), f"{story} answers {response.status_code} {response.text}: expected 409 EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST"
    params = detail.get("params") or {}
    shown = params.get("transaction_ids")
    assert shown == [case.seen], f"{story}: the 409 shows user A the transactions {shown}: expected [{case.seen}], theirs alone — {case.hidden} is on broker B, another user's transaction (R13-SEC7)"
    hidden = params.get("hidden_transactions_count")
    assert hidden == 1, f"{story}: the 409 counts {hidden!r} hidden adjustment(s): expected 1, the one on broker B, so user A learns the split has a link they cannot give a cost to: {params}"
    expected = _p10_details(owned, case, 310, [case.seen], hidden_transactions_count=1)
    assert params == expected, f"{story}: the 409's params are {params}: expected exactly {expected} — no other key, which could carry the hidden id"
    assert await _snapshot(owned) == events_before, f"{story} was refused, yet events were written: {_describe(await _rows(owned))}"
    assert await _tx_snapshot(owned) == transactions_before, f"{story} was refused, yet the transactions on the unit's brokers changed"


@pytest.mark.asyncio
async def test_without_a_caller_the_p10_refusal_names_no_adjustment_and_counts_them_all(owned):
    """Red today (X-R47b): without a caller the refusal names both adjustments, broker B's too, and counts none: fail open.

    Contract (X-R47b, E's security review of 5f68a8db0: fail closed): given no ``current_user_id``, ``bulk_upsert_events``
    knows no user who may see either adjustment, so the retype of the SPLIT (day 320) is refused with
    EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST, its details exactly {asset_id, item_index 0, event_id, date, ``transaction_ids``
    [], ``hidden_transactions_count`` 2} — no id named, both counted, no other key; nothing written, events and
    transactions, ``updated_at`` included; its message the one user A gets for the same request, the total count only,
    whoever asks (the SPLIT is still a SPLIT after a refusal, so user A's retype is refused too).
    """
    case = await _p10_case(owned, 320)
    events_before, transactions_before = await _snapshot(owned), await _tx_snapshot(owned)
    data = [_item(owned.asset_id, _retype(owned, case, 320)["events"])]
    story = f"a call without a caller retyping the SPLIT {case.split_id}, linked to a costless adjustment on broker A ({case.seen}) and to one on broker B ({case.hidden})"

    refusal = await _p10_refused(owned, data, story)

    assert refusal.error_code == "EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST", f"{story} was refused with {refusal.error_code} ({refusal.message}): {refusal.details}"
    details = refusal.details or {}
    shown = details.get("transaction_ids")
    assert shown == [], f"{story}: the refusal hands whoever reads it the transactions {shown}: expected none — no caller is known to see either, and {case.hidden} is on broker B, another user's transaction (X-R47b: fail closed)"
    hidden = details.get("hidden_transactions_count")
    assert hidden == 2, f"{story}: the refusal counts {hidden!r} hidden adjustment(s): expected 2, both, so it still says the split has links without a cost: {details}"
    expected = _p10_details(owned, case, 320, [], hidden_transactions_count=2)
    assert details == expected, f"{story}: the refusal's details are {details}: expected exactly {expected} — no other key, which could carry an id"
    assert await _snapshot(owned) == events_before, f"{story} was refused, yet events were written: {_describe(await _rows(owned))}"
    assert await _tx_snapshot(owned) == transactions_before, f"{story} was refused, yet the transactions on the unit's brokers changed"
    as_user_a = await _p10_refused(owned, data, f"user A retyping the SPLIT {case.split_id} after that refusal", current_user_id=owned.user_a_id)
    assert refusal.message == as_user_a.message, f"{story}: the message is {refusal.message!r}, not the one user A gets for the same request, {as_user_a.message!r} (X-R47b: the total count only, whoever asks)"
