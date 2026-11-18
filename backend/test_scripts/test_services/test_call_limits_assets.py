# ruff: noqa: PLC0415 — the U2 names are imported inside each test on purpose: red on HEAD, every test fails for its own reason
"""The asset boundary counts and checks the calls of a plugin to its external service (project 76, lot U2; plan 76 §3.5).

Modules under test: ``services/assets/core.py`` (``call_provider``, the new ``call_owner``), ``services/assets/base.py``
(``AssetSourceProvider.calls_external_service``, the new ``AssetCallLimitError``), ``services/plugin_settings/groups``
(``SettingsGroup.shares_credits``, ``validate_plugin_groups``), and the counter of U1 (``platform/call_counter.py``).
The effects through price, refresh, search, probe and scheduler are pinned in ``test_rate_limit_results.py``
(``test_u2_…``), whose private database already stands behind every engine those services ask for.

The contract pinned here:

1. **The flag.** ``AssetSourceProvider.calls_external_service = True`` (class attribute of the base). The shipped
   providers that reach the network keep True (yfinance, justetf, borsa_italiana, css_scraper);
   ``ScheduledInvestmentProvider`` and the test double ``MockProvider`` declare False in their own class.
2. **Shared credits.** ``SettingsGroup.shares_credits: bool = False``; ``validate_plugin_groups(plugin_class,
   family=…)`` raises ``SettingsDeclarationError`` for a plugin reading two groups with ``shares_credits=True`` (one,
   beside any number of plain groups, is accepted); the registry refuses such a plugin.
3. **The owner of the count** (``core.call_owner(provider) -> (family, code, CallLimits)``, sync): a provider reading a
   ``shares_credits`` group → ``("group", <name>, limits of the group's bound settings)``; otherwise ``("asset",
   provider_code, limits of its own bound settings)``. A limit is the plain integer field ``call_limit_<window>`` when
   declared and valued; undeclared or without value → None; 0 stays 0 (stopped, never «no limit»). A plain group's limit
   fields are not read.
4. **The order in ``call_provider``**: a bare test double is called, never counted; ``NOT_CONFIGURED`` and a running
   pause refuse before the counter; ``calls_external_service`` False is called, never counted; otherwise
   ``call_counter.count_and_check`` counts +1 BEFORE the call leaves, even when the call then fails (another error, a
   timeout, a refusal for too many requests), one count per call.
5. **A full window** (``CallLimitReached``): the provider function is never called; ``record_limit_pause`` pauses it
   exactly until the window ends, on the limit's own key (U2b); ``AssetCallLimitError`` (subclass of ``AssetRateLimitedError``,
   ``error_code="RATE_LIMITED"``) leaves with ``retry_after`` = the pause recorded (the counter's own wait when pauses are
   off), ``scope`` = the call's, ``details == {"reason": "call_limit", "window": …, "limit": …}``. The next call meets
   the pause and does not reach the counter. Limit 0 refuses the first call.
6. **A counter that fails** (``count_and_check`` → None, its warning logged): the call goes.
7. **The group owner**: two plugins reading one ``shares_credits`` group count on ONE row (``family="group"``, the
   group's name) and its limit holds both together; the pause stays the refused plugin's own
   (``("asset", code, scope)``). A plugin reading a plain group counts on its own row.

Pure: no lane database, no server, no network. The counter writes to a private SQLite file under ``tmp_path`` built
with ``SQLModel.metadata.create_all`` (``call_counter.get_async_engine`` patched); the counter's clock is frozen at
``NOW`` by patching ``call_counter._utc`` (``call_provider`` passes no ``now``), so the windows never roll mid-test and
``retry_after`` is exact. The pauses are a private ``Cooldowns`` on a fake clock, without jitter, in place of
``provider_cooldown.PROVIDER_COOLDOWNS``. Settings are bound two ways: ``BoundSettings`` given directly to the instance
(``bind_settings``) for the boundary and the owner (sections 3–6); for the group owner (7), through the real
``core.configured_provider`` on the asset registry, the plugin classes put in its storage with ``monkeypatch.setitem``,
the groups registered with ``register_group`` (released at teardown), ``runtime.get_async_engine`` patched to the same
private file, and the limits given as the fields' defaults. Every code and group name starts with ``u2``.

Red on HEAD f3fbd4b86: no ``calls_external_service``, no ``shares_credits``, no ``call_owner``, no
``AssetCallLimitError``, and ``call_provider`` never counts. Each negative («never counted») stands beside a positive
control in the same test (a counted sibling), so no test is green on HEAD by the absence of the feature.
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import sqlite3
import threading
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import IdentifierType
from backend.app.db.base import SQLModel  # imports every model
from backend.app.services.asset_source_providers.mockprov.plugin import RATE_LIMITED_PARAM, MockProvider
from backend.app.services.asset_source_providers.scheduled_investment.plugin import ScheduledInvestmentProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform import call_counter, provider_cooldown
from backend.app.services.platform.provider_cooldown import record_refusal
from backend.app.services.plugin_settings import runtime
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingsDeclarationError, SettingType
from backend.app.services.plugin_settings.groups import SettingsGroup, all_groups, register_group, release_group, validate_plugin_groups
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

BASE_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS"
MAX_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS"
TEST_INSTANCE_KEY = "u2-call-limits-assets-test-instance-key-0123456789"
START = 1_000_000.0
WINDOWS = ("minute", "hour", "day", "week", "month")
#: The counter's frozen clock: a Tuesday, 13:45:30 UTC. The hour ends in 870 s, the minute in 30 s.
NOW = datetime(2026, 11, 17, 13, 45, 30, tzinfo=UTC)
HOUR_WAIT = 870.0
MINUTE_WAIT = 30.0
#: The base pause of the private ``Cooldowns``: a counter's wait shorter than it is floored to it.
BASE_PAUSE = 60.0
SCOPE = "api.u2.example"
#: The test-only asset double that counts its calls (U4, for the limit's API and E2E tests): left out of the flags pin below
COUNTING_DOUBLE = "mockcount"
SHIPPED_FLAGS = {"yfinance": True, "justetf": True, "borsa_italiana": True, "css_scraper": True, "coingecko": True, "scheduled_investment": False, "mockprov": False}


class FakeClock:
    """A clock that moves only when the test moves it."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class _Calls:
    """The ``fn`` the boundary receives: counts the calls it let through, then builds the plugin's coroutine."""

    def __init__(self, make: Callable[[], object]) -> None:
        self.count = 0
        self._make = make

    def __call__(self):
        self.count += 1
        return self._make()


