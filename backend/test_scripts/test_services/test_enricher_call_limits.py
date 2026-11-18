"""The enrichers' read boundary counts and checks the calls of a plugin to its external service (project 76, lot K1).

Module under test: ``services/enrichers/refresh.py`` (``read_bindings``), with the counter of U1
(``platform/call_counter.py``: ``count_and_check``, ``call_owner``). Everything goes through ``read_bindings``: the
scheduler and «Aggiorna» reach the plugins only through it.

The contract pinned here:

1. **Counted, one per binding, before the read.** For a plugin whose class says ``calls_external_service`` True (read
   with ``getattr(plugin, "calls_external_service", False)``), every binding that goes to a real read — not served from
   the cache, not refused as not configured or as no such enricher — is counted once, in request order, with
   ``call_counter.count_and_check(*call_counter.call_owner(plugin, "enricher"))``, BEFORE the plugin's ``read`` runs.
2. **A full window.** When a window becomes full at the k-th binding (``CallLimitReached``), that binding and every
   following one of that plugin are NOT handed to ``read``: each comes out as ``ReadOutcome(status=ERROR,
   error_code=RATE_LIMITED, retry_after=<the counter's retry_after>, error_message=<the call limit, its window and
   limit>)``; the admitted ones are read as today (``read`` receives exactly them). A limit of 0: none read, all
   refused. These refusals are never cached.
3. **The owner.** A plugin reading a ``shares_credits`` group counts on ``("group", <name>)`` — the row an asset
   provider reading that group counts on too, so the group's limit holds both together; otherwise on
   ``("enricher", code)``.
4. **A counter that fails** (``count_and_check`` → None): the bindings are read (fail-open).
5. **Cached bindings** are served without counting: a second ``read_bindings`` of the same binding within the cache's
   TTL counts nothing more, and a cached binding takes no place in a window.
6. **A plugin with the flag False or absent** is read as today, never counted (beside a counted sibling).

Pure: no lane database, no server, no network. The counter and the plugin settings' reads share one private SQLite file
under ``tmp_path`` built with ``SQLModel.metadata.create_all`` (``call_counter.get_async_engine`` and
``runtime.get_async_engine`` patched); the counter's clock is a test clock patched into ``call_counter._utc`` (``NOW``,
moved forward by one test), so ``retry_after`` is exact. The test enrichers are ``MockEnricher`` subclasses put in
``EnricherRegistry``'s storage with ``monkeypatch.setitem`` (never through ``register``: they declare their own
``call_limit_<window>`` fields, their limits given as the fields' defaults); each records the identifiers its ``read``
received and, at the moment ``read`` starts, the counter row of its owner. The test groups (``register_group``) are
released at teardown; the asset side of section 3 uses a ``MockProvider`` subclass in the asset registry's storage and a
private ``Cooldowns``. The ``enricher_read`` cache is cleared before and after each test; every identifier and code is
unique (``k1`` prefix).

Red on HEAD f113b4549: ``read_bindings`` never counts. Each test asserts a count, a refusal or the counter's own warning
beside what it holds, so none is green on HEAD by the absence of the feature; the negatives (flag False or absent, not
configured, unknown code, cached) stand beside a counted sibling in the same test.

``call_counter.call_owner`` names the plugin by its ``provider_code``, or by its ``code`` when it has none (an
enricher): these doubles have no ``provider_code``, and the ``("enricher", code)`` row is pinned as the contract states.
Section 7 takes a class through ``EnricherRegistry.register`` itself: the five limit fields are given there, and the
count shows in the settings catalogue under the same family.
"""

from __future__ import annotations

import asyncio
import os
import re
import sqlite3
import threading
import uuid
from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import IdentifierType
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import User
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetCallLimitError
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.enricher_providers.mockenrich.plugin import MockEnricher
from backend.app.services.enrichers.base import RATE_LIMITED, EnricherBinding, EnricherReadStatus
from backend.app.services.enrichers.refresh import ReadOutcome, ReadRequest, read_bindings
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.enrichers.usable import NOT_CONFIGURED, configured_enricher
from backend.app.services.platform import call_counter, provider_cooldown
from backend.app.services.plugin_settings import runtime
from backend.app.services.plugin_settings import service as settings_service
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType, env_name, release_env_variables
from backend.app.services.plugin_settings.groups import SettingsGroup, all_groups, register_group, release_group
from backend.app.utils.runtime.cache import clear_cache
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

