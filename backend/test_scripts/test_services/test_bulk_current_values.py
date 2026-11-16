"""Project 76, lots C1 and C2 — the «bulk current-price read» of asset providers (no server, no network).

Lot C1 is pure (no DB). Lot C2 runs ``PriceQueryOperations.get_current_prices_bulk`` on a private SQLite file (see the C2
section at the end of this file).

A provider that can price many assets in one call says so; the core can then ask once instead of once per asset. This
file pins the contract, before any caller uses it:

1. ``FACurrentValueRequest`` (``schemas/prices.py``) is one item of such a call: ``key`` (non-empty), ``identifier``,
   ``identifier_type``, ``provider_params`` (``{}`` by default, a dict of its own per instance); a field it does not
   declare is refused.
2. ``AssetSourceProvider`` declares ``supports_bulk_current`` (False) and ``bulk_current_max_items`` (100); its
   ``get_current_values_bulk`` raises ``AssetSourceError`` ``NOT_SUPPORTED`` unless a plugin overrides it.
3. The declarations are checked when the class is defined (``TypeError``): ``supports_bulk_current`` a bool;
   ``bulk_current_max_items`` an int >= 1 (a bool, 1.5, 0 and -1 refused); ``supports_bulk_current = True`` only on a
   class that overrides ``get_current_values_bulk``. A well-formed declaration is accepted (guard).
4. ``MockProvider`` supports it (max 50 items): one call answers every item by its key, each answer equal to what
   ``get_current_value`` gives for the same inputs; ``mock_bulk_calls()`` records the keys of each call, in order.
5. An item carrying ``BULK_OMIT_PARAM`` is absent from the answer (no answer for that asset); the others stay.
6. ``INVALID_TICKER_12345`` answers an ``AssetSourceError`` ``NOT_FOUND`` under its key; the other items still answer.
7. An item carrying ``RATE_LIMITED_PARAM`` makes the WHOLE call raise ``AssetRateLimitedError`` (``retry_after`` 30.0);
   the call is recorded before anything else, so a refused call is recorded too.

Lot C2 — ``get_current_prices_bulk`` reads the assets of a bulk provider in ONE provider call per group
(``services/assets/bulk_current.py``: ``BULK_CURRENT_TIMEOUT`` 30 s, ``GROUP_STAMP_SECONDS`` 120 s, ``_clock``,
``reset_group_state()``, ``_group_lock(group_key)``). A group is (provider code, settings fingerprint, cooldown scope).
The keys sent to the provider are opaque: the tests count calls and keys per call, never key values.

8. One ``get_current_values_bulk`` call per group per chunk of ``bulk_current_max_items``: all the requested assets of
   mockprov in one call when there are at most 50.
9. Aligned expiry: when the group is read, the call covers every ACTIVE asset assigned to the provider plus the requested
   ones (a requested inactive asset in, an unrequested inactive one out). Every answer is cached per asset: a following
   request for the others makes no call and serves ``provider:mockprov``.
10. Group stamp: within ``GROUP_STAMP_SECONDS`` (by ``_clock``) an asset of the last read without a cached quote (omitted,
    or answered with an error) is served from the DB (``db:last_known`` or "No price data available") with no new call;
    after the stamp (121 s) the next request calls again. An asset NOT among the members of the last read makes the whole
    group read again.
11. Single-flight: two concurrent requests that need the same group make ONE provider call (the waiting is watched on
    ``_group_lock``, not inferred).
12. «Too many requests» on a group member: every REQUESTED item of the group carries ``RATE_LIMITED`` and ``retry_after``
    (the last stored price kept as ``db:last_known``); no stamp is left.
13. Another failure of the whole call: the items fall back to the DB with no refusal fields; a second request within the
    stamp makes no call; after 121 s it calls again.
14. A per-item ``AssetSourceError`` falls back to the DB for that item only; the others are served by the provider.
15. Today's row is written only for the requested assets; the others are only cached.
16. Chunks: ``bulk_current_max_items`` 2 and five requested assets make three calls of 2, 2 and 1 keys.
17. A dropped cache entry (``core.drop_asset_cache_entries``: a parametric assignment changed, the asset's currency
    changed) is no member of the stamp any more: the next request for that asset reads the group again, instead of
    serving the database until the stamp expires.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import threading
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, IdentifierType, PriceHistory, ProviderInputType
from backend.app.schemas import FACurrentValueRequest
from backend.app.schemas.prices import FACurrentValue
from backend.app.services.asset_source_providers.mockprov.plugin import (
    BULK_OMIT_PARAM,
    RATE_LIMITED_PARAM,
    MockProvider,
    mock_bulk_calls,
    reset_mock_bulk_calls,
)
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.services.platform import provider_cooldown
from backend.app.services.plugin_settings.fields import env_name, env_variables
from backend.app.utils.runtime.cache import NamedCache
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success


@pytest.fixture(autouse=True)
def _fresh_mock_counter() -> Iterator[None]:
    reset_mock_bulk_calls()
    yield
    reset_mock_bulk_calls()


def _req(key: str, identifier: str = "AAA", **params) -> FACurrentValueRequest:
    return FACurrentValueRequest(key=key, identifier=identifier, identifier_type=IdentifierType.TICKER, provider_params=params)


def _define(**attrs) -> type:
    """A minimal concrete provider (only the abstract members) with the given class attributes; raises at definition."""

    async def get_current_value(self, identifier, identifier_type, provider_params):
        raise NotImplementedError

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
        raise NotImplementedError

    body = {
        "provider_code": property(lambda self: "c1_test"),
        "provider_name": property(lambda self: "C1 test"),
        "test_cases": property(lambda self: []),
        "test_search_query": property(lambda self: None),
        "validate_params": lambda self, params: None,
        "get_current_value": get_current_value,
        "get_history_value": get_history_value,
    }
    body.update(attrs)
    return type("C1Provider", (AssetSourceProvider,), body)


async def _bulk_override(self, items):
    return {}


@pytest.mark.asyncio
async def test_c1_default_is_not_bulk_and_refuses_the_call():
    print_section("C1: base default")
    provider = _define()()
    assert provider.supports_bulk_current is False
    assert provider.bulk_current_max_items == 100
    with pytest.raises(AssetSourceError) as exc:
        await provider.get_current_values_bulk([_req("a")])
    assert exc.value.error_code == "NOT_SUPPORTED"
    print_success("default: not bulk, max 100, NOT_SUPPORTED")


@pytest.mark.parametrize(
    "attrs",
    [
        pytest.param({"supports_bulk_current": True}, id="true-without-override"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": 0}, id="max-0"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": -1}, id="max-minus-1"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": True}, id="max-bool"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": 1.5}, id="max-float"),
        pytest.param({"supports_bulk_current": "yes", "get_current_values_bulk": _bulk_override}, id="flag-not-bool"),
    ],
)
def test_c1_class_definition_guards_refuse(attrs):
    with pytest.raises(TypeError):
        _define(**attrs)
    print_success("refused at class definition")


def test_c1_class_definition_accepts_a_well_formed_declaration():
    cls = _define(supports_bulk_current=True, get_current_values_bulk=_bulk_override, bulk_current_max_items=1)
    assert cls.supports_bulk_current is True
    assert cls.bulk_current_max_items == 1
    print_success("True + override + max 1 accepted")


def test_c1_request_refuses_extra_fields_and_an_empty_key():
    with pytest.raises(ValidationError):
        FACurrentValueRequest(key="a", identifier="X", identifier_type=IdentifierType.TICKER, surprise=1)
    with pytest.raises(ValidationError):
        FACurrentValueRequest(key="", identifier="X", identifier_type=IdentifierType.TICKER)
    print_success("extra field and empty key refused")


def test_c1_request_provider_params_default_is_not_shared():
    a = FACurrentValueRequest(key="a", identifier="X", identifier_type=IdentifierType.TICKER)
    b = FACurrentValueRequest(key="b", identifier="X", identifier_type=IdentifierType.TICKER)
    assert a.provider_params == {} and b.provider_params == {}
    a.provider_params["x"] = 1
    assert b.provider_params == {}
    print_success("provider_params defaults to a dict of its own")


@pytest.mark.asyncio
async def test_c1_mock_answers_every_item_like_get_current_value_and_records_the_call():
    assert MockProvider.supports_bulk_current is True
    assert MockProvider.bulk_current_max_items == 50
    provider = MockProvider()
    items = [_req("k1", "AAA"), _req("k2", "BBB"), _req("k3", "CCC")]
    answer = await provider.get_current_values_bulk(items)
    assert mock_bulk_calls() == [("k1", "k2", "k3")]
    assert set(answer) == {"k1", "k2", "k3"}
    for item in items:
        single = await provider.get_current_value(item.identifier, item.identifier_type, item.provider_params)
        assert answer[item.key] == single
    print_success("3 items, one recorded call, each equal to get_current_value")


@pytest.mark.asyncio
async def test_c1_mock_omits_an_item_on_command():
    answer = await MockProvider().get_current_values_bulk([_req("keep"), _req("gone", **{BULK_OMIT_PARAM: True}), _req("keep2")])
    assert "gone" not in answer
    assert {"keep", "keep2"} <= set(answer)
    print_success("omitted key absent, others present")


@pytest.mark.asyncio
async def test_c1_mock_answers_an_invalid_ticker_with_its_own_error():
    answer = await MockProvider().get_current_values_bulk([_req("ok"), _req("bad", "INVALID_TICKER_12345"), _req("ok2")])
    assert isinstance(answer["bad"], AssetSourceError)
    assert answer["bad"].error_code == "NOT_FOUND"
    assert isinstance(answer["ok"], FACurrentValue)
    assert isinstance(answer["ok2"], FACurrentValue)
    print_success("NOT_FOUND under its key, others answered")


@pytest.mark.asyncio
async def test_c1_mock_rate_limited_item_refuses_the_whole_call_and_is_recorded():
    items = [_req("a"), _req("b", **{RATE_LIMITED_PARAM: 30}), _req("c")]
    with pytest.raises(AssetRateLimitedError) as exc:
        await MockProvider().get_current_values_bulk(items)
    assert exc.value.retry_after == 30.0
    assert mock_bulk_calls() == [("a", "b", "c")]
    print_success("whole call refused, retry_after 30.0, call recorded")


# =============================================================================
# LOT C2 — get_current_prices_bulk reads a bulk provider's assets in one call per group
# =============================================================================
# ``services/assets/bulk_current.py`` does not exist before C2: it is imported lazily (``_Groups.bc``), so C1 stays green
# and every C2 test fails on its own, for its own reason.

START = 1_000_000.0
TEST_INSTANCE_KEY = "c2-bulk-current-test-instance-key-0123456789abcdef"
STAMP_PASSED = 121.0  # just past GROUP_STAMP_SECONDS (120)


class FakeClock:
    """A clock that moves only when the test moves it (the group stamps and the provider pauses share it)."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class _Groups:
    """The ``bulk_current`` module, loaded on first use inside the test body, its ``_clock`` the fake one."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> None:
        self._monkeypatch = monkeypatch
        self._clock = clock
        self._module: ModuleType | None = None

    @property
    def bc(self) -> ModuleType:
        if self._module is None:
            module = importlib.import_module("backend.app.services.assets.bulk_current")
            module.reset_group_state()
            self._monkeypatch.setattr(module, "_clock", self._clock)
            self._module = module
        return self._module

    def close(self) -> None:
        if self._module is not None:
            self._module.reset_group_state()


@pytest.fixture(autouse=True)
def _c2_isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pauses on (60 s, an hour at most); no ambient variable of the mockprov fields; a test instance key."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "60")
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "3600")
    for field in MockProvider.settings_fields:
        for name in {*env_variables("asset", "mockprov", field), env_name("asset", "mockprov", field.key)}:
            monkeypatch.delenv(name, raising=False)
            monkeypatch.delenv(name + "_FILE", raising=False)
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", TEST_INSTANCE_KEY)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def groups(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> Iterator[_Groups]:
    """Private pauses on the fake clock, a private current-value cache, and the group state forgotten around the test."""
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", Cooldowns(60, 3600, jitter=0.0, clock=clock))
    monkeypatch.setattr(core, "_asset_current_cache", NamedCache(name=f"c2_current_{uuid.uuid4().hex[:8]}", maxsize=300, ttl=120))
    handle = _Groups(monkeypatch, clock)
    try:
        yield handle
    finally:
        handle.close()


@pytest_asyncio.fixture
async def private_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole schema, as the process's engine for the test; disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'c2_bulk_current.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        monkeypatch.setattr(db_session, "async_engine", engine)
        yield engine
    finally:
        await engine.dispose()


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


async def _asset(
    engine: AsyncEngine,
    *,
    params: dict | None = None,
    identifier: str | None = None,
    active: bool = True,
    last_price: tuple[date, Decimal] | None = None,
) -> int:
    """A USD asset of this test with its mockprov assignment and, optionally, one stored price."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=_unique("C2 asset"), currency="USD", asset_type=AssetType.STOCK, active=active)
        session.add(asset)
        await session.flush()
        session.add(
            AssetProviderAssignment(
                asset_id=asset.id,
                provider_code="mockprov",
                identifier=identifier or _unique("C2"),
                identifier_type=ProviderInputType.TICKER,
                provider_params=json.dumps(params or {}),
            )
        )
        if last_price is not None:
            day, close = last_price
            session.add(PriceHistory(asset_id=asset.id, date=day, close=close, currency="USD", source_plugin_key="test"))
        await session.commit()
        return asset.id