class _NotAPlugin:
    """A test double that is no plugin: no settings mixin, called as it is."""

    provider_code = "u2_bare_double"


def _code(label: str) -> str:
    return f"u2_{label}_{uuid.uuid4().hex[:8]}"


def _limit_field(window: str, default: int | None = None) -> PluginSettingField:
    return PluginSettingField(key=f"call_limit_{window}", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label=f"Calls per {window} (u2)", default=default, minimum=0)


def _plugin_class(code: str, *, fields: tuple[PluginSettingField, ...] = (), groups: tuple[str, ...] = (), external: bool = True, bulk: bool = False) -> type:
    """A test plugin: mockprov's answers under ``code``, not test-only, the flag, fields and groups given."""
    return type(
        f"U2Plugin_{code}",
        (MockProvider,),
        {
            "provider_code": property(lambda self: code),
            "provider_name": f"U2 {code}",
            "test_only": False,
            "calls_external_service": external,
            "settings_fields": fields,
            "settings_groups": groups,
            "supports_bulk_current": bulk,
        },
    )


def _bind(plugin: AssetSourceProvider, values: dict[str, Any] | None = None, groups: dict[str, tuple[SettingsGroup, dict[str, Any]]] | None = None) -> AssetSourceProvider:
    """Bind ``values`` (the plugin's own plain fields) and each group's values, as the core would."""
    bound_groups = {name: BoundSettings(group.fields, group_values, {}) for name, (group, group_values) in (groups or {}).items()}
    # A fingerprint of the values, as the core's binding has one (U2b: the limit pause's key carries it)
    fingerprint = repr((sorted((values or {}).items()), sorted((name, sorted(group_values.items())) for name, (_group, group_values) in (groups or {}).items())))
    plugin.bind_settings(BoundSettings(type(plugin).settings_fields, values or {}, {}, groups=bound_groups, fingerprint=fingerprint))
    return plugin


def _limit_key(code: str, plugin: AssetSourceProvider) -> tuple:
    """U2b: the key of a limit pause, never the source's: the settings fingerprint in it."""
    return ("asset", code, ("call-limit", plugin.settings.fingerprint))


def _current(plugin: AssetSourceProvider, params: dict | None = None) -> _Calls:
    return _Calls(lambda: plugin.get_current_value("MOCK", IdentifierType.TICKER, params or {}))


