"""Project 76, lots C1, C2, C3 and C4 — the «bulk current-price read» of asset providers (no server, no network).

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

Lot C3 — the history refresh (``RefreshOperations.bulk_refresh_prices``, reached as ``AssetSourceManager``) reads today's
current value through the same bulk group as the live read, BEFORE the per-asset history fetches:

18. A refresh of 3 mockprov assets over a range reaching today makes ONE bulk call and never ``get_current_value``; each
    result stores today's price 100.
19. The refresh shares the live read's group: after a live ``get_current_prices_bulk``, a refresh within the stamp makes no
    further call and still stores today's 100.
20. A range that ends before today asks no current value: no bulk call.
21. Aligned expiry: refreshing ONE asset reads the whole active group (3 keys); a following live read of the other two makes
    no new call and serves ``provider:mockprov``.
22. A refused bulk read (rate limited 90 s, refreshed alone): FAILED, ``RATE_LIMITED``, ``retry_after`` 90.0, nothing
    stored, and the history is not asked (the bulk read comes first, the provider's pause holds the history).
23. A current value the price columns refuse, read in bulk: the result carries the X-R51 note of the per-asset path
    (``unstorable_quote_reason``) and today's price is not stored.
24. An asset the bulk read left out, refreshed: the item takes the read's answer (no quote), never a
    ``get_current_value`` of its own; a second refresh within the stamp makes no call at all.
25. The X-R51 note outlives the read that met it: a live read refuses the quote for the price columns, then a refresh
    within the stamp (no new call) still carries the note.

Lot C4 — the minimum refresh interval of current values (``AssetSourceProvider.current_min_refresh_seconds``,
``core.current_cache_ttl``):

26. No interval declared: ``None``, a TTL of 120 s (an object that is no plugin too).
27. A number of at least 120 is the TTL; anything else (a bool, a text, 0, a negative number, below 120, a property
    that raises) gives 120 s.
28. Plan 4.1: 20 assets, interval 1800 s, the scheduler, the list and a detail page asking staggered sets for a fake
    hour: 2 bulk calls of 20 keys.
29. A history refresh within the interval makes no extra bulk call.
30. Without an interval the group is read again after 120 s; with 1800 it is not.
31. The per-asset path stores its quote with the provider's TTL, live and in a refresh.
32. Bulk first (XRL-R06 for a bulk provider): a refused bulk read fails the refresh with nothing stored and the history
    not asked; after the pause the next refresh stores the history and today.
33. Requested assets outside the active set do not chase each other out of the stamp: two inactive assets asked in
    turn within the interval cost one read each, not one per request.
34. A current-value cache emptied within the stamp (the administrator's «clear caches») is read again at the next
    request, not served from the database until the stamp ends.

Lot C3b — the midnight rule of the history refresh: the current quote never replaces a stored or fetched history point of
a day BEFORE today; it only adds that day when it is missing (every provider, per-asset and bulk paths alike):

35. The true close of yesterday survives: the round's history has yesterday (close 50), the quote is dated yesterday
    (100): yesterday stays 50, no row for today.
36. A missing yesterday gets the quote: the history stops the day before, the quote dated yesterday (100) is stored.
37. Resume, yesterday only in the DB: no history is asked (the start resolves to today), the DB has yesterday's close 50,
    the quote dated yesterday (100) is dropped; yesterday stays 50 and the result is not FAILED.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import threading
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import date, timedelta
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
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData, FAPricePoint
from backend.app.schemas.refresh import FARefreshItem, SyncDateRangeModel, SyncStatus
from backend.app.services.asset_source_providers.mockprov.plugin import (
    BULK_OMIT_PARAM,
    RATE_LIMITED_PARAM,
    MockProvider,
    mock_bulk_calls,
    reset_mock_bulk_calls,
)
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.services.assets.price_store import unstorable_quote_reason
from backend.app.services.assets.registry import AssetProviderRegistry
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


# =============================================================================
# LOT C3 — the history refresh reads today's current value through the bulk group
# =============================================================================


def _count_single(monkeypatch: pytest.MonkeyPatch, name: str) -> list[int]:
    """Count the calls of ``MockProvider.<name>`` (still running it)."""
    calls: list[int] = []
    original = getattr(MockProvider, name)

    async def counted(self, *args, **kwargs):
        calls.append(1)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(MockProvider, name, counted)
    return calls


async def _refresh_many(engine: AsyncEngine, asset_ids: list[int], start: date, end: date):
    """``AssetSourceManager.bulk_refresh_prices`` of those assets over [start, end]: the results by asset id."""
    requests = [FARefreshItem(asset_id=i, date_range=SyncDateRangeModel(start=start, end=end)) for i in asset_ids]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await AssetSourceManager.bulk_refresh_prices(requests, session)
    return {result.asset_id: result for result in response.results}


async def _days(engine: AsyncEngine, asset_id: int) -> dict[date, Decimal]:
    async with AsyncSession(engine) as session:
        rows = await session.execute(select(PriceHistory.date, PriceHistory.close).where(PriceHistory.asset_id == asset_id))
        return dict(rows.all())


@pytest.mark.asyncio
async def test_c3_a_refresh_reads_todays_value_in_one_bulk_call(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C3-01 — contract 18: three assets refreshed over a range reaching today: ONE bulk call of 3 keys, no
    ``get_current_value``; each stores today's price 100."""
    print_section("C3-01: refresh, one bulk call")
    ids = [await _asset(private_db) for _ in range(3)]
    groups.bc  # noqa: B018
    single = _count_single(monkeypatch, "get_current_value")
    today = date.today()

    results = await _refresh_many(private_db, ids, today - timedelta(days=3), today)

    assert _lens() == [3]
    assert single == [], "the per-asset current value is never asked"
    for i in ids:
        assert results[i].status != SyncStatus.FAILED
        assert (await _days(private_db, i)).get(today) == Decimal("100.00")
    print_success("1 bulk call, 3 keys, today stored")