async def _prices(engine: AsyncEngine, asset_ids: list[int]) -> dict[int, object]:
    """``get_current_prices_bulk`` on a session of its own, the items by asset id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        items = await PriceQueryOperations.get_current_prices_bulk(asset_ids, session)
    return {item.asset_id: item for item in items}


def _served(item) -> tuple:
    return (item.value, item.source, item.error_code)


def _lens() -> list[int]:
    return [len(call) for call in mock_bulk_calls()]


def _count_bulk(monkeypatch: pytest.MonkeyPatch, *, raises: Exception | None = None) -> list[int]:
    """Count the calls of ``MockProvider.get_current_values_bulk`` (one entry per call, its item count); with ``raises``
    the call fails with it, instead of running."""
    calls: list[int] = []
    original = MockProvider.get_current_values_bulk

    async def counted(self, items):
        calls.append(len(items))
        if raises is not None:
            raise raises
        return await original(self, items)

    monkeypatch.setattr(MockProvider, "get_current_values_bulk", counted)
    return calls


@pytest.mark.asyncio
async def test_c2_one_call_for_all_the_requested_assets(private_db: AsyncEngine, groups: _Groups):
    """C2-01 — contract 8: three assets of mockprov requested together: ONE bulk call carrying three keys, each served by it."""
    print_section("C2-01: one call per group")
    ids = [await _asset(private_db) for _ in range(3)]
    assert groups.bc.GROUP_STAMP_SECONDS == 120.0 and groups.bc.BULK_CURRENT_TIMEOUT == 30.0

    items = await _prices(private_db, ids)

    assert _lens() == [3]
    assert {_served(items[i]) for i in ids} == {(Decimal("100.00"), "provider:mockprov", None)}
    print_success("1 call, 3 keys, provider:mockprov")


@pytest.mark.asyncio
async def test_c2_aligned_expiry_reads_every_active_asset_and_serves_the_rest_from_cache(private_db: AsyncEngine, groups: _Groups):
    """C2-02 — contract 9: four active assets, one requested: the call carries all four; asking for the other three makes no call."""
    ids = [await _asset(private_db) for _ in range(4)]
    groups.bc  # noqa: B018 — load the module, its clock and its state

    first = await _prices(private_db, ids[:1])
    assert _lens() == [4]
    assert first[ids[0]].source == "provider:mockprov"

    rest = await _prices(private_db, ids[1:])

    assert _lens() == [4], "the others were cached by the first read: no new call"
    assert {_served(rest[i]) for i in ids[1:]} == {(Decimal("100.00"), "provider:mockprov", None)}


@pytest.mark.asyncio
async def test_c2_the_group_read_includes_a_requested_inactive_asset_and_leaves_an_unrequested_one_out(private_db: AsyncEngine, groups: _Groups):
    """C2-03 — contract 9: active a, inactive b (requested), inactive c (not): the call carries a and b only; a is then cached."""
    a = await _asset(private_db)
    b = await _asset(private_db, active=False)
    await _asset(private_db, active=False)
    groups.bc  # noqa: B018

    items = await _prices(private_db, [b])

    assert _lens() == [2]
    assert items[b].source == "provider:mockprov"
    again = await _prices(private_db, [a])
    assert _lens() == [2] and again[a].source == "provider:mockprov"


@pytest.mark.asyncio
async def test_c2_an_asset_left_out_of_the_answer_is_served_from_the_db_within_the_stamp_and_asked_again_after_it(private_db: AsyncEngine, groups: _Groups, clock: FakeClock):
    """C2-04 — contract 10: b is omitted by the provider: within the stamp it is ``db:last_known`` (c, without a price,
    the error item), no new call; 121 s later the next request calls again (the whole group: a, b, c)."""
    omit = {BULK_OMIT_PARAM: True}
    a = await _asset(private_db)
    b = await _asset(private_db, params=omit, last_price=(date(2026, 1, 2), Decimal("42.5")))
    c = await _asset(private_db, params=omit)
    groups.bc  # noqa: B018
    await _prices(private_db, [a])
    assert _lens() == [3]

    clock.now += 30
    within = await _prices(private_db, [b, c])

    assert _lens() == [3], "within the stamp: no new call"
    assert (within[b].value, within[b].source, within[b].as_of_date) == (Decimal("42.5"), "db:last_known", date(2026, 1, 2))
    assert within[c].value is None and within[c].error == "No price data available"
    clock.now += STAMP_PASSED
    await _prices(private_db, [b])
    assert _lens() == [3, 3], "after the stamp the group is read again"


@pytest.mark.asyncio
async def test_c2_an_asset_answered_with_an_error_is_served_from_the_db_within_the_stamp_without_a_new_call(private_db: AsyncEngine, groups: _Groups):
    """C2-05 — contract 10: the error of one item (NOT_FOUND) is no cached quote: asked again within the stamp it
    falls back to the DB, and the provider is not called."""
    ok = await _asset(private_db)
    bad = await _asset(private_db, identifier="INVALID_TICKER_12345", last_price=(date(2026, 1, 2), Decimal("7")))
    groups.bc  # noqa: B018
    await _prices(private_db, [ok])
    assert _lens() == [2]

    again = await _prices(private_db, [bad])

    assert _lens() == [2]
    assert (again[bad].value, again[bad].source) == (Decimal("7"), "db:last_known")


@pytest.mark.asyncio
async def test_c2_an_assignment_created_after_the_read_makes_the_group_read_again(private_db: AsyncEngine, groups: _Groups):
    """C2-06 — contract 10: an asset that was not a member of the last read, asked within the stamp: one more call,
    carrying every active asset and the new one."""
    a = await _asset(private_db)
    b = await _asset(private_db)
    groups.bc  # noqa: B018
    await _prices(private_db, [a])
    assert _lens() == [2]
    c = await _asset(private_db)

    items = await _prices(private_db, [c])

    assert _lens() == [2, 3]
    assert items[c].source == "provider:mockprov"
    assert (await _prices(private_db, [b]))[b].source == "provider:mockprov"
    assert _lens() == [2, 3]


@pytest.mark.asyncio
async def test_c2_two_concurrent_requests_for_one_group_make_one_provider_call(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C2-07 — contract 11: the first call is held until the second request waits on the group's lock (watched, not
    inferred); then ONE call in all, both requests served."""
    a = await _asset(private_db)
    b = await _asset(private_db)
    bc = groups.bc
    asked = 0
    everyone_asked = threading.Event()
    gate_missed: list[bool] = []
    original_lock = bc._group_lock

    class _WatchedLock:
        def __init__(self, lock: asyncio.Lock) -> None:
            self._lock = lock

        async def acquire(self) -> bool:
            nonlocal asked
            asked += 1
            if asked >= 2:
                everyone_asked.set()
            return await self._lock.acquire()

        def release(self) -> None:
            self._lock.release()

        def locked(self) -> bool:
            return self._lock.locked()

        async def __aenter__(self) -> None:
            await self.acquire()

        async def __aexit__(self, *exc_info: object) -> None:
            self.release()

    monkeypatch.setattr(bc, "_group_lock", lambda group_key: _WatchedLock(original_lock(group_key)))
    original_call = MockProvider.get_current_values_bulk

    async def held(self, items):
        # waited in the provider's own thread, with a deadline: a deadline passed is an unmet precondition
        if not everyone_asked.wait(10.0):
            gate_missed.append(True)
        return await original_call(self, items)

    monkeypatch.setattr(MockProvider, "get_current_values_bulk", held)

    first, second = await asyncio.gather(_prices(private_db, [a]), _prices(private_db, [b]))

    assert not gate_missed, "precondition: the second request never waited on the group's lock"
    assert asked >= 2
    assert _lens() == [2], "one provider call for both requests"
    assert first[a].source == "provider:mockprov" and second[b].source == "provider:mockprov"