TEST_INSTANCE_KEY = "k1-enricher-call-limits-test-instance-key-0123456789"
CACHE_NAME = "enricher_read"
WINDOWS = ("minute", "hour", "day", "week", "month")
#: The bound on every read: against a hang, never a wait.
DEADLINE = 15.0
#: The counter's clock: a Tuesday, 13:45:30 UTC. The hour ends in 870 s, the minute in 30 s.
NOW = datetime(2026, 11, 17, 13, 45, 30, tzinfo=UTC)
HOUR_WAIT = 870.0
MINUTE_WAIT = 30.0
FAMILY = "enricher"


# =============================================================================
# HELPERS
# =============================================================================


def _code(label: str) -> str:
    return f"k1_{label}_{uuid.uuid4().hex[:8]}"


def _ident(tag: str) -> str:
    """An identifier no other test (and no other run within the cache's TTL) uses; none is one of mockenrich's specials."""
    return f"K1{tag.upper()}{uuid.uuid4().hex[:10].upper()}"


def _limit_field(window: str, default: int | None = None) -> PluginSettingField:
    return PluginSettingField(key=f"call_limit_{window}", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label=f"Calls per {window} (k1)", default=default, minimum=0)


@dataclass
class Recorder:
    """What a test enricher's ``read`` saw: the identifiers of each call, and its owner's counter row when it started."""

    calls: list[list[str]] = field(default_factory=list)
    rows_at_start: list[tuple[int, ...] | None] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def received(self) -> list[str]:
        with self.lock:
            return [identifier for call in self.calls for identifier in call]


@dataclass
class Clock:
    """The counter's clock: ``call_counter._utc(None)`` answers ``now``."""

    now: datetime = NOW


@dataclass(frozen=True)
class Counter:
    """The private file (counter and settings) and its engine."""

    path: Path
    engine: AsyncEngine
    clock: Clock

    def counts(self, family: str, code: str) -> tuple[int, ...] | None:
        """The five counts of the pair's row, through a plain ``sqlite3`` connection (any thread), or None."""
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


def _enricher_class(
    code: str,
    recorder: Recorder,
    *,
    counter: Counter | None = None,
    owner: tuple[str, str] | None = None,
    fields: tuple[PluginSettingField, ...] = (),
    groups: tuple[str, ...] = (),
    external: bool | None = True,
) -> type:
    """A test enricher: mockenrich's answers under ``code``, not test-only; ``external`` None leaves the flag undeclared.
    Its ``read`` records the identifiers it receives and, when it starts, the counter row of ``owner``."""
    snapshot_owner = owner if owner is not None else (FAMILY, code)

    def read(self, bindings, keys=None):
        with recorder.lock:
            recorder.calls.append([binding.identifier for binding in bindings])
            recorder.rows_at_start.append(counter.counts(*snapshot_owner) if counter is not None else None)
        yield from MockEnricher.read(self, bindings, keys)

    attributes: dict[str, Any] = {"code": code, "name": f"K1 {code}", "test_only": False, "settings_fields": fields, "settings_groups": groups, "read": read}
    if external is not None:
        attributes["calls_external_service"] = external
    return type(f"K1Enricher_{code}", (MockEnricher,), attributes)


def _install(monkeypatch: pytest.MonkeyPatch, plugin_class: type) -> None:
    EnricherRegistry.auto_discover()
    monkeypatch.setitem(EnricherRegistry._get_storage(), EnricherRegistry._normalize_lookup_code(plugin_class.code), plugin_class)


async def _bound_limit(code: str, window: str, group: str | None = None) -> Any:
    """Barrier: the limit the instance of ``code`` sees, as ``read_bindings`` gets it (``configured_enricher``)."""
    plugin, missing = await configured_enricher(code)
    assert plugin is not None and not missing, f"barrier: {code} is served and configured ({missing})"
    settings = plugin.settings.group(group) if group is not None else plugin.settings
    return settings.get(f"call_limit_{window}")