def _state(cooldowns: Cooldowns) -> dict:
    return {state.key: (state.refusals, state.remaining) for state in cooldowns.snapshot()}


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Pauses on (base 60 s, max 3600 s), test mode, a test instance key and data directory; no u2 group left behind."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(BASE_VARIABLE, "60")
    monkeypatch.setenv(MAX_VARIABLE, "3600")
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", TEST_INSTANCE_KEY)
    yield
    for name in [name for name in all_groups() if name.startswith("u2")]:
        release_group(name)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def cooldowns(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> Cooldowns:
    """A private instance on the fake clock, without jitter, in place of the process's."""
    private = Cooldowns(60, 3600, jitter=0.0, clock=clock)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


@dataclass(frozen=True)
class Counter:
    """The counter's private file and its engine."""

    path: Path
    engine: AsyncEngine

    def counts(self, family: str, code: str) -> tuple[int, ...] | None:
        """The five counts of the pair's row, read through a plain ``sqlite3`` connection (any thread), or None."""
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


def _freeze_counter_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """``call_counter._utc(None)`` answers ``NOW``: the windows of every count are those of ``NOW``."""
    real = call_counter._utc
    monkeypatch.setattr(call_counter, "_utc", lambda now=None: real(NOW if now is None else now))


@pytest_asyncio.fixture
async def counter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Counter]:
    """A private file with the whole schema behind ``call_counter.get_async_engine`` (and the plugin settings' reads);
    the counter's clock frozen at ``NOW``."""
    path = tmp_path / "u2_counters.db"
    sync_engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    monkeypatch.setattr(call_counter, "get_async_engine", lambda: engine)
    monkeypatch.setattr(runtime, "get_async_engine", lambda: engine)
    _freeze_counter_clock(monkeypatch)
    try:
        yield Counter(path, engine)
    finally:
        await engine.dispose()


# =============================================================================
# 1. THE FLAG
# =============================================================================


def test_u2_the_base_declares_calls_external_service_true():
    """1: the base class owns the flag, True: a plugin that says nothing is counted."""
    assert "calls_external_service" in vars(AssetSourceProvider), "AssetSourceProvider declares no calls_external_service"
    assert AssetSourceProvider.calls_external_service is True


def test_u2_every_shipped_asset_provider_says_whether_it_calls_out():
    """1: the shipped providers, pinned: the network ones True, the scheduled investment and mockprov False in their own
    class; every test-only provider of the package False; no shipped provider left out of the pin. ``mockcount`` (U4) is
    the one test-only double that counts, on purpose: its flag and its fields are pinned in ``test_call_limit_settings.py``."""
    AssetProviderRegistry.auto_discover()
    shipped = {code: cls for code, cls in AssetProviderRegistry._get_storage().items() if cls.__module__.startswith("backend.app.services.asset_source_providers.") and code != COUNTING_DOUBLE}
    assert set(shipped) == set(SHIPPED_FLAGS), f"the shipped asset providers changed: pin the new one's flag here: {sorted(shipped)}"
    flags = {code: getattr(cls, "calls_external_service", "<missing>") for code, cls in shipped.items()}
    assert flags == SHIPPED_FLAGS
    for cls in (ScheduledInvestmentProvider, MockProvider):
        assert vars(cls).get("calls_external_service") is False, f"{cls.__name__} declares False in its own class"
    assert all(flags[code] is False for code, cls in shipped.items() if getattr(cls, "test_only", False)), "a test-only double never counts"


# =============================================================================
# 2. SHARED CREDITS
# =============================================================================


def test_u2_a_settings_group_shares_no_credits_by_default():
    """2: ``shares_credits`` is a field of the dataclass, False unless declared."""
    names = {field.name: field.default for field in dataclasses.fields(SettingsGroup)}
    assert names.get("shares_credits", "<missing>") is False
    assert SettingsGroup(name="u2_plain_default", label="U2").shares_credits is False


def test_u2_a_plugin_reading_two_credit_sharing_groups_is_refused():
    """2: two ``shares_credits`` groups → ``SettingsDeclarationError`` (the function and the registry); one beside a plain
    group is accepted; two plain groups too."""
    print_section("U2 2: two credit-sharing groups refused")
    register_group(SettingsGroup(name="u2_share_a", label="U2 share A", shares_credits=True, fields=(_limit_field("hour"),)))
    register_group(SettingsGroup(name="u2_share_b", label="U2 share B", shares_credits=True, fields=(_limit_field("day"),)))
    register_group(SettingsGroup(name="u2_plain_c", label="U2 plain C", fields=(_limit_field("month"),)))
    register_group(SettingsGroup(name="u2_plain_d", label="U2 plain D"))

    two = _plugin_class(_code("two"), groups=("u2_share_a", "u2_share_b"))
    with pytest.raises(SettingsDeclarationError):
        validate_plugin_groups(two, family="asset")
    with pytest.raises(SettingsDeclarationError):
        AssetProviderRegistry._validate_settings_declaration(two)

    validate_plugin_groups(_plugin_class(_code("one"), groups=("u2_share_a", "u2_plain_c")), family="asset")
    validate_plugin_groups(_plugin_class(_code("plain"), groups=("u2_plain_c", "u2_plain_d")), family="asset")
    print_success("two refused, one accepted beside a plain group")


# =============================================================================
# 3. THE OWNER OF THE COUNT
# =============================================================================