@pytest.mark.asyncio
async def test_c3_a_refresh_shares_the_group_of_the_live_read(private_db: AsyncEngine, groups: _Groups):
    """C3-02 — contract 19: after a live read of the group (one call), a refresh within the stamp makes no further call
    and still stores today's 100."""
    ids = [await _asset(private_db) for _ in range(3)]
    groups.bc  # noqa: B018
    await _prices(private_db, ids)
    assert _lens() == [3]
    today = date.today()

    await _refresh_many(private_db, ids, today - timedelta(days=3), today)

    assert _lens() == [3], "within the stamp the refresh reuses the live read's group"
    for i in ids:
        assert (await _days(private_db, i)).get(today) == Decimal("100.00")


@pytest.mark.asyncio
async def test_c3_a_range_ending_before_today_asks_no_current_value(private_db: AsyncEngine, groups: _Groups):
    """C3-03 — contract 20: a range that ends yesterday: no bulk call at all."""
    ids = [await _asset(private_db) for _ in range(2)]
    groups.bc  # noqa: B018
    yesterday = date.today() - timedelta(days=1)

    await _refresh_many(private_db, ids, yesterday - timedelta(days=3), yesterday)

    assert _lens() == []


@pytest.mark.asyncio
async def test_c3_refreshing_one_asset_reads_the_whole_group_and_caches_the_others(private_db: AsyncEngine, groups: _Groups):
    """C3-04 — contract 21: refreshing one of three active assets: one call with 3 keys; a live read of the other two
    makes no new call and serves ``provider:mockprov``."""
    ids = [await _asset(private_db) for _ in range(3)]
    groups.bc  # noqa: B018
    today = date.today()

    await _refresh_many(private_db, ids[:1], today - timedelta(days=3), today)

    assert _lens() == [3]
    rest = await _prices(private_db, ids[1:])
    assert _lens() == [3]
    assert {_served(rest[i]) for i in ids[1:]} == {(Decimal("100.00"), "provider:mockprov", None)}