def _requests(code: str, identifiers: Sequence[str]) -> list[ReadRequest]:
    return [ReadRequest(owner=index, code=code, binding=EnricherBinding(identifier_type="ISIN", identifier=identifier)) for index, identifier in enumerate(identifiers)]


async def _read(requests: Sequence[ReadRequest], *, use_cache: bool = True) -> list[ReadOutcome]:
    """Every outcome of ``read_bindings``, consumed to its end under ``DEADLINE``; exactly one per request."""

    async def consume() -> list[ReadOutcome]:
        return [outcome async for outcome in read_bindings(requests, use_cache=use_cache)]

    outcomes = await asyncio.wait_for(consume(), DEADLINE)
    assert len(outcomes) == len(requests), f"one outcome per request: {outcomes}"
    return outcomes


def _one(outcomes: Sequence[ReadOutcome], code: str, identifier: str) -> ReadOutcome:
    found = [outcome for outcome in outcomes if outcome.code == code and outcome.binding.identifier == identifier]
    assert len(found) == 1, f"exactly one outcome for {code} / {identifier}: {outcomes}"
    return found[0]


def _assert_refused(outcome: ReadOutcome, *, window: str, limit: int, retry_after: float) -> None:
    """A binding refused by a full window: RATE_LIMITED, the counter's wait, a message naming the limit, never cached."""
    assert (outcome.status, outcome.error_code) == (EnricherReadStatus.ERROR, RATE_LIMITED), f"refused for the call limit: {outcome}"
    assert outcome.retry_after == pytest.approx(retry_after), f"the counter's own wait: {outcome}"
    assert outcome.from_cache is False
    message = outcome.error_message or ""
    assert "limit" in message.lower(), f"the message names the call limit: {message!r}"
    assert re.search(rf"\b{window}\b", message), f"the message names the window {window}: {message!r}"
    # The plugin's code (a uuid tail) and a wait such as 30.0 never count as the limit
    bare = re.sub(r"k1_\w+", "", message)
    assert re.search(rf"(?<![\d.]){limit}(?![\d.])", bare), f"the message names the limit {limit}: {message!r}"


def _assert_read(outcome: ReadOutcome) -> None:
    assert outcome.status is EnricherReadStatus.OK and outcome.from_cache is False, f"read by the plugin: {outcome}"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Test mode, a test instance key and data directory, every enricher served, pauses on; no k1 group left behind."""
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
    yield
    for name in [name for name in all_groups() if name.startswith("k1")]:
        release_group(name)


@pytest.fixture(autouse=True)
def _fresh_read_cache() -> Iterator[None]:
    """The read cache is process-wide: empty before and after each test."""
    clear_cache(CACHE_NAME)
    yield
    clear_cache(CACHE_NAME)


@pytest.fixture
def cooldowns(monkeypatch: pytest.MonkeyPatch) -> Cooldowns:
    """A private instance on a still clock, without jitter, in place of the process's (the asset side of section 3)."""
    private = Cooldowns(60, 3600, jitter=0.0, clock=lambda: 1_000_000.0)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


@pytest_asyncio.fixture
async def counter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Counter]:
    """A private file with the whole schema behind ``call_counter.get_async_engine`` and the plugin settings' reads; the
    counter's clock on ``Clock`` (``NOW``)."""
    path = tmp_path / "k1_counters.db"
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


# =============================================================================
# 1. COUNTED, ONE PER BINDING, BEFORE THE READ
# =============================================================================


@pytest.mark.asyncio
async def test_k1_every_binding_read_is_counted_once_before_the_read(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """1: three bindings, an hour limit of 10: all three read in one call, the row ``("enricher", code)`` at 3 in every
    window — already at 3 when ``read`` started."""
    print_section("K1 1: one count per binding, before the read")
    code, recorder = _code("counted"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, counter=counter, fields=(_limit_field("hour", default=10),)))
    assert await _bound_limit(code, "hour") == 10

    identifiers = [_ident("a"), _ident("b"), _ident("c")]
    outcomes = await _read(_requests(code, identifiers))

    for identifier in identifiers:
        _assert_read(_one(outcomes, code, identifier))
    assert recorder.calls == [identifiers], "one read, the bindings in request order"
    assert counter.counts(FAMILY, code) == (3,) * 5, "one count per binding read, on the enricher's own row"
    assert recorder.rows_at_start == [(3,) * 5], "counted BEFORE the plugin's read ran"
    assert counter.rows() == {(FAMILY, code)}
    print_success("three bindings, three counts, before the read")