def test_u2_call_owner_of_a_plugin_is_itself_with_its_own_limits():
    """3: own fields minute=3, hour=0 (stopped, not «no limit»), day declared without value, week and month undeclared."""
    from backend.app.services.assets.core import call_owner

    code = _code("own")
    plugin = _bind(_plugin_class(code, fields=(_limit_field("minute"), _limit_field("hour"), _limit_field("day")))(), {"call_limit_minute": 3, "call_limit_hour": 0})
    assert (plugin.settings.get("call_limit_minute"), plugin.settings.get("call_limit_hour")) == (3, 0), "barrier: the values reached the instance"

    assert call_owner(plugin) == ("asset", code, call_counter.CallLimits(minute=3, hour=0, day=None, week=None, month=None))


def test_u2_call_owner_without_limit_fields_has_no_limit():
    from backend.app.services.assets.core import call_owner

    code = _code("nolimits")
    assert call_owner(_bind(_plugin_class(code)())) == ("asset", code, call_counter.CallLimits())


def test_u2_call_owner_of_a_plugin_reading_a_credit_sharing_group_is_the_group():
    """3: the group's limits, never the plugin's; a plain group beside it changes nothing."""
    from backend.app.services.assets.core import call_owner

    shared = SettingsGroup(name="u2_owner_share", label="U2 owner share", shares_credits=True, fields=(_limit_field("minute"), _limit_field("hour")))
    plain = SettingsGroup(name="u2_owner_plain", label="U2 owner plain", fields=(_limit_field("day"),))
    register_group(shared)
    register_group(plain)
    plugin = _bind(_plugin_class(_code("grouped"), groups=("u2_owner_plain", "u2_owner_share"))(), {}, {"u2_owner_share": (shared, {"call_limit_minute": 5}), "u2_owner_plain": (plain, {"call_limit_day": 1})})
    assert plugin.settings.group("u2_owner_share").get("call_limit_minute") == 5, "barrier: the group's value reached the instance"

    assert call_owner(plugin) == ("group", "u2_owner_share", call_counter.CallLimits(minute=5))


def test_u2_call_owner_ignores_the_limits_of_a_plain_group():
    """3: a group without ``shares_credits`` is no owner: the plugin's own limits, the group's ignored."""
    from backend.app.services.assets.core import call_owner

    plain = SettingsGroup(name="u2_owner_plain_only", label="U2 owner plain only", fields=(_limit_field("hour"),))
    register_group(plain)
    code = _code("plaingroup")
    plugin = _bind(_plugin_class(code, fields=(_limit_field("minute"),), groups=("u2_owner_plain_only",))(), {"call_limit_minute": 2}, {"u2_owner_plain_only": (plain, {"call_limit_hour": 1})})

    assert call_owner(plugin) == ("asset", code, call_counter.CallLimits(minute=2))


# =============================================================================
# 4. THE ORDER IN call_provider
# =============================================================================


@pytest.mark.asyncio
async def test_u2_a_bare_test_double_is_called_and_never_counted(counter: Counter):
    """4.1: the counted sibling first (control), then the bare double: called, no row."""
    code = _code("control")
    sibling = _bind(_plugin_class(code)())
    await core.call_provider(sibling, _current(sibling), timeout=10)
    assert counter.counts("asset", code) == (1,) * 5, "control: a plugin that calls out is counted"

    async def answer():
        return "bare"

    calls = _Calls(answer)
    assert await core.call_provider(_NotAPlugin(), calls, timeout=10) == "bare"
    assert calls.count == 1
    assert counter.rows() == {("asset", code)}, "the bare double left no row"


@pytest.mark.asyncio
async def test_u2_a_provider_not_configured_is_refused_before_the_counter(counter: Counter):
    """4.2: a required field without value → NOT_CONFIGURED, the function not called, nothing counted."""
    control = _code("control")
    sibling = _bind(_plugin_class(control)())
    await core.call_provider(sibling, _current(sibling), timeout=10)
    assert counter.counts("asset", control) == (1,) * 5, "control: counted"

    code = _code("unconfigured")
    required = PluginSettingField(key="endpoint", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="Endpoint (u2)", required=True)
    plugin = _plugin_class(code, fields=(required,))()
    plugin.bind_settings(BoundSettings((required,), {}, {}, ("endpoint",)))
    calls = _current(plugin)
    with pytest.raises(AssetSourceError) as refused:
        await core.call_provider(plugin, calls, timeout=10)

    assert refused.value.error_code == "NOT_CONFIGURED"
    assert calls.count == 0
    assert counter.counts("asset", code) is None


@pytest.mark.asyncio
async def test_u2_a_paused_provider_is_refused_before_the_counter(counter: Counter, cooldowns: Cooldowns):
    """4.3: counted once, then paused: the paused call is refused, the function not called, the count unchanged."""
    code = _code("paused")
    plugin = _bind(_plugin_class(code)())
    await core.call_provider(plugin, _current(plugin), timeout=10)
    assert counter.counts("asset", code) == (1,) * 5, "the answered call was counted"
    record_refusal("asset", code, None, 100.0)

    calls = _current(plugin)
    with pytest.raises(AssetRateLimitedError):
        await core.call_provider(plugin, calls, timeout=10)

    assert calls.count == 0
    assert counter.counts("asset", code) == (1,) * 5, "a paused call is not counted"