@pytest.mark.asyncio
async def test_c2_too_many_requests_marks_every_requested_item_of_the_group_and_leaves_no_stamp(private_db: AsyncEngine, groups: _Groups, clock: FakeClock):
    """C2-08 — contract 12: a member refuses (90 s): every requested item is RATE_LIMITED with ``retry_after`` (the stored
    price kept for a), the pause passed (100 s) and the refusal gone, the next request calls again: no stamp was left."""
    print_section("C2-08: the whole call refused")
    a = await _asset(private_db, last_price=(date(2026, 1, 2), Decimal("42.5")))
    b = await _asset(private_db, params={"mock_rate_limited": 90})
    groups.bc  # noqa: B018

    items = await _prices(private_db, [a, b])

    assert _lens() == [2]
    assert (items[a].value, items[a].source, items[a].error_code, items[a].retry_after) == (Decimal("42.5"), "db:last_known", "RATE_LIMITED", 90.0)
    assert (items[b].value, items[b].error_code, items[b].retry_after) == (None, "RATE_LIMITED", 90.0)
    assert items[b].error
    async with AsyncSession(private_db) as session:
        await session.execute(update(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == b).values(provider_params="{}"))
        await session.commit()
    clock.now += 100

    after = await _prices(private_db, [a, b])

    assert _lens() == [2, 2], "no stamp: the group is read again as soon as the pause is over"
    assert {_served(after[a]), _served(after[b])} == {(Decimal("100.00"), "provider:mockprov", None)}
    print_success("RATE_LIMITED on every requested item, no stamp")