# =============================================================================
# 2. A FULL WINDOW
# =============================================================================


@pytest.mark.asyncio
async def test_k1_a_full_window_hands_only_the_admitted_bindings_to_read(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """2: an hour limit of 2, four bindings: ``read`` receives exactly the first two; the third and the fourth come out
    RATE_LIMITED with the hour's wait (870 s), a message naming the call limit, «hour» and 2; the row stays at 2."""
    print_section("K1 2: a full window")
    code, recorder = _code("full"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, counter=counter, fields=(_limit_field("hour", default=2),)))
    assert await _bound_limit(code, "hour") == 2

    identifiers = [_ident("a"), _ident("b"), _ident("c"), _ident("d")]
    outcomes = await _read(_requests(code, identifiers))

    assert recorder.received() == identifiers[:2], "the plugin receives the admitted bindings only, in request order"
    for identifier in identifiers[:2]:
        _assert_read(_one(outcomes, code, identifier))
    for identifier in identifiers[2:]:
        _assert_refused(_one(outcomes, code, identifier), window="hour", limit=2, retry_after=HOUR_WAIT)
    assert counter.counts(FAMILY, code) == (2,) * 5, "a refused binding is not counted"
    print_success("two read, two refused with the counter's wait")


@pytest.mark.asyncio
async def test_k1_a_limit_of_zero_reads_no_binding(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """2: ``call_limit_minute = 0`` stops the plugin: no binding reaches ``read``, both come out RATE_LIMITED with the
    minute's wait (30 s); nothing counted."""
    code, recorder = _code("stopped"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, counter=counter, fields=(_limit_field("minute", default=0),)))
    assert await _bound_limit(code, "minute") == 0

    identifiers = [_ident("a"), _ident("b")]
    outcomes = await _read(_requests(code, identifiers))

    assert recorder.received() == [], "a stopped plugin receives no binding"
    for identifier in identifiers:
        _assert_refused(_one(outcomes, code, identifier), window="minute", limit=0, retry_after=MINUTE_WAIT)
    assert counter.counts(FAMILY, code) is None


@pytest.mark.asyncio
async def test_k1_a_refusal_for_the_call_limit_is_never_cached(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """2: a minute limit of 1, bindings A and B: A read, B refused. Read again in the same minute, B is refused again
    (not from the cache, not handed to ``read``); in the next minute B reaches ``read`` and comes out ``ok``: the
    refusal was never kept as B's answer."""
    print_section("K1 2: a refusal is never cached")
    code, recorder = _code("nocache"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, counter=counter, fields=(_limit_field("minute", default=1),)))
    assert await _bound_limit(code, "minute") == 1
    first, second = _ident("a"), _ident("b")

    outcomes = await _read(_requests(code, [first, second]))
    _assert_read(_one(outcomes, code, first))
    _assert_refused(_one(outcomes, code, second), window="minute", limit=1, retry_after=MINUTE_WAIT)

    again = await _read(_requests(code, [second]))
    _assert_refused(_one(again, code, second), window="minute", limit=1, retry_after=MINUTE_WAIT)
    assert recorder.received() == [first], "the full minute still keeps B from the plugin"

    counter.clock.now = NOW + timedelta(minutes=1)
    later = await _read(_requests(code, [second]))
    _assert_read(_one(later, code, second))
    assert recorder.received() == [first, second], "in the next minute B is read"
    assert counter.counts(FAMILY, code) == (1, 2, 2, 2, 2), "A in the first minute, B in the next"
    print_success("refused twice, then read in the next minute")


# =============================================================================
# 3. THE OWNER: A CREDIT-SHARING GROUP
# =============================================================================


def _asset_plugin_class(code: str, groups: tuple[str, ...]) -> type:
    """A test asset provider: mockprov's answers under ``code``, not test-only, counted, reading ``groups``."""
    return type(
        f"K1Asset_{code}",
        (MockProvider,),
        {"provider_code": property(lambda self: code), "provider_name": f"K1 {code}", "test_only": False, "calls_external_service": True, "settings_fields": (), "settings_groups": groups},
    )