@pytest.mark.asyncio
async def test_u2_a_provider_that_calls_no_external_service_is_called_and_never_counted(counter: Counter):
    """4.4: the same plugin, flag True counted, flag False called and not counted."""
    out, local = _code("out"), _code("local")
    counted = _bind(_plugin_class(out, external=True)())
    uncounted = _bind(_plugin_class(local, external=False)())

    await core.call_provider(counted, _current(counted), timeout=10)
    calls = _current(uncounted)
    value = await core.call_provider(uncounted, calls, timeout=10)

    assert counter.counts("asset", out) == (1,) * 5, "flag True: counted"
    assert (calls.count, value.value is not None) == (1, True)
    assert counter.counts("asset", local) is None, "flag False: called, never counted"


@pytest.mark.asyncio
async def test_u2_every_call_counts_once_before_it_leaves(counter: Counter):
    """4.5: three answered calls → 3; the provider's function finds its own call already counted."""
    code = _code("before")
    plugin = _bind(_plugin_class(code)())
    seen: list[tuple[int, ...] | None] = []

    async def observed():
        seen.append(counter.counts("asset", code))
        return await plugin.get_current_value("MOCK", IdentifierType.TICKER, {})

    for _ in range(3):
        await core.call_provider(plugin, observed, timeout=10)

    assert seen == [(1,) * 5, (2,) * 5, (3,) * 5], "counted before the call left, once per call"
    assert counter.counts("asset", code) == (3,) * 5


@pytest.mark.parametrize("ending", ["provider-error", "refused-429"])
@pytest.mark.asyncio
async def test_u2_a_call_that_fails_is_counted_all_the_same(counter: Counter, ending: str):
    """4.5: another error, or the provider's own «too many requests»: counted before it left, +1."""
    code = _code(ending.replace("-", "_"))
    plugin = _bind(_plugin_class(code)())
    seen: list[tuple[int, ...] | None] = []

    async def failing():
        seen.append(counter.counts("asset", code))
        if ending == "refused-429":
            return await plugin.get_current_value("MOCK", IdentifierType.TICKER, {RATE_LIMITED_PARAM: 30})
        raise RuntimeError("the source is down (u2)")

    with pytest.raises(Exception):  # noqa: B017, PT011 — the failure's own type is the boundary's business, not this test's
        await core.call_provider(plugin, failing, timeout=10)

    assert seen == [(1,) * 5]
    assert counter.counts("asset", code) == (1,) * 5


@pytest.mark.asyncio
async def test_u2_a_call_that_times_out_is_counted_all_the_same(counter: Counter):
    """4.5: the provider held on an event past the boundary's timeout: the call was counted before it left. The event is
    released at the end, never waited on the clock."""
    code = _code("timeout")
    plugin = _bind(_plugin_class(code)())
    release = threading.Event()

    async def held():
        await asyncio.to_thread(release.wait, 30)
        return await plugin.get_current_value("MOCK", IdentifierType.TICKER, {})

    try:
        with pytest.raises(TimeoutError):
            await core.call_provider(plugin, held, timeout=0.2)
    finally:
        release.set()

    assert counter.counts("asset", code) == (1,) * 5


