"""The calls an enricher makes outside its reads, counted on the account it shares (lane 82, lot CG-C).

Module under test: ``services/enrichers/admission.py`` (``count_shared_call``) as the four doors use it:
``recognize.py`` (``_Cascade._call``), ``search.py`` (``_ready``, before a search task) and the routes ``GET
/assets/enrichers/{code}/search`` and ``POST /assets/enrichers/{code}/test`` (``api/v1/assets/enrichers.py``). Reads stay
as they were (``refresh.py``, ``test_enricher_call_limits.py``).

The contract pinned here:

1. **Counted once, before the call.** For an enricher with ``calls_external_service`` True whose settings group
   ``shares_credits``, a recognize (cascade), a search (``search_enrichers``), the ``{code}/search`` route and the
   ``{code}/test`` route each add exactly ONE to the group's row ``("group", <name>)`` and to no other row, and the count
   is already there when the plugin's method starts. A search across two enrichers sharing the group counts two.
2. **A full ceiling refuses before the plugin runs.** The plugin's method is never called: the cascade answers ``error``
   for it, the search outcome is ``rate_limited`` with ``retry_after`` the limit's wait rounded up to whole seconds, both
   routes answer HTTP 429 ``RATE_LIMITED`` with ``Retry-After`` the same.
3. **A limit of 0** stops the group: refused and never called, the same four ways.
4. **Nothing counted** for an enricher with no group, with a group that does not share credits, or with
   ``calls_external_service`` False (beside a counted sibling in each test).
5. **A counter that fails** (the database unreachable, ``count_and_check`` → None) lets the call go.
6. **An identifier-only enricher** (no search, a text that has no identifier shape) is not asked, so counts nothing; the
   same enricher with an identifier-shaped text is asked by recognize, and counts one.
7. **The group holds both families**: the price provider's own calls on the same group are seen by the enricher's
   refusal, and the enricher's call by the provider's.

Pure: no lane database, no server, no network. The counter and the plugin settings' reads share one private SQLite file
under ``tmp_path`` (``call_counter.get_async_engine`` and ``runtime.get_async_engine`` patched); the counter's clock is a
test clock patched into ``call_counter._utc`` (NOW: the minute ends in 30 s, the hour in 870 s, so ``retry_after`` is
exact). The lab enrichers are ``MockEnricher`` subclasses put in ``EnricherRegistry``'s storage with
``monkeypatch.setitem``; each records the method it ran and, when it started, the counter row of the group. The test
groups (``register_group``, their limit given as the field's default) are released at teardown. The routes are called as
coroutines with the per-user probe limit off.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import threading
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1.assets import enrichers as routes
from backend.app.db import IdentifierType
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import AssetType
from backend.app.schemas.assets.enrichers import FAEnricherBinding, FAEnricherTestRequest
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetCallLimitError
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.enricher_providers.mockenrich.plugin import MockEnricher
from backend.app.services.enrichers.base import EnricherPlugin
from backend.app.services.enrichers.recognize import Recognized, RecognizeStatus, recognize_cascade
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.enrichers.search import SearchOutcome, SearchStatus, search_enrichers
from backend.app.services.enrichers.usable import configured_enricher
from backend.app.services.platform import call_counter, provider_cooldown
from backend.app.services.plugin_settings import runtime
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType
from backend.app.services.plugin_settings.groups import SettingsGroup, all_groups, register_group, release_group
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

TEST_INSTANCE_KEY = "cgc-enricher-shared-calls-test-instance-key-0123456789"
WINDOWS = ("minute", "hour", "day", "week", "month")
DEADLINE = 15.0
#: The counter's clock: a Tuesday, 13:45:30 UTC. The minute ends in 30 s, the hour in 870 s.
NOW = datetime(2026, 11, 17, 13, 45, 30, tzinfo=UTC)
MINUTE_WAIT = 30
HOUR_WAIT = 870
GROUP_FAMILY = "group"
#: A valid ISIN (an identifier shape the search recognises); the mock answers it as found.
ISIN = "IE00B4L5Y983"


# =============================================================================
# HELPERS
# =============================================================================


def _code(label: str) -> str:
    return f"cgc_{label}_{uuid.uuid4().hex[:8]}"


def _ident(tag: str) -> str:
    return f"CGC{tag.upper()}{uuid.uuid4().hex[:9].upper()}"


def _limit_field(window: str, default: int | None = None) -> PluginSettingField:
    return PluginSettingField(key=f"call_limit_{window}", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label=f"Calls per {window} (cgc)", default=default, minimum=0)


def _group(*, shares: bool = True, minute: int | None = None, hour: int | None = None) -> str:
    """A test group registered under a unique name, its limits the fields' defaults; released at teardown."""
    name = f"cgc_credits_{uuid.uuid4().hex[:8]}"
    fields = tuple(_limit_field(window, default) for window, default in (("minute", minute), ("hour", hour)))
    register_group(SettingsGroup(name=name, label="CGC credits", shares_credits=shares, fields=fields))
    return name