@pytest.mark.asyncio
async def test_k1_an_enricher_and_an_asset_plugin_of_one_credit_sharing_group_count_on_one_row(counter: Counter, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """3: an asset provider and an enricher read one ``shares_credits`` group, minute limit 3. One asset call, then the
    enricher's three bindings: two admitted, the third refused by the group's window. One row, the group's, at 3; the
    asset provider's next call is refused by the same window."""
    print_section("K1 3: one group, one row, one limit for both families")
    group = f"k1_credits_{uuid.uuid4().hex[:8]}"
    register_group(SettingsGroup(name=group, label="K1 credits", shares_credits=True, fields=(_limit_field("minute", default=3),)))
    asset_code, enricher_code, recorder = _code("asset"), _code("member"), Recorder()
    AssetProviderRegistry.auto_discover()
    monkeypatch.setitem(AssetProviderRegistry._get_storage(), AssetProviderRegistry._normalize_lookup_code(asset_code), _asset_plugin_class(asset_code, (group,)))
    _install(monkeypatch, _enricher_class(enricher_code, recorder, counter=counter, owner=("group", group), groups=(group,)))
    assert await _bound_limit(enricher_code, "minute", group=group) == 3

    async def asset_call() -> int:
        provider = await core.configured_provider(asset_code)
        assert provider.settings.group(group).get("call_limit_minute") == 3, "barrier: the group's limit reached the asset provider"
        calls = 0

        def fn():
            nonlocal calls
            calls += 1
            return provider.get_current_value("MOCK", IdentifierType.TICKER, {})

        await core.call_provider(provider, fn, timeout=10)
        return calls

    assert await asset_call() == 1
    assert counter.counts("group", group) == (1,) * 5, "barrier: the asset provider counts on the group's row"

    identifiers = [_ident("a"), _ident("b"), _ident("c")]
    outcomes = await _read(_requests(enricher_code, identifiers))
    assert recorder.received() == identifiers[:2], "the group's window admits two more calls, whoever makes them"
    for identifier in identifiers[:2]:
        _assert_read(_one(outcomes, enricher_code, identifier))
    _assert_refused(_one(outcomes, enricher_code, identifiers[2]), window="minute", limit=3, retry_after=MINUTE_WAIT)
    assert recorder.rows_at_start == [(3,) * 5], "the enricher's two counted on the group's row before its read"
    assert counter.rows() == {("group", group)}, "one row, the group's; none of the plugins'"
    assert counter.counts("group", group) == (3,) * 5

    with pytest.raises(AssetCallLimitError) as refused:
        await asset_call()
    assert refused.value.details == {"reason": "call_limit", "window": "minute", "limit": 3}, "the asset provider meets the window the enricher filled"
    print_success("asset 1 + enricher 2 on one row; both refused past it")


# =============================================================================
# 4. A COUNTER THAT FAILS
# =============================================================================


@pytest.mark.asyncio
async def test_k1_a_counter_that_fails_lets_every_binding_be_read(counter: Counter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """4: the counter's engine on a file in a missing folder (the settings still on the good file): ``count_and_check``
    returns None and warns for this enricher; all three bindings are read although the hour limit is 1."""
    print_section("K1 4: a failing counter lets the read go")
    code, recorder = _code("dbdown"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, fields=(_limit_field("hour", default=1),)))
    assert await _bound_limit(code, "hour") == 1
    broken = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'missing-folder' / 'counters.db'}", poolclass=NullPool)
    monkeypatch.setattr(call_counter, "get_async_engine", lambda: broken)

    identifiers = [_ident("a"), _ident("b"), _ident("c")]
    try:
        with capture_logs() as events:
            outcomes = await _read(_requests(code, identifiers))
    finally:
        await broken.dispose()

    for identifier in identifiers:
        _assert_read(_one(outcomes, code, identifier))
    assert recorder.received() == identifiers, "fail-open: every binding read"
    warned = [event for event in events if event.get("log_level") == "warning" and event.get("plugin") == code and event.get("family") == FAMILY]
    assert warned, f"barrier: the counter was asked for ('enricher', {code}) and said it failed: {events}"
    assert counter.rows() == set(), "nothing reached the good file's counter"
    print_success("counter down, three bindings read, its warning logged")