@pytest.mark.asyncio
async def test_c2_another_failure_of_the_call_falls_back_to_the_db_and_stamps_a_short_pause(private_db: AsyncEngine, groups: _Groups, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """C2-09 — contract 13: the call fails (FETCH_ERROR): DB fallback, no refusal fields; asked again within the stamp,
    no new call; 121 s later it calls again."""
    a = await _asset(private_db, last_price=(date(2026, 1, 2), Decimal("42.5")))
    b = await _asset(private_db)
    calls = _count_bulk(monkeypatch, raises=AssetSourceError("x", "FETCH_ERROR"))
    groups.bc  # noqa: B018

    items = await _prices(private_db, [a, b])

    assert calls == [2]
    assert (items[a].value, items[a].source, items[a].error_code, items[a].retry_after) == (Decimal("42.5"), "db:last_known", None, None)
    assert (items[b].value, items[b].error_code, items[b].retry_after) == (None, None, None) and items[b].error
    clock.now += 30
    await _prices(private_db, [a, b])
    assert calls == [2], "within the stamp: no new call"
    clock.now += STAMP_PASSED
    await _prices(private_db, [a, b])
    assert calls == [2, 2], "after the stamp: asked again"


@pytest.mark.asyncio
async def test_c2_a_per_item_error_falls_back_for_that_item_only(private_db: AsyncEngine, groups: _Groups):
    """C2-10 — contract 14: INVALID_TICKER_12345 answers NOT_FOUND for its item: DB fallback for it, the others
    ``provider:mockprov``, all in one call."""
    ok1 = await _asset(private_db)
    bad = await _asset(private_db, identifier="INVALID_TICKER_12345", last_price=(date(2026, 1, 2), Decimal("7")))
    ok2 = await _asset(private_db)
    groups.bc  # noqa: B018

    items = await _prices(private_db, [ok1, bad, ok2])

    assert _lens() == [3]
    assert (items[bad].value, items[bad].source, items[bad].error_code) == (Decimal("7"), "db:last_known", None)
    assert items[ok1].source == items[ok2].source == "provider:mockprov"


@pytest.mark.asyncio
async def test_c2_todays_row_is_written_for_the_requested_assets_only(private_db: AsyncEngine, groups: _Groups):
    """C2-11 — contract 15: three active assets, one requested: a row of today exists for it alone; the others are only cached."""
    ids = [await _asset(private_db) for _ in range(3)]
    groups.bc  # noqa: B018

    await _prices(private_db, ids[:1])

    assert _lens() == [3]
    async with AsyncSession(private_db) as session:
        rows = (await session.execute(select(PriceHistory.asset_id).where(PriceHistory.asset_id.in_(ids), PriceHistory.date == date.today()))).scalars().all()
    assert sorted(rows) == [ids[0]]


@pytest.mark.asyncio
async def test_c2_the_group_is_read_in_chunks_of_the_provider_maximum(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C2-12 — contract 16: ``bulk_current_max_items`` 2, five requested assets: three calls of 2, 2 and 1 keys."""
    monkeypatch.setattr(MockProvider, "bulk_current_max_items", 2)
    ids = [await _asset(private_db) for _ in range(5)]
    groups.bc  # noqa: B018

    items = await _prices(private_db, ids)

    assert sorted(_lens()) == [1, 2, 2]
    assert {_served(items[i]) for i in ids} == {(Decimal("100.00"), "provider:mockprov", None)}


@pytest.mark.asyncio
async def test_c2_a_dropped_cache_entry_makes_the_group_read_again(private_db: AsyncEngine, groups: _Groups):
    """C2-13 — contract 17: a and b read together; a's entries dropped as a currency change drops them: the next request
    for a reads the group again (a second call), within the stamp."""
    print_section("C2-13: a dropped entry reads the group again")
    a = await _asset(private_db)
    b = await _asset(private_db)
    groups.bc  # noqa: B018
    await _prices(private_db, [a, b])
    assert _lens() == [2]
    async with AsyncSession(private_db, expire_on_commit=False) as session:
        assignment = (await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == a))).scalar_one()

    await core.drop_asset_cache_entries(assignment.provider_code, assignment.identifier, assignment.identifier_type, assignment.provider_params)
    items = await _prices(private_db, [a])

    assert _lens() == [2, 2], "the dropped asset makes the group read again"
    assert items[a].source == "provider:mockprov"
    print_success("dropped entry → group read again, served by the provider")