@dataclass
class Recorder:
    """What the lab enrichers' methods saw: the method names, and the group's counter row when each started."""

    methods: list[str] = field(default_factory=list)
    rows_at_start: list[tuple[int, ...] | None] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def count(self, method: str) -> int:
        with self.lock:
            return self.methods.count(method)


@dataclass
class Clock:
    now: datetime = NOW


@dataclass(frozen=True)
class Counter:
    """The private file (counter and settings) and its engine."""

    path: Path
    engine: AsyncEngine
    clock: Clock

    def counts(self, family: str, code: str) -> tuple[int, ...] | None:
        connection = sqlite3.connect(self.path)
        try:
            row = connection.execute(f"SELECT {', '.join(f'{window}_count' for window in WINDOWS)} FROM plugin_call_counters WHERE family = ? AND plugin_code = ?", (family, code)).fetchone()
        finally:
            connection.close()
        return tuple(row) if row is not None else None

    def rows(self) -> set[tuple[str, str]]:
        connection = sqlite3.connect(self.path)
        try:
            return set(connection.execute("SELECT family, plugin_code FROM plugin_call_counters").fetchall())
        finally:
            connection.close()


def _enricher_class(code: str, recorder: Recorder, counter: Counter, *, group: str | None, external: bool = True, searches: bool = True) -> type:
    """A lab enricher: mockenrich's answers under ``code``, not test-only, reading ``group`` (None: no group). Its
    ``recognize`` and ``search`` record themselves and the group's counter row at the moment they start."""
    watched = (GROUP_FAMILY, group) if group is not None else None

    def record(method: str) -> None:
        with recorder.lock:
            recorder.methods.append(method)
            recorder.rows_at_start.append(counter.counts(*watched) if watched is not None else None)

    def recognize(self, binding):
        record("recognize")
        return MockEnricher.recognize(self, binding)

    def search(self, query):
        record("search")
        return MockEnricher.search(self, query)

    attributes: dict[str, Any] = {"code": code, "name": f"CGC {code}", "test_only": False, "settings_fields": (), "settings_groups": (group,) if group is not None else (), "calls_external_service": external, "recognize": recognize}
    attributes["search"] = search if searches else EnricherPlugin.search
    return type(f"CGCEnricher_{code}", (MockEnricher,), attributes)


def _install(monkeypatch: pytest.MonkeyPatch, plugin_class: type) -> None:
    EnricherRegistry.auto_discover()
    monkeypatch.setitem(EnricherRegistry._get_storage(), EnricherRegistry._normalize_lookup_code(plugin_class.code), plugin_class)


async def _plugin(code: str) -> EnricherPlugin:
    """The instance of ``code`` with its settings bound (the barrier that it is served and configured)."""
    plugin, missing = await configured_enricher(code)
    assert plugin is not None and not missing, f"barrier: {code} is served and configured ({missing})"
    return plugin


def _fill(group: str, limit: int) -> Any:
    """Fill the group's minute window to ``limit`` as another plugin of the group would (the counter's own call)."""

    async def fill() -> None:
        for _ in range(limit):
            await call_counter.count_and_check(GROUP_FAMILY, group, call_counter.CallLimits(minute=limit))

    return fill()


async def _cascade(plugin: EnricherPlugin, identifier: str = ISIN) -> list[Recognized]:
    async def consume() -> list[Recognized]:
        return [event async for event in recognize_cascade(AssetType.ETF, {"ISIN": identifier}, plugins=[plugin]) if isinstance(event, Recognized)]

    return await asyncio.wait_for(consume(), DEADLINE)