@pytest.mark.asyncio
async def test_u2_a_full_window_never_calls_the_provider_and_pauses_it(counter: Counter, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """5: hour limit 1 — the first call passes; the second raises ``AssetCallLimitError`` (RATE_LIMITED, the pause of
    870 s recorded under the call's scope, details reason/window/limit) without calling the provider; the next call, with
    no limit any more, meets the pause and does not reach the counter."""
    from backend.app.services.assets.base import AssetCallLimitError

    print_section("U2 5: a full window")
    assert issubclass(AssetCallLimitError, AssetRateLimitedError)
    code = _code("full")
    cls = _plugin_class(code, fields=(_limit_field("hour"),))
    plugin = _bind(cls(), {"call_limit_hour": 1})
    assert plugin.settings.get("call_limit_hour") == 1, "barrier: the limit reached the instance"
    first = _current(plugin)
    await core.call_provider(plugin, first, timeout=10, scope=SCOPE)
    second = _current(plugin)
    with pytest.raises(AssetCallLimitError) as refused:
        await core.call_provider(plugin, second, timeout=10, scope=SCOPE)

    error = refused.value
    assert (first.count, second.count) == (1, 0), "the full window never calls the provider"
    assert (error.error_code, error.scope, error.details) == ("RATE_LIMITED", SCOPE, {"reason": "call_limit", "window": "hour", "limit": 1})
    # U2b: exactly until the window ends, on the limit's own key, no refusal counted (the 429 streak untouched)
    assert _state(cooldowns) == {_limit_key(code, plugin): (0, HOUR_WAIT)}
    assert error.retry_after == HOUR_WAIT, "retry_after is the pause recorded"
    assert counter.counts("asset", code) == (1,) * 5

    third = _current(plugin)
    with pytest.raises(AssetCallLimitError) as paused:
        await core.call_provider(plugin, third, timeout=10, scope=SCOPE)
    assert third.count == 0
    assert (paused.value.retry_after, paused.value.details) == (HOUR_WAIT, {"reason": "call_limit"})
    assert counter.counts("asset", code) == (1,) * 5, "the paused call never reached the counter"

    # U2b: a changed limit (another fingerprint) lifts the pause; the counter decides again
    unlimited = _bind(cls(), {})
    fourth = _current(unlimited)
    await core.call_provider(unlimited, fourth, timeout=10, scope=SCOPE)
    assert fourth.count == 1, "a raised limit lifts the limit pause"
    assert counter.counts("asset", code) == (2,) * 5
    print_success("refused without a call, paused 870 s, the next call held by the pause")


@pytest.mark.asyncio
async def test_u2_with_pauses_off_a_full_window_reports_the_counters_own_wait(counter: Counter, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """5: base 0 — no pause recorded; ``retry_after`` is the counter's 870 s; every later call is refused by the counter."""
    from backend.app.services.assets.base import AssetCallLimitError

    monkeypatch.setenv(BASE_VARIABLE, "0")
    code = _code("pausesoff")
    plugin = _bind(_plugin_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 1})
    await core.call_provider(plugin, _current(plugin), timeout=10)

    waits = []
    later = _current(plugin)
    for _ in range(2):
        with pytest.raises(AssetCallLimitError) as refused:
            await core.call_provider(plugin, later, timeout=10)
        waits.append(refused.value.retry_after)

    assert waits == [pytest.approx(HOUR_WAIT)] * 2
    assert later.count == 0
    assert _state(cooldowns) == {}
    assert counter.counts("asset", code) == (1,) * 5


@pytest.mark.asyncio
async def test_u2_a_limit_of_zero_stops_the_first_call(counter: Counter, cooldowns: Cooldowns):
    """5: ``call_limit_minute = 0`` is a stopped plugin, not «no limit»: the first call is refused, the provider never
    called; paused exactly until the minute ends, 30 s (U2b: no 60 s base)."""
    from backend.app.services.assets.base import AssetCallLimitError

    code = _code("stopped")
    plugin = _bind(_plugin_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 0})
    calls = _current(plugin)
    with pytest.raises(AssetCallLimitError) as refused:
        await core.call_provider(plugin, calls, timeout=10)

    assert calls.count == 0
    assert refused.value.details == {"reason": "call_limit", "window": "minute", "limit": 0}
    assert refused.value.retry_after == MINUTE_WAIT
    assert _state(cooldowns) == {_limit_key(code, plugin): (0, MINUTE_WAIT)}
    assert counter.counts("asset", code) is None