@pytest.mark.asyncio
async def test_c3_a_refused_bulk_read_fails_the_refresh_and_holds_the_history(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C3-05 — contract 22: the bulk read is refused (90 s): FAILED, RATE_LIMITED, 90.0, nothing stored, and the history
    is never asked."""
    print_section("C3-05: refused bulk read")
    asset_id = await _asset(private_db, params={"mock_rate_limited": 90})
    groups.bc  # noqa: B018
    history = _count_single(monkeypatch, "get_history_value")
    today = date.today()

    results = await _refresh_many(private_db, [asset_id], today - timedelta(days=5), today)

    result = results[asset_id]
    assert (result.status, result.error_code, result.retry_after) == (SyncStatus.FAILED, "RATE_LIMITED", 90.0)
    assert await _days(private_db, asset_id) == {}
    assert history == [], "the bulk read comes first: the pause holds the history"
    print_success("FAILED with RATE_LIMITED, history not asked")


@pytest.mark.asyncio
async def test_c3_an_unstorable_bulk_current_value_is_noted_and_not_stored(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C3-06 — contract 23: the bulk answer is 1E-13 USD: the result carries the X-R51 note, today's price is not stored."""
    asset_id = await _asset(private_db)
    groups.bc  # noqa: B018
    today = date.today()

    async def refused_value(self, items):
        return {item.key: FACurrentValue(value=Decimal("1E-13"), currency="USD", as_of_date=today) for item in items}

    monkeypatch.setattr(MockProvider, "get_current_values_bulk", refused_value)

    results = await _refresh_many(private_db, [asset_id], today - timedelta(days=3), today)

    result = results[asset_id]
    assert unstorable_quote_reason(Decimal("1E-13")) in result.errors
    assert today not in await _days(private_db, asset_id)


@pytest.mark.asyncio
async def test_c3_an_omitted_asset_takes_the_bulk_answer_and_makes_no_call_of_its_own(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C3-07 — contract 24: an asset left out of the bulk answer, refreshed twice over a range reaching today: one bulk
    call in all, never a ``get_current_value``, today's price not stored."""
    print_section("C3-07: an omitted asset takes the bulk answer")
    asset_id = await _asset(private_db, params={BULK_OMIT_PARAM: True})
    groups.bc  # noqa: B018
    single = _count_single(monkeypatch, "get_current_value")
    today = date.today()

    await _refresh_many(private_db, [asset_id], today - timedelta(days=3), today)
    await _refresh_many(private_db, [asset_id], today - timedelta(days=3), today)

    assert _lens() == [1], "one bulk read, then the stamp"
    assert single == [], "the item never asks its own current value"
    assert today not in await _days(private_db, asset_id)
    print_success("one bulk call, no single call, today not stored")


@pytest.mark.asyncio
async def test_c3_the_unstorable_note_outlives_the_read_that_met_it(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C3-08 — contract 25: a live read meets a quote of 1E-13 (refused for the price columns); a refresh within the
    stamp makes no call and still carries the X-R51 note."""
    print_section("C3-08: the X-R51 note kept with the stamp")
    asset_id = await _asset(private_db)
    groups.bc  # noqa: B018
    today = date.today()
    calls = 0

    async def refused_value(self, items):
        nonlocal calls
        calls += 1
        return {item.key: FACurrentValue(value=Decimal("1E-13"), currency="USD", as_of_date=today) for item in items}

    monkeypatch.setattr(MockProvider, "get_current_values_bulk", refused_value)
    await _prices(private_db, [asset_id])
    assert calls == 1

    results = await _refresh_many(private_db, [asset_id], today - timedelta(days=3), today)

    assert calls == 1, "within the stamp: no new call"
    assert unstorable_quote_reason(Decimal("1E-13")) in results[asset_id].errors
    print_success("no new call, the X-R51 note still reported")


# =============================================================================
# LOT C4 — the minimum refresh interval of current values
# =============================================================================

C4_CODE_PER_ASSET = "c4_per_asset"
C4_CODE_BULK_ONCE = "c4_bulk_refused_once"


def _interval(monkeypatch: pytest.MonkeyPatch, value: object) -> None:
    """``MockProvider`` declares ``current_min_refresh_seconds`` = ``value`` (the property does not exist before C4)."""
    monkeypatch.setattr(MockProvider, "current_min_refresh_seconds", property(lambda self: value), raising=False)


def _hand_out(monkeypatch: pytest.MonkeyPatch, doubles: dict[str, type]) -> None:
    """The provider registry hands out a new instance of ``doubles[code]`` for those codes, its own providers otherwise."""
    original = AssetProviderRegistry.get_provider_instance

    def get_provider_instance(_cls, code, **kwargs):
        double = doubles.get(code)
        return double() if double is not None else original(code, **kwargs)

    monkeypatch.setattr(AssetProviderRegistry, "get_provider_instance", classmethod(get_provider_instance))


def test_c4_default_is_no_interval_and_a_ttl_of_120():
    """C4-01 — contract 26: no declared interval is ``None`` and the TTL is 120 s; an object that is no plugin has 120 s too."""
    print_section("C4-01: default interval")
    assert MockProvider().current_min_refresh_seconds is None
    assert core.current_cache_ttl(MockProvider()) == 120.0
    assert core.current_cache_ttl(object()) == 120.0
    print_success("None -> 120.0")


@pytest.mark.parametrize("declared", [1800, 1800.5, 120])
def test_c4_a_declared_interval_is_the_ttl(monkeypatch: pytest.MonkeyPatch, declared):
    """C4-02 — contract 27: a number of at least 120 (int or float) is the TTL, as a float."""
    _interval(monkeypatch, declared)
    ttl = core.current_cache_ttl(MockProvider())
    assert ttl == float(declared) and isinstance(ttl, float)


def _raising(self):
    raise RuntimeError("the property failed")


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(True, id="bool"),
        pytest.param("1800", id="string"),
        pytest.param(0, id="zero"),
        pytest.param(-5, id="negative"),
        pytest.param(60, id="below-120"),
        pytest.param(_raising, id="raises"),
    ],
)
def test_c4_an_invalid_interval_falls_back_to_120(monkeypatch: pytest.MonkeyPatch, declared):
    """C4-03 — contract 27: anything else than a number of at least 120 (or an error of the property) is 120.0."""
    prop = property(declared) if callable(declared) else property(lambda self: declared)
    monkeypatch.setattr(MockProvider, "current_min_refresh_seconds", prop, raising=False)
    assert core.current_cache_ttl(MockProvider()) == 120.0


@pytest.mark.asyncio
async def test_c4_a_fake_hour_of_the_plan_makes_two_bulk_calls(private_db: AsyncEngine, groups: _Groups, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """C4-04 — contract 28 (plan 4.1): 20 assets, interval 1800 s; the scheduler asks all 20 every 600 s, the list the first
    10 every 60 s, the detail page asks #15 every 30 s between t=1200 and t=2400, for a fake hour: 2 bulk calls of 20 keys."""
    print_section("C4-04: the call count of the plan")
    _interval(monkeypatch, 1800)
    ids = [await _asset(private_db) for _ in range(20)]
    groups.bc  # noqa: B018
    answered: list[tuple] = []

    async def ask(subset: list[int]) -> None:
        items = await _prices(private_db, subset)
        answered.extend(_served(items[i]) for i in subset)

    for t in range(0, 3600, 30):
        clock.now = START + t
        if t % 600 == 0:
            await ask(ids)
        if t % 60 == 0:
            await ask(ids[:10])
        if 1200 <= t <= 2400:
            await ask([ids[14]])

    assert _lens() == [20, 20], "one read at t=0, one at t=1800"
    assert set(answered) == {(Decimal("100.00"), "provider:mockprov", None)}
    print_success("2 bulk calls of 20 keys in a fake hour")


@pytest.mark.asyncio
async def test_c4_a_history_refresh_makes_no_extra_bulk_call_within_the_interval(private_db: AsyncEngine, groups: _Groups, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """C4-05 — contract 29: interval 1800; reads at t=0 and t=1800, a refresh of all 20 over a range reaching today at t=900
    and at t=2700: no extra bulk call (1 by t=900, 2 in all); today's price stored."""
    _interval(monkeypatch, 1800)
    ids = [await _asset(private_db) for _ in range(20)]
    groups.bc  # noqa: B018
    today = date.today()

    clock.now = START
    await _prices(private_db, ids)
    clock.now = START + 900
    await _refresh_many(private_db, ids, today - timedelta(days=3), today)
    assert _lens() == [20], "the refresh at t=900 reads nothing more"
    clock.now = START + 1800
    await _prices(private_db, ids)
    clock.now = START + 2700
    results = await _refresh_many(private_db, ids, today - timedelta(days=3), today)

    assert _lens() == [20, 20]
    for i in ids:
        assert results[i].status != SyncStatus.FAILED
        assert (await _days(private_db, i)).get(today) == Decimal("100.00")


@pytest.mark.asyncio
@pytest.mark.parametrize(("declared", "calls"), [(None, [3, 3]), (1800, [3])])
async def test_c4_the_group_is_read_again_after_120_seconds_only_without_an_interval(private_db: AsyncEngine, groups: _Groups, clock: FakeClock, monkeypatch: pytest.MonkeyPatch, declared, calls):
    """C4-06 — contract 30: asks at t=0 and t=121: without an interval two calls, with 1800 one."""
    _interval(monkeypatch, declared)
    ids = [await _asset(private_db) for _ in range(3)]
    groups.bc  # noqa: B018

    await _prices(private_db, ids)
    clock.now = START + STAMP_PASSED
    await _prices(private_db, ids)

    assert _lens() == calls


class _PerAssetProvider(MockProvider):
    """mockprov without bulk support, declaring a minimum refresh interval of 1800 s."""

    settings_fields = ()
    supports_bulk_current = False

    @property
    def provider_code(self) -> str:
        return C4_CODE_PER_ASSET

    @property
    def current_min_refresh_seconds(self):
        return 1800


def _record_ttls(monkeypatch: pytest.MonkeyPatch) -> list:
    """Wrap the private current-value cache's ``set``: the ``ttl`` of every entry stored."""
    ttls: list = []
    cache = core._asset_current_cache
    original = cache.set

    def recording(key, value, *args, ttl=None, **kwargs):
        ttls.append(ttl)
        return original(key, value, *args, ttl=ttl, **kwargs)

    monkeypatch.setattr(cache, "set", recording)
    return ttls


async def _per_asset_asset(engine: AsyncEngine) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=_unique("C4 asset"), currency="USD", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=C4_CODE_PER_ASSET, identifier=_unique("C4"), identifier_type=ProviderInputType.TICKER, provider_params="{}"))
        await session.commit()
        return asset.id


@pytest.mark.asyncio
async def test_c4_the_per_asset_live_read_stores_the_quote_with_the_providers_ttl(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C4-07 — contract 31: a live read of an asset of a provider without bulk support declaring 1800 stores its quote with
    ttl 1800 s."""
    _hand_out(monkeypatch, {C4_CODE_PER_ASSET: _PerAssetProvider})
    asset_id = await _per_asset_asset(private_db)
    groups.bc  # noqa: B018
    ttls = _record_ttls(monkeypatch)

    items = await _prices(private_db, [asset_id])

    assert items[asset_id].source == f"provider:{C4_CODE_PER_ASSET}"
    assert ttls and set(ttls) == {timedelta(seconds=1800)}, f"ttl of the entries stored: {ttls}"


@pytest.mark.asyncio
async def test_c4_the_per_asset_refresh_stores_the_quote_with_the_providers_ttl(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch):
    """C4-08 — contract 31: the same for a refresh over a range reaching today."""
    _hand_out(monkeypatch, {C4_CODE_PER_ASSET: _PerAssetProvider})
    asset_id = await _per_asset_asset(private_db)
    groups.bc  # noqa: B018
    ttls = _record_ttls(monkeypatch)
    today = date.today()

    results = await _refresh_many(private_db, [asset_id], today - timedelta(days=3), today)

    assert results[asset_id].status != SyncStatus.FAILED
    assert ttls and set(ttls) == {timedelta(seconds=1800)}, f"ttl of the entries stored: {ttls}"


@pytest.mark.asyncio
async def test_c4_a_bulk_provider_refused_once_fails_the_refresh_then_serves_it_after_the_pause(private_db: AsyncEngine, groups: _Groups, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """C4-09 — contract 32 (plan 3.1 point 5): the bulk call is refused (240 s) on its first call only. Round 1: FAILED,
    RATE_LIMITED, 240.0, nothing stored, no history asked. Past the pause, round 2: OK, the history days and today stored."""
    print_section("C4-09: bulk first, refused once")
    history: list[int] = []

    class _BulkRefusedOnce(MockProvider):
        settings_fields = ()
        bulk_calls = 0

        @property
        def provider_code(self) -> str:
            return C4_CODE_BULK_ONCE

        async def get_current_values_bulk(self, items):
            type(self).bulk_calls += 1
            if type(self).bulk_calls == 1:
                raise AssetRateLimitedError("bulk read refused for too many requests (testing)", retry_after=240.0)
            return await super().get_current_values_bulk(items)

        async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
            history.append(1)
            return await super().get_history_value(identifier, identifier_type, provider_params, start_date, end_date)

    _hand_out(monkeypatch, {C4_CODE_BULK_ONCE: _BulkRefusedOnce})
    async with AsyncSession(private_db, expire_on_commit=False) as session:
        asset = Asset(display_name=_unique("C4 asset"), currency="USD", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=C4_CODE_BULK_ONCE, identifier=_unique("C4"), identifier_type=ProviderInputType.TICKER, provider_params="{}"))
        await session.commit()
        asset_id = asset.id
    groups.bc  # noqa: B018
    today = date.today()
    window = {today - timedelta(days=offset) for offset in range(0, 6)}

    first = (await _refresh_many(private_db, [asset_id], today - timedelta(days=5), today))[asset_id]

    assert (first.status, first.error_code, first.retry_after) == (SyncStatus.FAILED, "RATE_LIMITED", 240.0)
    assert await _days(private_db, asset_id) == {}
    assert history == [], "the bulk read comes first: the pause holds the history"
    clock.now += 241

    second = (await _refresh_many(private_db, [asset_id], today - timedelta(days=5), today))[asset_id]

    assert second.status == SyncStatus.OK and second.error_code is None
    assert set(await _days(private_db, asset_id)) == window
    assert _BulkRefusedOnce.bulk_calls == 2
    print_success("round 1 FAILED, round 2 stored the history and today")


@pytest.mark.asyncio
async def test_c4_inactive_assets_asked_in_turn_do_not_chase_each_other_out(private_db: AsyncEngine, groups: _Groups, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """C4-11 — contract 33: interval 1800; two inactive assets (two detail pages) asked in turn four times within the
    stamp: two reads (one for each, the first time), never one per request."""
    print_section("C4-11: inactive assets asked in turn")
    _interval(monkeypatch, 1800)
    x = await _asset(private_db, active=False)
    y = await _asset(private_db, active=False)
    groups.bc  # noqa: B018
    for step, asset_id in enumerate([x, y, x, y]):
        clock.now = START + 10 * step
        items = await _prices(private_db, [asset_id])
        assert items[asset_id].source == "provider:mockprov"
    assert len(_lens()) == 2, f"one read for each asset, not one per request: {_lens()}"
    print_success("2 reads for 4 requests")


@pytest.mark.asyncio
async def test_c4_an_emptied_cache_is_read_again_within_the_stamp(private_db: AsyncEngine, groups: _Groups, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """C4-12 — contract 34: interval 1800; a read, then the current-value cache emptied («clear caches»): the next
    request within the stamp reads the group again and is served by the provider."""
    print_section("C4-12: an emptied cache is read again")
    _interval(monkeypatch, 1800)
    a = await _asset(private_db)
    b = await _asset(private_db)
    groups.bc  # noqa: B018
    clock.now = START
    await _prices(private_db, [a, b])
    assert len(_lens()) == 1
    core._asset_current_cache.clear()
    clock.now = START + 60
    items = await _prices(private_db, [a])
    assert len(_lens()) == 2, "the emptied cache makes the group read again"
    assert items[a].source == "provider:mockprov"
    print_success("read again after the cache was emptied")


# =============================================================================
# LOT C3b — the midnight rule
# =============================================================================

C3B_CODE_PER_ASSET = "c3b_per_asset"
C3B_CODE_BULK = "c3b_bulk"
C3B_QUOTE = Decimal("100")
C3B_CLOSE = Decimal("50")


def _c3b_quote() -> FACurrentValue:
    """A cached quote read just after midnight: 100 USD dated YESTERDAY."""
    return FACurrentValue(value=C3B_QUOTE, currency="USD", as_of_date=date.today() - timedelta(days=1), source="c3b")


class _C3bMixin:
    """History of close 50 on ``history_days`` only; the current quote is 100 USD dated yesterday."""

    settings_fields = ()
    history_days: set[date] = set()

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
        start = date.min if start_date == "min" else start_date
        prices = [FAPricePoint(date=day, open=C3B_CLOSE, high=C3B_CLOSE, low=C3B_CLOSE, close=C3B_CLOSE, volume=None, currency="USD") for day in sorted(self.history_days) if start <= day <= end_date]
        return FAHistoricalData(prices=prices, events=[], currency="USD", source=self.provider_name)


def _c3b_double(variant: str, days: set[date]) -> tuple[str, type]:
    """The provider code and a double of the given variant ("per_asset" or "bulk") with that history."""
    if variant == "bulk":

        class _Bulk(_C3bMixin, MockProvider):
            supports_bulk_current = True
            history_days = days

            @property
            def provider_code(self) -> str:
                return C3B_CODE_BULK

            async def get_current_values_bulk(self, items):
                return {item.key: _c3b_quote() for item in items}

        return C3B_CODE_BULK, _Bulk

    class _PerAsset(_C3bMixin, MockProvider):
        supports_bulk_current = False
        history_days = days

        @property
        def provider_code(self) -> str:
            return C3B_CODE_PER_ASSET

        async def get_current_value(self, identifier, identifier_type, provider_params=None):
            return _c3b_quote()

    return C3B_CODE_PER_ASSET, _PerAsset


async def _c3b_asset(engine: AsyncEngine, code: str, last_price: tuple[date, Decimal] | None = None) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=_unique("C3b asset"), currency="USD", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=code, identifier=_unique("C3b"), identifier_type=ProviderInputType.TICKER, provider_params="{}"))
        if last_price is not None:
            day, close = last_price
            session.add(PriceHistory(asset_id=asset.id, date=day, close=close, currency="USD", source_plugin_key="test"))
        await session.commit()
        return asset.id


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["per_asset", "bulk"])
async def test_c3b_yesterdays_true_close_survives_the_quote(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch, variant: str):
    """C3b-01 — contract 35: the history has yesterday (close 50), the quote is dated yesterday (100): yesterday stays 50,
    no row for today."""
    print_section(f"C3b-01 yesterday's close survives ({variant})")
    today = date.today()
    yesterday = today - timedelta(days=1)
    code, double = _c3b_double(variant, {today - timedelta(days=offset) for offset in (3, 2, 1)})
    _hand_out(monkeypatch, {code: double})
    asset_id = await _c3b_asset(private_db, code)
    groups.bc  # noqa: B018

    result = (await _refresh_many(private_db, [asset_id], today - timedelta(days=3), today))[asset_id]

    days = await _days(private_db, asset_id)
    assert result.status != SyncStatus.FAILED
    assert days.get(yesterday) == C3B_CLOSE, f"yesterday overwritten by the stale quote: {days}"
    assert today not in days
    print_success("yesterday keeps its true close, no row for today")


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["per_asset", "bulk"])
async def test_c3b_a_missing_yesterday_gets_the_quote(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch, variant: str):
    """C3b-02 — contract 36: the history stops the day before yesterday: the quote dated yesterday is stored (100)."""
    print_section(f"C3b-02 a missing yesterday gets the quote ({variant})")
    today = date.today()
    yesterday = today - timedelta(days=1)
    code, double = _c3b_double(variant, {today - timedelta(days=3), today - timedelta(days=2)})
    _hand_out(monkeypatch, {code: double})
    asset_id = await _c3b_asset(private_db, code)
    groups.bc  # noqa: B018

    result = (await _refresh_many(private_db, [asset_id], today - timedelta(days=3), today))[asset_id]

    days = await _days(private_db, asset_id)
    assert result.status != SyncStatus.FAILED
    assert days.get(yesterday) == C3B_QUOTE, f"the quote did not fill the missing day: {days}"
    assert days[today - timedelta(days=2)] == C3B_CLOSE
    print_success("the quote filled yesterday")


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["per_asset", "bulk"])
async def test_c3b_resume_keeps_a_close_that_only_the_db_has(private_db: AsyncEngine, groups: _Groups, monkeypatch: pytest.MonkeyPatch, variant: str):
    """C3b-03 — contract 37: «resume» with yesterday only in the DB (close 50) asks no history; the quote dated yesterday
    (100) is dropped, yesterday stays 50 and the result is not FAILED."""
    print_section(f"C3b-03 resume keeps the DB close ({variant})")
    today = date.today()
    yesterday = today - timedelta(days=1)
    code, double = _c3b_double(variant, set())
    _hand_out(monkeypatch, {code: double})
    asset_id = await _c3b_asset(private_db, code, last_price=(yesterday, C3B_CLOSE))
    groups.bc  # noqa: B018

    requests = [FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start="resume", end=today))]
    async with AsyncSession(private_db, expire_on_commit=False) as session:
        response = await AssetSourceManager.bulk_refresh_prices(requests, session)
    result = response.results[0]

    days = await _days(private_db, asset_id)
    assert result.status != SyncStatus.FAILED, f"{result.status} {result.error_code}"
    assert days.get(yesterday) == C3B_CLOSE, f"the DB close was overwritten by the stale quote: {days}"
    print_success("the DB close of yesterday survives a resume")