async def _search(text: str, codes: list[str]) -> dict[str, SearchOutcome]:
    async def consume() -> list[SearchOutcome]:
        return [outcome async for outcome in search_enrichers(text, codes, asset_type=AssetType.ETF)]

    outcomes = await asyncio.wait_for(consume(), DEADLINE)
    assert sorted(outcome.code for outcome in outcomes) == sorted(codes), f"one outcome per code: {outcomes}"
    return {outcome.code: outcome for outcome in outcomes}


async def _route_search(code: str) -> Any:
    return await asyncio.wait_for(routes.search_enricher(code, "word", _USER), DEADLINE)


async def _route_test(code: str) -> Any:
    request = FAEnricherTestRequest(binding=FAEnricherBinding(identifier_type="ISIN", identifier=_ident("T")))
    return await asyncio.wait_for(routes.test_enricher(code, request, _USER), DEADLINE)


class _User:
    id = 9_382


_USER = _User()


async def _refused(call) -> HTTPException:
    with pytest.raises(HTTPException) as raised:
        await call()
    return raised.value


def _assert_429(refused: HTTPException, wait: int) -> None:
    assert refused.status_code == 429
    assert refused.detail["error_code"] == "RATE_LIMITED" and refused.detail["retry_after"] == wait
    assert refused.headers["Retry-After"] == str(wait)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "60")
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "3600")
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", TEST_INSTANCE_KEY)
    monkeypatch.delenv("LIBREFOLIO_ENRICHERS_ENABLED", raising=False)
    monkeypatch.delenv("LIBREFOLIO_ASSET_PROVIDERS_ENABLED", raising=False)
    monkeypatch.setattr(call_counter, "_warned_at", {})
    monkeypatch.setattr(routes, "enforce_probe_limit", lambda user_id: None, raising=True)
    yield
    for name in [name for name in all_groups() if name.startswith("cgc")]:
        release_group(name)


@pytest.fixture
def cooldowns(monkeypatch: pytest.MonkeyPatch) -> Cooldowns:
    private = Cooldowns(60, 3600, jitter=0.0, clock=lambda: 1_000_000.0)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


@pytest_asyncio.fixture
async def counter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Counter]:
    path = tmp_path / "cgc_counters.db"
    sync_engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    clock = Clock()
    real = call_counter._utc
    monkeypatch.setattr(call_counter, "get_async_engine", lambda: engine)
    monkeypatch.setattr(runtime, "get_async_engine", lambda: engine)
    monkeypatch.setattr(call_counter, "_utc", lambda now=None: real(clock.now if now is None else now))
    try:
        yield Counter(path, engine, clock)
    finally:
        await engine.dispose()


@dataclass
class Member:
    code: str
    group: str
    recorder: Recorder