# =============================================================================
# 5. CACHED BINDINGS
# =============================================================================


@pytest.mark.asyncio
async def test_k1_a_cached_binding_is_served_without_counting(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """5: an hour limit of 2. A read alone: count 1. Then A, B, C: A from the cache (no count, no place in the window),
    B read (count 2), C refused. Then A and B again: both from the cache, the count still 2, no read."""
    print_section("K1 5: the cache counts nothing")
    code, recorder = _code("cached"), Recorder()
    _install(monkeypatch, _enricher_class(code, recorder, counter=counter, fields=(_limit_field("hour", default=2),)))
    assert await _bound_limit(code, "hour") == 2
    first, second, third = _ident("a"), _ident("b"), _ident("c")

    outcomes = await _read(_requests(code, [first]))
    _assert_read(_one(outcomes, code, first))
    assert counter.counts(FAMILY, code) == (1,) * 5, "the first read is counted"

    outcomes = await _read(_requests(code, [first, second, third]))
    assert _one(outcomes, code, first).from_cache is True, "barrier: A served from the cache"
    _assert_read(_one(outcomes, code, second))
    _assert_refused(_one(outcomes, code, third), window="hour", limit=2, retry_after=HOUR_WAIT)
    assert recorder.calls == [[first], [second]], "A never read twice, C never read"
    assert counter.counts(FAMILY, code) == (2,) * 5

    outcomes = await _read(_requests(code, [first, second]))
    assert all(outcome.from_cache and outcome.status is EnricherReadStatus.OK for outcome in outcomes), f"both from the cache: {outcomes}"
    assert counter.counts(FAMILY, code) == (2,) * 5, "a cached binding counts nothing"
    assert recorder.calls == [[first], [second]]
    print_success("cached bindings served, uncounted")


# =============================================================================
# 6. NOT COUNTED: FLAG FALSE OR ABSENT, NOT CONFIGURED, UNKNOWN
# =============================================================================


@pytest.mark.asyncio
async def test_k1_a_plugin_that_does_not_call_out_is_never_counted(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """6: in one ``read_bindings``, a counted sibling (hour limit 1, two bindings: one read, one refused) beside a
    plugin with the flag False and one without the flag, both with an hour limit of 0: theirs are all read, no row of
    theirs."""
    print_section("K1 6: flag False or absent, never counted")
    counted, local, silent = _code("sibling"), _code("local"), _code("noflag")
    counted_rec, local_rec, silent_rec = Recorder(), Recorder(), Recorder()
    _install(monkeypatch, _enricher_class(counted, counted_rec, counter=counter, fields=(_limit_field("hour", default=1),)))
    _install(monkeypatch, _enricher_class(local, local_rec, fields=(_limit_field("hour", default=0),), external=False))
    _install(monkeypatch, _enricher_class(silent, silent_rec, fields=(_limit_field("hour", default=0),), external=None))
    assert "calls_external_service" not in vars(EnricherRegistry.get_plugin(silent)), "barrier: the flag is not declared on that class"
    for code, limit in ((counted, 1), (local, 0), (silent, 0)):
        assert await _bound_limit(code, "hour") == limit

    ids = {code: [_ident(f"{tag}1"), _ident(f"{tag}2")] for code, tag in ((counted, "s"), (local, "l"), (silent, "n"))}
    outcomes = await _read([request for code in (counted, local, silent) for request in _requests(code, ids[code])])

    assert counted_rec.received() == ids[counted][:1]
    _assert_read(_one(outcomes, counted, ids[counted][0]))
    _assert_refused(_one(outcomes, counted, ids[counted][1]), window="hour", limit=1, retry_after=HOUR_WAIT)
    for code, recorder in ((local, local_rec), (silent, silent_rec)):
        assert recorder.received() == ids[code], f"{code} is read as today"
        for identifier in ids[code]:
            _assert_read(_one(outcomes, code, identifier))
    assert counter.rows() == {(FAMILY, counted)}, "only the plugin that calls out has a row"
    print_success("the sibling counted and limited; the others read, uncounted")


@pytest.mark.asyncio
async def test_k1_not_configured_and_unknown_enrichers_are_not_counted(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """1: a binding refused as not configured or as no such enricher never reaches the counter; a counted sibling in the
    same call is counted for its own binding."""
    counted, unconfigured, unknown = _code("sibling"), _code("noconfig"), _code("nosuch")
    counted_rec, unconfigured_rec = Recorder(), Recorder()
    required = PluginSettingField(key="k1_token", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="K1 token", required=True)
    _install(monkeypatch, _enricher_class(counted, counted_rec, counter=counter, fields=(_limit_field("hour", default=5),)))
    _install(monkeypatch, _enricher_class(unconfigured, unconfigured_rec, fields=(required, _limit_field("hour", default=5))))
    assert await _bound_limit(counted, "hour") == 5
    _plugin, missing = await configured_enricher(unconfigured)
    assert missing == ("k1_token",), f"barrier: {unconfigured} lacks its required setting"

    ids = {counted: [_ident("s")], unconfigured: [_ident("u1"), _ident("u2")], unknown: [_ident("x")]}
    outcomes = await _read([request for code in (counted, unconfigured, unknown) for request in _requests(code, ids[code])])

    _assert_read(_one(outcomes, counted, ids[counted][0]))
    for identifier in ids[unconfigured]:
        assert _one(outcomes, unconfigured, identifier).error_code == NOT_CONFIGURED
    assert _one(outcomes, unknown, ids[unknown][0]).status is EnricherReadStatus.ERROR
    assert unconfigured_rec.received() == []
    assert counter.rows() == {(FAMILY, counted)}, "only the binding that went to a real read is counted"
    assert counter.counts(FAMILY, counted) == (1,) * 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# =============================================================================
# 7. A REAL REGISTRATION: THE FIELDS GIVEN, THE COUNT IN THE CATALOGUE
# =============================================================================


@pytest.mark.asyncio
async def test_k1_a_flagged_enricher_registered_gets_the_five_limits_and_its_count_shows_in_the_catalogue(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """7: a class that declares nothing and says ``calls_external_service``, through ``EnricherRegistry.register``: it gets
    the core's five limit fields, its variable binds the hour limit (1), one binding of two is read, and the settings
    catalogue's ``call_usage`` of ``("enricher", code)`` shows that count, the limit and the full window."""
    code, recorder = _code("registered"), Recorder()
    plugin_class = _enricher_class(code, recorder, counter=counter)
    EnricherRegistry.auto_discover()
    monkeypatch.setitem(EnricherRegistry._get_storage(), code, None)  # restored (removed) at teardown
    monkeypatch.setenv(env_name(FAMILY, code, "call_limit_hour"), "1")
    try:
        EnricherRegistry.register(plugin_class)

        assert [declared.key for declared in plugin_class.settings_fields] == [f"call_limit_{window}" for window in WINDOWS], "the core's five limits"
        assert await _bound_limit(code, "hour") == 1, "barrier: the variable binds the hour limit"
        first, second = _ident("a"), _ident("b")
        outcomes = await _read(_requests(code, [first, second]))
        _assert_read(_one(outcomes, code, first))
        _assert_refused(_one(outcomes, code, second), window="hour", limit=1, retry_after=HOUR_WAIT)

        async with AsyncSession(counter.engine, expire_on_commit=False) as session:
            admin = User(username=f"k1admin{uuid.uuid4().hex[:6]}", email="k1admin@example.test", hashed_password="$argon2id$test", is_superuser=True)
            session.add(admin)
            await session.commit()
            catalogue = await settings_service.read_catalogue(session, admin, family=FAMILY, plugin_code=code)
        entries = [entry for entry in catalogue.plugins if entry.plugin_code == code]
        assert len(entries) == 1 and entries[0].family == FAMILY, f"one {FAMILY} entry: {catalogue.plugins}"
        usage = entries[0].call_usage
        assert usage is not None and (usage.family, usage.plugin_code) == (FAMILY, code)
        hour = next(window for window in usage.windows if window.window == "hour")
        assert (hour.count, hour.limit, hour.full) == (1, 1, True)
    finally:
        release_env_variables(FAMILY, code)
    print_success("registered: five limits, the count in the catalogue")