@pytest.mark.asyncio
async def test_u2_a_counter_that_fails_lets_the_call_go(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """6: the counter's engine on a file in a missing folder: ``count_and_check`` returns None and warns; the provider is
    called and answers."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'missing-folder' / 'counters.db'}", poolclass=NullPool)
    monkeypatch.setattr(call_counter, "get_async_engine", lambda: engine)
    _freeze_counter_clock(monkeypatch)
    code = _code("dbdown")
    plugin = _bind(_plugin_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 5})
    calls = _current(plugin)
    try:
        with capture_logs() as events:
            value = await core.call_provider(plugin, calls, timeout=10)
    finally:
        await engine.dispose()

    assert calls.count == 1 and value.value is not None, "the call went"
    warned = [event for event in events if event.get("log_level") == "warning" and code in repr(event)]
    assert len(warned) == 1, f"barrier: the counter was asked, and said it failed: {events}"


# =============================================================================
# 7. THE GROUP OWNER
# =============================================================================


@pytest.mark.asyncio
async def test_u2_two_plugins_of_a_credit_sharing_group_count_on_one_row(counter: Counter, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """7: A and B read ``u2_credits`` (``shares_credits``, hour limit 3 by default): A, B, A pass on one ``group`` row;
    B's next call is refused by the group's full window without being called, paused under B's own key."""
    from backend.app.services.assets.base import AssetCallLimitError

    print_section("U2 7: one group, one row, one limit")
    register_group(SettingsGroup(name="u2_credits", label="U2 credits", shares_credits=True, fields=(_limit_field("hour", default=3),)))
    code_a, code_b = _code("member_a"), _code("member_b")
    AssetProviderRegistry.auto_discover()
    storage = AssetProviderRegistry._get_storage()
    for code in (code_a, code_b):
        monkeypatch.setitem(storage, AssetProviderRegistry._normalize_lookup_code(code), _plugin_class(code, groups=("u2_credits",)))

    async def call(code: str) -> _Calls:
        provider = await core.configured_provider(code)
        assert provider.settings.group("u2_credits").get("call_limit_hour") == 3, "barrier: the group's limit reached the instance"
        calls = _current(provider)
        await core.call_provider(provider, calls, timeout=10)
        return calls

    for code in (code_a, code_b, code_a):
        assert (await call(code)).count == 1

    with pytest.raises(AssetCallLimitError) as refused:
        await call(code_b)

    assert refused.value.details == {"reason": "call_limit", "window": "hour", "limit": 3}
    assert counter.rows() == {("group", "u2_credits")}, "one row, the group's; none of the plugins'"
    assert counter.counts("group", "u2_credits") == (3,) * 5
    ((key, state),) = _state(cooldowns).items()
    assert (key[:2], key[2][0], state) == (("asset", code_b), "call-limit", (0, HOUR_WAIT)), "the limit pause is the refused plugin's own"
    print_success("A, B, A on one row; B refused by the group's window")


@pytest.mark.asyncio
async def test_u2_a_plugin_of_a_plain_group_counts_on_its_own_row(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """7: ``u2_plainshare`` has no ``shares_credits``: its hour limit of 1 is not the owner's; two calls pass, counted on
    the plugin's own row; no group row."""
    register_group(SettingsGroup(name="u2_plainshare", label="U2 plain share", fields=(_limit_field("hour", default=1),)))
    code = _code("plainmember")
    AssetProviderRegistry.auto_discover()
    monkeypatch.setitem(AssetProviderRegistry._get_storage(), AssetProviderRegistry._normalize_lookup_code(code), _plugin_class(code, groups=("u2_plainshare",)))

    for _ in range(2):
        provider = await core.configured_provider(code)
        calls = _current(provider)
        await core.call_provider(provider, calls, timeout=10)
        assert calls.count == 1

    assert counter.counts("asset", code) == (2,) * 5
    assert ("group", "u2_plainshare") not in counter.rows()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


@pytest.mark.asyncio
async def test_u2_a_counter_that_ends_without_a_verdict_frees_the_trial_of_an_expired_pause(counter: Counter, cooldowns: Cooldowns, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """Review: when a pause has expired, ``wait_before_call`` hands the trial to one caller. A count that ends with
    neither an answer nor a refusal (cancelled, say, as a closed search stream cancels it) must free that trial, as any
    other end without a verdict does: the next caller may try at once, not after the trial's seconds."""
    code = _code("trial")
    plugin = _bind(_plugin_class(code)())
    record_refusal("asset", code, None, 60.0)
    clock.now += 61  # the pause is over: the next caller holds the trial

    async def cancelled(*_args: Any, **_kwargs: Any) -> None:
        raise asyncio.CancelledError

    real = core.call_counter.count_and_check
    monkeypatch.setattr(core.call_counter, "count_and_check", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await core.call_provider(plugin, _current(plugin), timeout=10)
    monkeypatch.setattr(core.call_counter, "count_and_check", real)
    assert provider_cooldown.PROVIDER_COOLDOWNS is cooldowns, "barrier: the private pauses are still in place"

    calls = _current(plugin)
    await core.call_provider(plugin, calls, timeout=10)
    assert calls.count == 1, "the trial was freed: the next caller is called at once"


# =============================================================================
# U2b: THE LIMIT PAUSE IS EXACT, ITS OWN, AND LIFTED BY A CHANGED LIMIT
# =============================================================================


def test_u2b_cooldowns_hold_is_exact_counts_no_refusal_and_stops_at_24_hours() -> None:
    """``Cooldowns.hold(key, seconds)``: exactly ``seconds`` (no base, no doubling, no jitter even at the maximum), no
    refusal counted, capped at the 24 h hard maximum; a shorter hold never shortens a running one."""
    clock = FakeClock()
    pauses = Cooldowns(60, 3600, jitter=0.1, clock=clock, rng=lambda: 1.0)
    assert pauses.hold("k", 30.0) == 30.0
    assert pauses.check("k") == 30.0
    assert [(state.refusals, state.remaining) for state in pauses.snapshot()] == [(0, 30.0)]
    assert pauses.hold("k", 10.0) == 30.0, "a shorter hold never shortens the running pause"
    assert pauses.hold("long", 200_000.0) == 86_400.0


@pytest.mark.asyncio
async def test_u2b_a_window_filled_twice_is_paused_exactly_each_time(counter: Counter, cooldowns: Cooldowns, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """Minute limit 1: full at 13:45:30 → 30 s; at 13:46:31 the call passes, the next fills the minute again → 29 s, not
    doubled: a limit pause never counts a refusal."""
    from backend.app.services.assets.base import AssetCallLimitError

    code = _code("twice")
    plugin = _bind(_plugin_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 1})
    await core.call_provider(plugin, _current(plugin), timeout=10)
    with pytest.raises(AssetCallLimitError) as first:
        await core.call_provider(plugin, _current(plugin), timeout=10)
    assert first.value.retry_after == MINUTE_WAIT

    clock.now += 61
    later = NOW + timedelta(seconds=61)
    monkeypatch.setattr(call_counter, "_utc", lambda now=None: (later if now is None else now).astimezone(UTC))
    await core.call_provider(plugin, _current(plugin), timeout=10)
    with pytest.raises(AssetCallLimitError) as second:
        await core.call_provider(plugin, _current(plugin), timeout=10)
    assert second.value.retry_after == 29.0, "exact again, never doubled"
    assert _state(cooldowns) == {_limit_key(code, plugin): (0, 29.0)}


@pytest.mark.asyncio
async def test_u2b_a_limit_pause_never_feeds_the_streak_of_a_source_refusal(counter: Counter, cooldowns: Cooldowns):
    """After a limit pause, a source's 429 on the same provider (another binding, so not held by the limit pause) gets
    the base first pause, 60 s, its first refusal: the limit pause is on a key of its own."""
    from backend.app.services.assets.base import AssetCallLimitError

    code = _code("streak")
    cls = _plugin_class(code, fields=(_limit_field("hour"),))
    limited = _bind(cls(), {"call_limit_hour": 1})
    await core.call_provider(limited, _current(limited), timeout=10)
    with pytest.raises(AssetCallLimitError):
        await core.call_provider(limited, _current(limited), timeout=10)

    free = _bind(cls(), {})

    async def refusing():
        raise AssetRateLimitedError("source said 429")

    with pytest.raises(AssetRateLimitedError) as refused:
        await core.call_provider(free, refusing, timeout=10)
    assert not isinstance(refused.value, AssetCallLimitError)
    assert _state(cooldowns) == {_limit_key(code, limited): (0, HOUR_WAIT), ("asset", code, None): (1, BASE_PAUSE)}


@pytest.mark.asyncio
async def test_u2b_a_settings_change_never_lifts_a_source_pause(counter: Counter, cooldowns: Cooldowns):
    """A source's 429 pause is the provider's, whatever its settings: another binding (another fingerprint) still meets
    it, as a plain ``RATE_LIMITED``, and the counter is not reached."""
    from backend.app.services.assets.base import AssetCallLimitError

    code = _code("sourcepause")
    cls = _plugin_class(code, fields=(_limit_field("hour"),))
    record_refusal("asset", code, None, 100.0)
    other = _bind(cls(), {"call_limit_hour": 50})
    calls = _current(other)
    with pytest.raises(AssetRateLimitedError) as paused:
        await core.call_provider(other, calls, timeout=10)
    assert not isinstance(paused.value, AssetCallLimitError)
    assert calls.count == 0
    assert counter.counts("asset", code) is None


@pytest.mark.asyncio
async def test_u2b_a_limit_refusal_leaves_the_trial_of_an_expired_source_pause_free(counter: Counter, cooldowns: Cooldowns, clock: FakeClock):
    """Review (U3): an expired source pause hands its trial to the caller; a refusal by the limit (its running pause, or a
    full window) is no verdict on the source, so the source's trial is freed."""
    from backend.app.services.assets.base import AssetCallLimitError

    for held in (True, False):
        code = _code("trialfree")
        plugin = _bind(_plugin_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 1})
        await core.call_provider(plugin, _current(plugin), timeout=10)
        if held:
            with pytest.raises(AssetCallLimitError):
                await core.call_provider(plugin, _current(plugin), timeout=10)
        record_refusal("asset", code, None, 60.0)
        clock.now += 61
        with pytest.raises(AssetCallLimitError):
            await core.call_provider(plugin, _current(plugin), timeout=10)
        source = next(state for state in cooldowns.snapshot() if state.key == ("asset", code, None))
        assert not source.trial_in_flight, f"held={held}: the source's trial is free after a limit refusal"


@pytest.mark.asyncio
async def test_u2b_parallel_calls_after_an_expired_limit_pause_all_reach_the_counter(counter: Counter, cooldowns: Cooldowns, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """Review (U3): after a limit pause ends with its window, calls made at once (the per-asset reads in ``gather``, a
    refresh at concurrency 3) all reach the counter, which alone decides: none waits for another's trial."""
    from backend.app.services.assets.base import AssetCallLimitError

    code = _code("parallel")
    plugin = _bind(_plugin_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 2})
    for _ in range(2):
        await core.call_provider(plugin, _current(plugin), timeout=10)
    with pytest.raises(AssetCallLimitError):
        await core.call_provider(plugin, _current(plugin), timeout=10)
    clock.now += 31
    later = NOW + timedelta(seconds=31)
    monkeypatch.setattr(call_counter, "_utc", lambda now=None: (later if now is None else now).astimezone(UTC))

    calls = [_current(plugin), _current(plugin)]
    await asyncio.gather(*(core.call_provider(plugin, current, timeout=10) for current in calls))
    assert [current.count for current in calls] == [1, 1], "both reach the counter and are called"