@pytest.fixture
def member(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """``member(minute=…, hour=…)``: a lab enricher reading a fresh credit-sharing group with those limits."""

    def make(*, minute: int | None = None, hour: int | None = None) -> Member:
        group, code, recorder = _group(minute=minute, hour=hour), _code("member"), Recorder()
        _install(monkeypatch, _enricher_class(code, recorder, counter, group=group))
        return Member(code, group, recorder)

    return make


# =============================================================================
# 1. COUNTED ONCE, BEFORE THE CALL
# =============================================================================


@pytest.mark.asyncio
async def test_cgc_a_recognize_counts_one_on_the_group_before_the_plugin_runs(counter: Counter, member):
    print_section("CGC 1: recognize")
    lab = member(minute=100)
    answer = await _cascade(await _plugin(lab.code))
    assert [(event.code, event.status) for event in answer] == [(lab.code, RecognizeStatus.FOUND)]
    assert counter.counts(GROUP_FAMILY, lab.group) == (1,) * 5
    assert counter.rows() == {(GROUP_FAMILY, lab.group)}, "on the group's row and nothing else"
    assert lab.recorder.methods == ["recognize"] and lab.recorder.rows_at_start == [(1,) * 5], "counted before recognize ran"
    print_success("one count, before")


@pytest.mark.asyncio
async def test_cgc_a_search_counts_one_on_the_group_before_the_plugin_runs(counter: Counter, member):
    print_section("CGC 1: search")
    lab = member(minute=100)
    outcomes = await _search("word", [lab.code])
    assert outcomes[lab.code].status is SearchStatus.OK
    assert counter.counts(GROUP_FAMILY, lab.group) == (1,) * 5
    assert counter.rows() == {(GROUP_FAMILY, lab.group)}
    assert lab.recorder.methods == ["search"] and lab.recorder.rows_at_start == [(1,) * 5]


@pytest.mark.asyncio
async def test_cgc_a_search_across_two_enrichers_of_the_group_counts_two(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    group, first, second = _group(minute=100), _code("one"), _code("two")
    recorder = Recorder()
    _install(monkeypatch, _enricher_class(first, recorder, counter, group=group))
    _install(monkeypatch, _enricher_class(second, recorder, counter, group=group))
    outcomes = await _search("word", [first, second])
    assert {outcome.status for outcome in outcomes.values()} == {SearchStatus.OK}
    assert counter.counts(GROUP_FAMILY, group) == (2,) * 5, "one per enricher asked"
    assert counter.rows() == {(GROUP_FAMILY, group)}
    assert recorder.count("search") == 2


@pytest.mark.asyncio
async def test_cgc_the_search_route_counts_one_before_the_plugin_runs(counter: Counter, member):
    lab = member(minute=100)
    results = await _route_search(lab.code)
    assert [result.name for result in results] == ["Mock word"]
    assert counter.counts(GROUP_FAMILY, lab.group) == (1,) * 5 and counter.rows() == {(GROUP_FAMILY, lab.group)}
    assert lab.recorder.methods == ["search"] and lab.recorder.rows_at_start == [(1,) * 5]


@pytest.mark.asyncio
async def test_cgc_the_test_route_counts_one_before_the_plugin_runs(counter: Counter, member):
    lab = member(minute=100)
    answer = await _route_test(lab.code)
    assert answer.status == RecognizeStatus.FOUND.value
    assert counter.counts(GROUP_FAMILY, lab.group) == (1,) * 5 and counter.rows() == {(GROUP_FAMILY, lab.group)}
    assert lab.recorder.methods == ["recognize"] and lab.recorder.rows_at_start == [(1,) * 5]


@pytest.mark.asyncio
async def test_cgc_every_door_adds_to_the_same_row(counter: Counter, member):
    lab = member(minute=100)
    await _cascade(await _plugin(lab.code))
    await _search("word", [lab.code])
    await _route_search(lab.code)
    await _route_test(lab.code)
    assert counter.counts(GROUP_FAMILY, lab.group) == (4,) * 5
    assert lab.recorder.rows_at_start == [(1,) * 5, (2,) * 5, (3,) * 5, (4,) * 5]


# =============================================================================
# 2. A FULL CEILING REFUSES BEFORE THE PLUGIN RUNS
# =============================================================================


@pytest.mark.asyncio
async def test_cgc_a_full_ceiling_refuses_the_cascade_and_the_plugin_never_runs(counter: Counter, member):
    lab = member(minute=1)
    plugin = await _plugin(lab.code)
    await _fill(lab.group, 1)
    answer = await _cascade(plugin)
    assert [(event.code, event.status) for event in answer] == [(lab.code, RecognizeStatus.ERROR)]
    assert lab.recorder.methods == []
    assert counter.counts(GROUP_FAMILY, lab.group) == (1,) * 5, "a refused call is not counted"


@pytest.mark.asyncio
async def test_cgc_a_full_ceiling_refuses_the_search_with_the_wait_rounded_up(counter: Counter, member):
    lab = member(minute=1)
    await _plugin(lab.code)
    await _fill(lab.group, 1)
    counter.clock.now = NOW.replace(microsecond=400_000)  # 29.6 s left of the minute: rounded up to 30
    outcome = (await _search("word", [lab.code]))[lab.code]
    assert (outcome.status, outcome.retry_after) == (SearchStatus.RATE_LIMITED, 30)
    assert lab.recorder.methods == []


@pytest.mark.asyncio
async def test_cgc_the_wait_is_the_windows_that_ends_last(counter: Counter, member):
    lab = member(minute=100, hour=1)
    await _plugin(lab.code)
    await call_counter.count_and_check(GROUP_FAMILY, lab.group, call_counter.CallLimits(minute=100, hour=1))
    outcome = (await _search("word", [lab.code]))[lab.code]
    assert (outcome.status, outcome.retry_after) == (SearchStatus.RATE_LIMITED, HOUR_WAIT)


@pytest.mark.asyncio
async def test_cgc_a_full_ceiling_answers_429_on_the_two_routes(counter: Counter, member):
    lab = member(minute=1)
    await _plugin(lab.code)
    await _fill(lab.group, 1)
    _assert_429(await _refused(lambda: _route_search(lab.code)), MINUTE_WAIT)
    _assert_429(await _refused(lambda: _route_test(lab.code)), MINUTE_WAIT)
    assert lab.recorder.methods == []
    assert counter.counts(GROUP_FAMILY, lab.group) == (1,) * 5


@pytest.mark.asyncio
async def test_cgc_the_window_that_opens_again_admits_again(counter: Counter, member):
    lab = member(minute=1)
    plugin = await _plugin(lab.code)
    await _fill(lab.group, 1)
    assert (await _cascade(plugin))[0].status is RecognizeStatus.ERROR
    counter.clock.now = datetime(2026, 11, 17, 13, 46, 1, tzinfo=UTC)
    assert (await _cascade(plugin))[0].status is RecognizeStatus.FOUND
    assert lab.recorder.methods == ["recognize"]


# =============================================================================
# 3. A LIMIT OF 0
# =============================================================================


@pytest.mark.asyncio
async def test_cgc_a_limit_of_zero_refuses_every_door_and_the_plugin_never_runs(counter: Counter, member):
    lab = member(minute=0)
    plugin = await _plugin(lab.code)
    assert (await _cascade(plugin))[0].status is RecognizeStatus.ERROR
    assert (await _search("word", [lab.code]))[lab.code].status is SearchStatus.RATE_LIMITED
    for call in (lambda: _route_search(lab.code), lambda: _route_test(lab.code)):
        assert (await _refused(call)).status_code == 429
    assert lab.recorder.methods == []
    assert counter.counts(GROUP_FAMILY, lab.group) in (None, (0,) * 5)


# =============================================================================
# 4. NOTHING COUNTED
# =============================================================================


@pytest.mark.asyncio
async def test_cgc_an_enricher_that_is_not_counted_there_counts_nothing(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """No group, a group that does not share credits, and the flag False: each beside a counted sibling, every door."""
    counted_group = _group(minute=100)
    plain_group = _group(shares=False, minute=0)  # a limit of 0 on a group that shares nothing must not stop anyone
    recorder, counted = Recorder(), _code("counted")
    _install(monkeypatch, _enricher_class(counted, recorder, counter, group=counted_group))
    others = {
        "no group": _enricher_class(_code("nogroup"), recorder, counter, group=None),
        "not sharing": _enricher_class(_code("plain"), recorder, counter, group=plain_group),
        "flag false": _enricher_class(_code("local"), recorder, counter, group=counted_group, external=False),
    }
    for plugin_class in others.values():
        _install(monkeypatch, plugin_class)
    codes = [counted] + [plugin_class.code for plugin_class in others.values()]

    outcomes = await _search("word", codes)
    assert {outcome.status for outcome in outcomes.values()} == {SearchStatus.OK}, "none stopped, none refused"
    assert counter.counts(GROUP_FAMILY, counted_group) == (1,) * 5, "only the sibling"
    for plugin_class in others.values():
        plugin = await _plugin(plugin_class.code)
        assert (await _cascade(plugin))[0].status is RecognizeStatus.FOUND
        assert await _route_search(plugin_class.code)
        assert (await _route_test(plugin_class.code)).status == RecognizeStatus.FOUND.value
    assert counter.counts(GROUP_FAMILY, counted_group) == (1,) * 5, "the others' calls counted nothing on the sibling's group"
    assert counter.rows() == {(GROUP_FAMILY, counted_group)}, "no row for a plugin, a plain group or a local one"
    assert recorder.count("search") == 4 + 3 and recorder.count("recognize") == 3 * 2


# =============================================================================
# 5. A COUNTER THAT FAILS
# =============================================================================


@pytest.mark.asyncio
async def test_cgc_a_failing_counter_lets_every_call_go(counter: Counter, member, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    lab = member(minute=1)  # the limit is read from the settings; the count goes to a database that cannot be reached
    plugin = await _plugin(lab.code)
    broken = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'missing-folder' / 'counters.db'}", poolclass=NullPool)
    monkeypatch.setattr(call_counter, "get_async_engine", lambda: broken)
    try:
        assert (await _cascade(plugin))[0].status is RecognizeStatus.FOUND
        assert (await _search("word", [lab.code]))[lab.code].status is SearchStatus.OK
        assert await _route_search(lab.code)
        assert (await _route_test(lab.code)).status == RecognizeStatus.FOUND.value
        assert lab.recorder.methods == ["recognize", "search", "search", "recognize"], "every door let the call go"
    finally:
        await broken.dispose()


# =============================================================================
# 6. AN IDENTIFIER-ONLY ENRICHER
# =============================================================================


@pytest.mark.asyncio
async def test_cgc_an_identifier_only_enricher_counts_nothing_for_a_text_that_is_no_identifier(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    group, code, recorder = _group(minute=100), _code("idonly"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, counter, group=group, searches=False))
    word = (await _search("hello world", [code]))[code]
    assert word.status is SearchStatus.IDENTIFIER_ONLY
    assert recorder.methods == [] and counter.rows() == set(), "nothing asked, nothing counted"
    shaped = (await _search(ISIN, [code]))[code]
    assert shaped.status is SearchStatus.OK, "the same enricher asked by an identifier-shaped text"
    assert recorder.methods == ["recognize"]
    assert counter.counts(GROUP_FAMILY, group) == (1,) * 5


@pytest.mark.asyncio
async def test_cgc_an_identifier_only_enricher_with_a_full_group_is_refused_only_when_it_would_be_asked(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    group, code, recorder = _group(minute=0), _code("idfull"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, counter, group=group, searches=False))
    assert (await _search("hello world", [code]))[code].status is SearchStatus.IDENTIFIER_ONLY
    assert (await _search(ISIN, [code]))[code].status is SearchStatus.RATE_LIMITED
    assert recorder.methods == []


# =============================================================================
# 7. THE GROUP HOLDS BOTH FAMILIES
# =============================================================================


def _asset_plugin_class(code: str, group: str) -> type:
    return type(
        f"CGCAsset_{code}",
        (MockProvider,),
        {"provider_code": property(lambda self: code), "provider_name": f"CGC {code}", "test_only": False, "calls_external_service": True, "settings_fields": (), "settings_groups": (group,)},
    )


@pytest.mark.asyncio
async def test_cgc_the_price_providers_calls_on_the_group_are_seen_by_the_enrichers_refusal(counter: Counter, cooldowns: Cooldowns, member, monkeypatch: pytest.MonkeyPatch):
    lab = member(minute=3)
    asset_code = _code("price")
    AssetProviderRegistry.auto_discover()
    monkeypatch.setitem(AssetProviderRegistry._get_storage(), AssetProviderRegistry._normalize_lookup_code(asset_code), _asset_plugin_class(asset_code, lab.group))
    await _plugin(lab.code)

    async def price_call() -> None:
        provider = await core.configured_provider(asset_code)
        assert provider.settings.group(lab.group).get("call_limit_minute") == 3, "barrier: the group's limit reached the price provider"
        await core.call_provider(provider, lambda: provider.get_current_value("MOCK", IdentifierType.TICKER, {}), timeout=10)

    await price_call()
    await price_call()
    assert counter.counts(GROUP_FAMILY, lab.group) == (2,) * 5, "barrier: the price provider counts on the group's row"

    assert (await _search("word", [lab.code]))[lab.code].status is SearchStatus.OK, "the third call of the window is the enricher's"
    assert counter.counts(GROUP_FAMILY, lab.group) == (3,) * 5
    assert lab.recorder.rows_at_start == [(3,) * 5]
    assert (await _search("word", [lab.code]))[lab.code].status is SearchStatus.RATE_LIMITED, "the price provider's two and its own one fill the window"
    _assert_429(await _refused(lambda: _route_test(lab.code)), MINUTE_WAIT)
    assert lab.recorder.count("search") == 1 and lab.recorder.count("recognize") == 0
    with pytest.raises(AssetCallLimitError):
        await price_call()
    assert counter.rows() == {(GROUP_FAMILY, lab.group)}, "one row for both families"
