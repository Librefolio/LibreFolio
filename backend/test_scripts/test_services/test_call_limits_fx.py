# ruff: noqa: PLC0415 — the U3 names are imported inside each test on purpose: red on HEAD, every test fails for its own reason
"""The FX boundary counts and checks the calls of a plugin to its external service (project 76, lot U3; plan 76 §3.5).

Modules under test: ``services/fx/runtime.py`` (``call_fx_provider``), ``services/fx/base.py``
(``FXRateProvider.calls_external_service``, the new ``FXCallLimitError``), ``services/platform/call_counter.py`` (the
new ``call_owner(provider, family)``, shared with the asset boundary), ``services/platform/provider_cooldown.py`` (the
limit pause of U2b: ``limit_pause_left``, a read that hands out no trial, and ``record_limit_pause``) and
``services/fx/catalog.py`` (the supported-currency list asked through the boundary). The effects through the FX sync
and the scheduler's history job are pinned in ``test_rate_limit_results.py`` (``test_u3_…``), whose private database
already stands behind the sync's route reads and rate writes.

The contract pinned here:

1. **The flag.** ``FXRateProvider.calls_external_service = True`` (class attribute of the base). Every shipped central
   bank keeps True (ECB, FED, BOE, SNB, BDI, BCB, NORGES, NBU, BOC); ``ManualProvider`` (hand-entered rates) and the
   test-only doubles ``MockFXProvider``, ``MockFXFailProvider`` declare False in their own class. A double with settings
   that is no ``FXRateProvider`` declares nothing: never counted (read with ``getattr(..., False)``).
2. **The owner of the count moves to the counter**: ``call_counter.call_owner(provider, family) -> (family, code,
   CallLimits)``: the ``shares_credits`` group the provider reads → ``("group", name, the group's limits)``, else
   ``(family, provider_code, its own limits)``; a limit is the ``call_limit_<window>`` field when declared and valued,
   else None; 0 stays 0. ``assets.core.call_owner(p) == call_counter.call_owner(p, "asset")``.
3. **The order in ``call_fx_provider``**: a bare double is called, never counted; ``NOT_CONFIGURED``
   (``FXNotConfiguredError``) and a source pause (``FXRateLimitedError``) refuse before the counter; the flag False is
   called, never counted; a running limit pause refuses with ``FXCallLimitError`` (``retry_after`` the pause left,
   ``details == {"reason": "call_limit"}``), not counted; otherwise ``call_counter.count_and_check(family, owner,
   limits)`` counts +1 BEFORE ``fn()`` is awaited, even when the call then fails (an ``FXServiceError``, the provider's
   own 429); one count per call.
4. **A full window** (``CallLimitReached``): ``fn`` is never called; the limit pause is recorded EXACTLY until the full
   window ends (no base, no doubling, no jitter), on its own key ``("fx", code, ("call-limit", fingerprint))``, never on
   the source key ``("fx", code, None)``, whose 429 streak it never feeds; ``FXCallLimitError`` (subclass of
   ``FXRateLimitedError``: ``error_code == "RATE_LIMITED"``, an ``FXServiceError``) leaves with ``retry_after`` = that
   pause (the counter's own wait when the pauses are off), ``details == {"reason": "call_limit", "window": …,
   "limit": …}`` and ``__cause__`` the ``CallLimitReached``. The next call meets the limit pause and does not reach the
   counter. A changed fingerprint (a raised limit) is another key: the next call reaches the counter. A source pause
   survives a fingerprint change.
5. **A count that ends without a verdict** (cancelled) frees the trial of an expired source pause
   (``record_no_verdict``); an expired limit pause hands out no trial at all (review): the next call goes at once.
6. **A counter that fails** (``count_and_check`` → None, its warning logged): the call goes.
7. **The group owner**: two FX plugins reading one ``shares_credits`` group count on ONE row (``family="group"``); its
   limit binds both; the limit pause stays the refused plugin's own.
8. **The catalog** (``catalog.get_supported_currencies_status``): the first list asked is counted; a full limit answers
   like a provider's refusal (the last known list, or the empty ``unavailable`` one), the provider not called.

Pure: no lane database, no server, no network. The counter (and the plugin settings' reads) on a private SQLite file
under ``tmp_path`` built with ``SQLModel.metadata.create_all`` (``call_counter.get_async_engine`` and
``plugin_settings.runtime.get_async_engine`` patched); the counter's clock is ``CounterClock.moment``, read through a
patched ``call_counter._utc`` (``call_fx_provider`` passes no ``now``); the pauses are a private ``Cooldowns`` on a
``FakeClock`` without jitter, in place of ``provider_cooldown.PROVIDER_COOLDOWNS``. A test that lets time pass moves
both clocks together (``_advance``). Settings are bound with ``BoundSettings`` given to the instance (fingerprints set
by the test) or, for the group owner, through the real ``fx.runtime.configured_fx_provider`` on the FX registry, the
classes put in its storage with ``monkeypatch.setitem``. FX limit fields are SYSTEM integers: ``FAMILY_RULES["fx"]``
admits no user field. Every code starts with ``U3_``, every group name with ``u3``.

Red on HEAD 0c8f26731: no ``calls_external_service`` on the FX side, no ``FXCallLimitError``, no
``call_counter.call_owner``, no limit-pause functions, and ``call_fx_provider`` never counts. Each negative («never
counted», «not refused») stands beside a positive control in the same test, so no test is green on HEAD by the absence
of the feature.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core
from backend.app.services.fx import catalog
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx.base import FXNotConfiguredError, FXRateLimitedError, FXRateProvider, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.manual.plugin import ManualProvider
from backend.app.services.fx_providers.mockfx.plugin import MockFXFailProvider, MockFXProvider
from backend.app.services.platform import call_counter, provider_cooldown
from backend.app.services.platform.provider_cooldown import record_refusal
from backend.app.services.plugin_settings import runtime as settings_runtime
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import FAMILY_RULES, PluginSettingField, SettingScope, SettingType, validate_declaration
from backend.app.services.plugin_settings.groups import SettingsGroup, all_groups, register_group, release_group, validate_plugin_groups
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

BASE_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS"
MAX_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS"
TEST_INSTANCE_KEY = "u3-call-limits-fx-test-instance-key-0123456789ab"
START = 1_000_000.0
WINDOWS = ("minute", "hour", "day", "week", "month")
#: The counter's clock at the start of every test: a Tuesday, 13:45:30 UTC. The hour ends in 870 s, the minute in 30 s.
NOW = datetime(2026, 11, 17, 13, 45, 30, tzinfo=UTC)
HOUR_WAIT = 870.0
MINUTE_WAIT = 30.0
#: The base pause of the private ``Cooldowns``: the first source refusal without a Retry-After pauses this long.
BASE_PAUSE = 60.0
DAY = date(1987, 3, 2)
SHIPPED_FLAGS = {
    "ECB": True,
    "FED": True,
    "BOE": True,
    "SNB": True,
    "BDI": True,
    "BCB": True,
    "NORGES": True,
    "NBU": True,
    "BOC": True,
    "BANXICO": True,
    "MANUAL": False,
    "MOCKFX": False,
    "MOCKFX_FAIL": False,
}


class FakeClock:
    """A clock that moves only when the test moves it: the pauses'."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class CounterClock:
    """The counter's «now», moved by the test together with the pauses' clock."""

    def __init__(self) -> None:
        self.moment = NOW


class _Calls:
    """The ``fn`` the boundary receives: counts the calls it let through, then builds the plugin's coroutine."""

    def __init__(self, make: Callable[[], object]) -> None:
        self.count = 0
        self._make = make

    def __call__(self):
        self.count += 1
        return self._make()


class _AnsweringFX(MockFXProvider):
    """An FX provider of the test: rate 2 on the first day for every currency asked; MockFX's list of currencies."""

    settings_fields = ()
    rate_limited = False

    async def fetch_rates(self, date_range, currencies, base_currency=None):
        return {currency: [(date_range[0], "EUR", currency, Decimal("2.000000"))] for currency in currencies}


class _NotAPlugin:
    """A test double that is no plugin: no settings mixin, called as it is."""

    provider_code = "U3_BARE_DOUBLE"


def _code(label: str) -> str:
    return f"U3_{label.upper()}_{uuid.uuid4().hex[:8].upper()}"


def _limit_field(window: str, default: int | None = None) -> PluginSettingField:
    return PluginSettingField(key=f"call_limit_{window}", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label=f"Calls per {window} (u3)", default=default, minimum=0)


def _fx_class(code: str, *, fields: tuple[PluginSettingField, ...] = (), groups: tuple[str, ...] = (), external: bool = True) -> type:
    """A test FX plugin: ``_AnsweringFX``'s answers under ``code``, not test-only, the flag, fields and groups given."""
    return type(
        f"U3FX_{code}",
        (_AnsweringFX,),
        {
            "code": property(lambda self: code),
            "name": f"U3 {code}",
            "test_only": False,
            "calls_external_service": external,
            "settings_fields": fields,
            "settings_groups": groups,
        },
    )


def _bind(plugin: Any, values: dict[str, Any] | None = None, groups: dict[str, tuple[SettingsGroup, dict[str, Any]]] | None = None, *, fingerprint: str = "") -> Any:
    """Bind ``values`` (the plugin's own plain fields) and each group's values, as the core would."""
    bound_groups = {name: BoundSettings(group.fields, group_values, {}) for name, (group, group_values) in (groups or {}).items()}
    plugin.bind_settings(BoundSettings(type(plugin).settings_fields, values or {}, {}, fingerprint=fingerprint, groups=bound_groups))
    return plugin


def _fetch(plugin: Any) -> _Calls:
    return _Calls(lambda: plugin.fetch_rates((DAY, DAY), ["USD"]))


def _state(cooldowns: Cooldowns) -> dict:
    return {state.key: (state.refusals, state.remaining) for state in cooldowns.snapshot()}


def _source_key(code: str) -> tuple:
    return ("fx", code, None)


def _limit_key(code: str, fingerprint: str) -> tuple:
    return ("fx", code, ("call-limit", fingerprint))


def _advance(clock: FakeClock, counter_clock: CounterClock, seconds: float) -> None:
    """Let ``seconds`` pass for the pauses and the counter together."""
    clock.now += seconds
    counter_clock.moment += timedelta(seconds=seconds)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Pauses on (base 60 s, max 3600 s), test mode, a test instance key and data directory, no FX allow-list; no u3
    group left behind."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(BASE_VARIABLE, "60")
    monkeypatch.setenv(MAX_VARIABLE, "3600")
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", TEST_INSTANCE_KEY)
    monkeypatch.delenv("LIBREFOLIO_FX_PROVIDERS_ENABLED", raising=False)
    yield
    for name in [name for name in all_groups() if name.startswith("u3")]:
        release_group(name)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def counter_clock() -> CounterClock:
    return CounterClock()


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
        """The five counts of the pair's row, read through a plain ``sqlite3`` connection, or None."""
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


def _counter_clock_patch(monkeypatch: pytest.MonkeyPatch, counter_clock: CounterClock) -> None:
    """``call_counter._utc(None)`` answers ``counter_clock.moment``: the windows of every count are those of that moment."""
    real = call_counter._utc
    monkeypatch.setattr(call_counter, "_utc", lambda now=None: real(counter_clock.moment if now is None else now))


@pytest_asyncio.fixture
async def counter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, counter_clock: CounterClock) -> AsyncIterator[Counter]:
    """A private file with the whole schema behind ``call_counter.get_async_engine`` (and the plugin settings' reads);
    the counter's clock is ``counter_clock``."""
    path = tmp_path / "u3_counters.db"
    sync_engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    monkeypatch.setattr(call_counter, "get_async_engine", lambda: engine)
    monkeypatch.setattr(settings_runtime, "get_async_engine", lambda: engine)
    _counter_clock_patch(monkeypatch, counter_clock)
    try:
        yield Counter(path, engine)
    finally:
        await engine.dispose()


# =============================================================================
# 1. THE FLAG
# =============================================================================


def test_u3_the_fx_base_declares_calls_external_service_true():
    """1: the base class owns the flag, True: a central bank that says nothing is counted."""
    assert "calls_external_service" in vars(FXRateProvider), "FXRateProvider declares no calls_external_service"
    assert FXRateProvider.calls_external_service is True


def test_u3_every_shipped_fx_provider_says_whether_it_calls_out():
    """1: the shipped FX providers, pinned: every central bank True; MANUAL and the test-only doubles False in their own
    class; no shipped provider left out of the pin."""
    FXProviderRegistry.auto_discover()
    shipped = {code: cls for code, cls in FXProviderRegistry._get_storage().items() if cls.__module__.startswith("backend.app.services.fx_providers.")}
    assert set(shipped) == set(SHIPPED_FLAGS), f"the shipped FX providers changed: pin the new one's flag here: {sorted(shipped)}"
    flags = {code: getattr(cls, "calls_external_service", "<missing>") for code, cls in shipped.items()}
    assert flags == SHIPPED_FLAGS
    for cls in (ManualProvider, MockFXProvider, MockFXFailProvider):
        assert vars(cls).get("calls_external_service") is False, f"{cls.__name__} declares False in its own class"
    assert all(flags[code] is False for code, cls in shipped.items() if getattr(cls, "test_only", False)), "a test-only double never counts"


# =============================================================================
# 2. THE OWNER OF THE COUNT, IN THE COUNTER
# =============================================================================


def test_u3_call_owner_of_an_fx_plugin_is_itself_with_its_own_limits():
    """2: own fields minute=3, hour=0 (stopped, not «no limit»), day declared without value, week and month undeclared;
    the FX family admits these SYSTEM fields."""
    assert FAMILY_RULES["fx"].user_scope is False, "barrier: FX plugins take system fields only"
    fields = (_limit_field("minute"), _limit_field("hour"), _limit_field("day"))
    validate_declaration(fields, family="fx")  # barrier: the declaration is valid for the FX family

    code = _code("own")
    plugin = _bind(_fx_class(code, fields=fields)(), {"call_limit_minute": 3, "call_limit_hour": 0})
    assert (plugin.settings.get("call_limit_minute"), plugin.settings.get("call_limit_hour")) == (3, 0), "barrier: the values reached the instance"

    assert call_counter.call_owner(plugin, "fx") == ("fx", code, call_counter.CallLimits(minute=3, hour=0, day=None, week=None, month=None))


def test_u3_call_owner_of_an_fx_plugin_reading_a_credit_sharing_group_is_the_group():
    """2: the group's limits, never the plugin's; a plain group beside it changes nothing."""
    shared = SettingsGroup(name="u3_owner_share", label="U3 owner share", shares_credits=True, fields=(_limit_field("minute"), _limit_field("hour")))
    plain = SettingsGroup(name="u3_owner_plain", label="U3 owner plain", fields=(_limit_field("day"),))
    register_group(shared)
    register_group(plain)
    # U4: a reader of a credit-sharing group declares no limit of its own (the group holds all five; one key in both
    # would be refused), so the plugin's own limits cannot leak into the owner's
    cls = _fx_class(_code("grouped"), groups=("u3_owner_plain", "u3_owner_share"))
    validate_plugin_groups(cls, family="fx")  # barrier: an FX plugin may read these groups
    plugin = _bind(cls(), {}, {"u3_owner_share": (shared, {"call_limit_minute": 5}), "u3_owner_plain": (plain, {"call_limit_day": 1})})
    assert plugin.settings.group("u3_owner_share").get("call_limit_minute") == 5, "barrier: the group's value reached the instance"

    assert call_counter.call_owner(plugin, "fx") == ("group", "u3_owner_share", call_counter.CallLimits(minute=5))


def _asset_class(code: str, *, fields: tuple[PluginSettingField, ...] = (), groups: tuple[str, ...] = ()) -> type:
    return type(
        f"U3Asset_{code}",
        (MockProvider,),
        {"provider_code": property(lambda self: code), "provider_name": f"U3 {code}", "test_only": False, "calls_external_service": True, "settings_fields": fields, "settings_groups": groups},
    )


def test_u3_the_asset_call_owner_is_the_counters_with_the_asset_family():
    """2: ``core.call_owner(p)`` stays, equal to ``call_counter.call_owner(p, "asset")``: a plain plugin and a group reader."""
    shared = SettingsGroup(name="u3_asset_share", label="U3 asset share", shares_credits=True, fields=(_limit_field("hour"),))
    register_group(shared)
    code = _code("assetplain")
    plain = _bind(_asset_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 2})
    grouped = _bind(_asset_class(_code("assetgroup"), groups=("u3_asset_share",))(), {}, {"u3_asset_share": (shared, {"call_limit_hour": 4})})

    assert call_counter.call_owner(plain, "asset") == ("asset", code, call_counter.CallLimits(minute=2))
    assert call_counter.call_owner(grouped, "asset") == ("group", "u3_asset_share", call_counter.CallLimits(hour=4))
    for provider in (plain, grouped):
        assert core.call_owner(provider) == call_counter.call_owner(provider, "asset")


# =============================================================================
# 3. THE ORDER IN call_fx_provider
# =============================================================================


@pytest.mark.asyncio
async def test_u3_a_bare_test_double_is_called_and_never_counted(counter: Counter):
    """3: the counted sibling first (control), then the bare double: called, no row."""
    code = _code("control")
    sibling = _bind(_fx_class(code)())
    await fx_runtime.call_fx_provider(sibling, _fetch(sibling))
    assert counter.counts("fx", code) == (1,) * 5, "control: a plugin that calls out is counted"

    async def answer():
        return "bare"

    calls = _Calls(answer)
    assert await fx_runtime.call_fx_provider(_NotAPlugin(), calls) == "bare"
    assert calls.count == 1
    assert counter.rows() == {("fx", code)}, "the bare double left no row"


@pytest.mark.asyncio
async def test_u3_a_settings_double_that_is_no_fx_provider_is_never_counted(counter: Counter):
    """3: a ``PluginSettingsMixin`` double without the flag (no ``FXRateProvider``) is called and never counted."""
    from backend.app.services.plugin_settings.contract import PluginSettingsMixin

    code = _code("control")
    sibling = _bind(_fx_class(code)())
    await fx_runtime.call_fx_provider(sibling, _fetch(sibling))
    assert counter.counts("fx", code) == (1,) * 5, "control: counted"

    double_code = _code("settingsdouble")
    double = type("U3SettingsDouble", (PluginSettingsMixin,), {"provider_code": double_code})()
    assert not hasattr(type(double), "calls_external_service"), "barrier: the double declares no flag"

    async def answer():
        return "double"

    calls = _Calls(answer)
    assert await fx_runtime.call_fx_provider(double, calls) == "double"
    assert calls.count == 1
    assert counter.counts("fx", double_code) is None


@pytest.mark.asyncio
async def test_u3_a_provider_not_configured_is_refused_before_the_counter(counter: Counter):
    """3: a required field without value → ``FXNotConfiguredError``, the function not called, nothing counted."""
    control = _code("control")
    sibling = _bind(_fx_class(control)())
    await fx_runtime.call_fx_provider(sibling, _fetch(sibling))
    assert counter.counts("fx", control) == (1,) * 5, "control: counted"

    code = _code("unconfigured")
    required = PluginSettingField(key="endpoint", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="Endpoint (u3)", required=True)
    plugin = _fx_class(code, fields=(required,))()
    plugin.bind_settings(BoundSettings((required,), {}, {}, ("endpoint",)))
    calls = _fetch(plugin)
    with pytest.raises(FXNotConfiguredError):
        await fx_runtime.call_fx_provider(plugin, calls)

    assert calls.count == 0
    assert counter.counts("fx", code) is None


@pytest.mark.asyncio
async def test_u3_a_source_paused_provider_is_refused_before_the_counter(counter: Counter):
    """3: counted once, then paused for too many requests: refused, the function not called, the count unchanged."""
    code = _code("paused")
    plugin = _bind(_fx_class(code)())
    await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    assert counter.counts("fx", code) == (1,) * 5, "the answered call was counted"
    record_refusal("fx", code, None, 100.0)

    calls = _fetch(plugin)
    with pytest.raises(FXRateLimitedError) as refused:
        await fx_runtime.call_fx_provider(plugin, calls)

    assert refused.value.retry_after == 100.0
    assert calls.count == 0
    assert counter.counts("fx", code) == (1,) * 5, "a paused call is not counted"


@pytest.mark.asyncio
async def test_u3_manual_mockfx_and_a_local_plugin_are_called_and_never_counted(counter: Counter):
    """3: the flag True counted; the flag False (a test plugin, MockFX, MANUAL) called and never counted."""
    out = _code("out")
    counted = _bind(_fx_class(out, external=True)())
    await fx_runtime.call_fx_provider(counted, _fetch(counted))
    assert counter.counts("fx", out) == (1,) * 5, "flag True: counted"

    local = _bind(_fx_class(_code("local"), external=False)())
    mock = _bind(MockFXProvider())
    manual = ManualProvider()
    for provider in (local, mock, manual):
        calls = _fetch(provider)
        await fx_runtime.call_fx_provider(provider, calls)
        assert calls.count == 1, f"{provider.provider_code} was called"

    assert counter.rows() == {("fx", out)}, "flag False: called, never counted"


@pytest.mark.asyncio
async def test_u3_every_call_counts_once_before_it_leaves(counter: Counter):
    """3: three answered calls → 3; the provider's function finds its own call already counted."""
    code = _code("before")
    plugin = _bind(_fx_class(code)())
    seen: list[tuple[int, ...] | None] = []

    async def observed():
        seen.append(counter.counts("fx", code))
        return await plugin.fetch_rates((DAY, DAY), ["USD"])

    for _ in range(3):
        await fx_runtime.call_fx_provider(plugin, observed)

    assert seen == [(1,) * 5, (2,) * 5, (3,) * 5], "counted before the call left, once per call"
    assert counter.counts("fx", code) == (3,) * 5


@pytest.mark.parametrize("ending", ["fx-service-error", "provider-429"])
@pytest.mark.asyncio
async def test_u3_a_call_that_fails_is_counted_all_the_same(counter: Counter, ending: str):
    """3: an ``FXServiceError``, or the provider's own «too many requests»: counted before it left, +1."""
    code = _code(ending.replace("-", "_"))
    plugin = _bind(_fx_class(code)())
    seen: list[tuple[int, ...] | None] = []

    async def failing():
        seen.append(counter.counts("fx", code))
        if ending == "provider-429":
            raise FXRateLimitedError("refused for too many requests (u3)", retry_after=30.0)
        raise FXServiceError("the central bank is down (u3)")

    with pytest.raises(FXServiceError):
        await fx_runtime.call_fx_provider(plugin, failing)

    assert seen == [(1,) * 5]
    assert counter.counts("fx", code) == (1,) * 5


# =============================================================================
# 4. A FULL WINDOW: THE LIMIT PAUSE
# =============================================================================


@pytest.mark.asyncio
async def test_u3_a_full_window_never_calls_the_provider_and_pauses_it_on_its_own_key(counter: Counter, cooldowns: Cooldowns):
    """4: hour limit 1 — the first call passes; the second raises ``FXCallLimitError`` (RATE_LIMITED, an FXServiceError,
    details reason/window/limit, ``__cause__`` the counter's refusal, ``retry_after`` the exact 870 s) without calling
    the provider; the pause is on the limit key, never the source key; the next call meets the limit pause and does not
    reach the counter."""
    from backend.app.services.fx.base import FXCallLimitError

    print_section("U3 4: a full window")
    assert issubclass(FXCallLimitError, FXRateLimitedError) and issubclass(FXCallLimitError, FXServiceError)
    code = _code("full")
    plugin = _bind(_fx_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 1}, fingerprint="u3-full")
    assert plugin.settings.get("call_limit_hour") == 1, "barrier: the limit reached the instance"

    first = _fetch(plugin)
    await fx_runtime.call_fx_provider(plugin, first)
    second = _fetch(plugin)
    with pytest.raises(FXCallLimitError) as refused:
        await fx_runtime.call_fx_provider(plugin, second)

    error = refused.value
    assert (first.count, second.count) == (1, 0), "the full window never calls the provider"
    assert (error.error_code, error.details) == ("RATE_LIMITED", {"reason": "call_limit", "window": "hour", "limit": 1})
    assert isinstance(error.__cause__, call_counter.CallLimitReached)
    assert error.retry_after == HOUR_WAIT, "retry_after is the pause recorded: exactly until the hour ends"
    state = _state(cooldowns)
    assert _source_key(code) not in state, "a limit never feeds the source's 429 streak"
    assert state[_limit_key(code, "u3-full")][1] == HOUR_WAIT, "the limit pause, on its own key, exact"
    assert provider_cooldown.limit_pause_left("fx", code, "u3-full") == HOUR_WAIT
    assert counter.counts("fx", code) == (1,) * 5

    third = _fetch(plugin)
    with pytest.raises(FXCallLimitError) as held:
        await fx_runtime.call_fx_provider(plugin, third)
    assert third.count == 0
    assert (held.value.retry_after, held.value.details) == (HOUR_WAIT, {"reason": "call_limit"})
    assert counter.counts("fx", code) == (1,) * 5, "the call held by the limit pause never reached the counter"
    print_success("refused without a call, 870 s on the limit key, the next call held by the limit pause")


@pytest.mark.asyncio
async def test_u3_the_limit_pause_is_exact_and_never_doubles(counter: Counter, cooldowns: Cooldowns, clock: FakeClock, counter_clock: CounterClock):
    """4: minute limit 1 at 13:45:30 — the full minute pauses exactly 30 s (no 60 s base); 31 s later the next minute
    admits a call; filled again at 13:46:01, it pauses exactly 59 s (no doubling)."""
    from backend.app.services.fx.base import FXCallLimitError

    code = _code("exact")
    plugin = _bind(_fx_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 1}, fingerprint="u3-exact")
    await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    with pytest.raises(FXCallLimitError) as first_fill:
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    assert first_fill.value.retry_after == MINUTE_WAIT

    _advance(clock, counter_clock, MINUTE_WAIT + 1)
    admitted = _fetch(plugin)
    await fx_runtime.call_fx_provider(plugin, admitted)
    assert admitted.count == 1, "the next minute admits a call"
    with pytest.raises(FXCallLimitError) as second_fill:
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))

    assert second_fill.value.retry_after == 59.0, "exactly until 13:47:00: never doubled"
    assert _source_key(code) not in _state(cooldowns)
    assert counter.counts("fx", code) == (1, 2, 2, 2, 2)


@pytest.mark.asyncio
async def test_u3_a_source_429_after_a_limit_pause_gets_the_first_base_pause(counter: Counter, cooldowns: Cooldowns, clock: FakeClock, counter_clock: CounterClock):
    """4: the limit pause over, the source refuses without a Retry-After: its first refusal, the 60 s base pause; the
    limit never fed its streak."""
    from backend.app.services.fx.base import FXCallLimitError

    code = _code("streak")
    plugin = _bind(_fx_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 1}, fingerprint="u3-streak")
    await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    with pytest.raises(FXCallLimitError):
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    _advance(clock, counter_clock, MINUTE_WAIT + 1)

    async def refused_by_the_source():
        raise FXRateLimitedError("refused for too many requests (u3)")

    with pytest.raises(FXRateLimitedError) as refused:
        await fx_runtime.call_fx_provider(plugin, refused_by_the_source)

    assert not isinstance(refused.value, FXCallLimitError), "barrier: the source's own refusal"
    assert refused.value.retry_after == BASE_PAUSE
    assert _state(cooldowns)[_source_key(code)] == (1, BASE_PAUSE), "the first refusal of the source's streak"


@pytest.mark.asyncio
async def test_u3_a_changed_fingerprint_lets_the_next_call_reach_the_counter(counter: Counter):
    """4: the hour full under ``u3-old``; the administrator raises the limit (new values, new fingerprint): the next
    call is counted and called at once."""
    from backend.app.services.fx.base import FXCallLimitError

    code = _code("raised")
    cls = _fx_class(code, fields=(_limit_field("hour"),))
    plugin = _bind(cls(), {"call_limit_hour": 1}, fingerprint="u3-old")
    await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    with pytest.raises(FXCallLimitError):
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))

    raised = _bind(cls(), {"call_limit_hour": 5}, fingerprint="u3-new")
    calls = _fetch(raised)
    await fx_runtime.call_fx_provider(raised, calls)

    assert calls.count == 1, "the old limit pause no longer applies"
    assert counter.counts("fx", code) == (2,) * 5, "the call reached the counter"


@pytest.mark.asyncio
async def test_u3_a_source_pause_survives_a_fingerprint_change(counter: Counter):
    """4: counted once, then a source pause; new settings (another fingerprint) do not lift it: refused, not called, not
    counted, and not as a limit."""
    from backend.app.services.fx.base import FXCallLimitError

    code = _code("sourcepause")
    cls = _fx_class(code, fields=(_limit_field("hour"),))
    plugin = _bind(cls(), {"call_limit_hour": 5}, fingerprint="u3-before")
    await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    assert counter.counts("fx", code) == (1,) * 5, "control: counted"
    record_refusal("fx", code, None, 100.0)

    changed = _bind(cls(), {"call_limit_hour": 50}, fingerprint="u3-after")
    calls = _fetch(changed)
    with pytest.raises(FXRateLimitedError) as refused:
        await fx_runtime.call_fx_provider(changed, calls)

    assert not isinstance(refused.value, FXCallLimitError)
    assert refused.value.retry_after == 100.0
    assert calls.count == 0
    assert counter.counts("fx", code) == (1,) * 5


@pytest.mark.asyncio
async def test_u3_with_pauses_off_a_full_window_reports_the_counters_own_wait(counter: Counter, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """4: base 0 — no pause recorded; ``retry_after`` is the counter's 870 s; every later call is refused by the counter."""
    from backend.app.services.fx.base import FXCallLimitError

    monkeypatch.setenv(BASE_VARIABLE, "0")
    code = _code("pausesoff")
    plugin = _bind(_fx_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 1})
    await fx_runtime.call_fx_provider(plugin, _fetch(plugin))

    waits = []
    details = []
    later = _fetch(plugin)
    for _ in range(2):
        with pytest.raises(FXCallLimitError) as refused:
            await fx_runtime.call_fx_provider(plugin, later)
        waits.append(refused.value.retry_after)
        details.append(refused.value.details)

    assert waits == [pytest.approx(HOUR_WAIT)] * 2
    assert details == [{"reason": "call_limit", "window": "hour", "limit": 1}] * 2, "both refused by the counter itself"
    assert later.count == 0
    assert _state(cooldowns) == {}
    assert counter.counts("fx", code) == (1,) * 5


@pytest.mark.asyncio
async def test_u3_a_limit_of_zero_stops_the_first_call(counter: Counter, cooldowns: Cooldowns):
    """4: ``call_limit_minute = 0`` is a stopped plugin, not «no limit»: the first call is refused, the provider never
    called, the pause exactly the 30 s left in the minute."""
    from backend.app.services.fx.base import FXCallLimitError

    code = _code("stopped")
    plugin = _bind(_fx_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 0})
    calls = _fetch(plugin)
    with pytest.raises(FXCallLimitError) as refused:
        await fx_runtime.call_fx_provider(plugin, calls)

    assert calls.count == 0
    assert refused.value.details == {"reason": "call_limit", "window": "minute", "limit": 0}
    assert refused.value.retry_after == MINUTE_WAIT
    assert _source_key(code) not in _state(cooldowns)
    assert counter.counts("fx", code) is None


# =============================================================================
# 5. A COUNT WITHOUT A VERDICT
# =============================================================================


@pytest.mark.asyncio
async def test_u3_a_counter_that_ends_without_a_verdict_frees_the_trial_of_an_expired_source_pause(counter: Counter, cooldowns: Cooldowns, clock: FakeClock, monkeypatch: pytest.MonkeyPatch):
    """5: a source pause has expired, so this caller holds its trial; the count is cancelled: the trial is freed, and
    the next caller is called at once. Only the counter's function is replaced, and only it is put back."""
    code = _code("trial")
    plugin = _bind(_fx_class(code)())
    record_refusal("fx", code, None, 60.0)
    clock.now += 61  # the pause is over: the next caller holds the trial

    async def cancelled(*_args: Any, **_kwargs: Any) -> None:
        raise asyncio.CancelledError

    real = call_counter.count_and_check
    monkeypatch.setattr(call_counter, "count_and_check", cancelled)
    first = _fetch(plugin)
    with pytest.raises(asyncio.CancelledError):
        await fx_runtime.call_fx_provider(plugin, first)
    monkeypatch.setattr(call_counter, "count_and_check", real)
    assert provider_cooldown.PROVIDER_COOLDOWNS is cooldowns, "barrier: the private pauses are still in place"
    assert first.count == 0, "the cancelled count let nothing leave"

    calls = _fetch(plugin)
    await fx_runtime.call_fx_provider(plugin, calls)
    assert calls.count == 1, "the trial was freed: the next caller is called at once"


@pytest.mark.asyncio
async def test_u3_a_counter_that_ends_without_a_verdict_frees_the_trial_of_an_expired_limit_pause(counter: Counter, clock: FakeClock, counter_clock: CounterClock, monkeypatch: pytest.MonkeyPatch):
    """5: the limit pause has expired, so this caller holds its trial; the count is cancelled: the limit trial is
    released, and the next caller reaches the counter at once."""
    from backend.app.services.fx.base import FXCallLimitError

    code = _code("limittrial")
    plugin = _bind(_fx_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 1}, fingerprint="u3-trial")
    await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    with pytest.raises(FXCallLimitError):
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    _advance(clock, counter_clock, MINUTE_WAIT + 1)

    async def cancelled(*_args: Any, **_kwargs: Any) -> None:
        raise asyncio.CancelledError

    real = call_counter.count_and_check
    monkeypatch.setattr(call_counter, "count_and_check", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    monkeypatch.setattr(call_counter, "count_and_check", real)

    calls = _fetch(plugin)
    await fx_runtime.call_fx_provider(plugin, calls)
    assert calls.count == 1, "the limit trial was released: the next caller is counted and called at once"
    assert counter.counts("fx", code) == (1, 2, 2, 2, 2)


# =============================================================================
# 6. A COUNTER THAT FAILS
# =============================================================================


@pytest.mark.asyncio
async def test_u3_a_counter_that_fails_lets_the_call_go(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, counter_clock: CounterClock):
    """6: the counter's engine on a file in a missing folder: ``count_and_check`` returns None and warns; the provider
    is called and answers."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'missing-folder' / 'counters.db'}", poolclass=NullPool)
    monkeypatch.setattr(call_counter, "get_async_engine", lambda: engine)
    _counter_clock_patch(monkeypatch, counter_clock)
    code = _code("dbdown")
    plugin = _bind(_fx_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 5})
    calls = _fetch(plugin)
    try:
        with capture_logs() as events:
            rates = await fx_runtime.call_fx_provider(plugin, calls)
    finally:
        await engine.dispose()

    assert calls.count == 1 and rates["USD"], "the call went"
    warned = [event for event in events if event.get("log_level") == "warning" and code in repr(event)]
    assert len(warned) == 1, f"barrier: the counter was asked, and said it failed: {events}"


# =============================================================================
# 7. THE GROUP OWNER
# =============================================================================


@pytest.mark.asyncio
async def test_u3_two_fx_plugins_of_a_credit_sharing_group_count_on_one_row(counter: Counter, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """7: A and B read ``u3_credits`` (``shares_credits``, hour limit 3 by default), configured by the real FX runtime:
    A, B, A pass on one ``group`` row; B's next call is refused by the group's full window without being called, the
    limit pause B's own."""
    from backend.app.services.fx.base import FXCallLimitError

    print_section("U3 7: one group, one row, one limit")
    register_group(SettingsGroup(name="u3_credits", label="U3 credits", shares_credits=True, fields=(_limit_field("hour", default=3),)))
    code_a, code_b = _code("member_a"), _code("member_b")
    FXProviderRegistry.auto_discover()
    storage = FXProviderRegistry._get_storage()
    for code in (code_a, code_b):
        monkeypatch.setitem(storage, FXProviderRegistry._normalize_lookup_code(code), _fx_class(code, groups=("u3_credits",)))

    async def configured(code: str):
        provider = await fx_runtime.configured_fx_provider(code)
        assert provider is not None and provider.settings.group("u3_credits").get("call_limit_hour") == 3, "barrier: the group's limit reached the instance"
        return provider

    for code in (code_a, code_b, code_a):
        provider = await configured(code)
        calls = _fetch(provider)
        await fx_runtime.call_fx_provider(provider, calls)
        assert calls.count == 1

    refused_b = await configured(code_b)
    calls = _fetch(refused_b)
    with pytest.raises(FXCallLimitError) as refused:
        await fx_runtime.call_fx_provider(refused_b, calls)

    assert calls.count == 0
    assert refused.value.details == {"reason": "call_limit", "window": "hour", "limit": 3}
    assert counter.rows() == {("group", "u3_credits")}, "one row, the group's; none of the plugins'"
    assert counter.counts("group", "u3_credits") == (3,) * 5
    assert provider_cooldown.limit_pause_left("fx", code_b, refused_b.settings.fingerprint) == HOUR_WAIT, "the limit pause is the refused plugin's own"
    assert {_source_key(code_a), _source_key(code_b)}.isdisjoint(_state(cooldowns))
    print_success("A, B, A on one row; B refused by the group's window")


@pytest.mark.asyncio
async def test_u3_an_fx_plugin_of_a_plain_group_counts_on_its_own_row(counter: Counter, monkeypatch: pytest.MonkeyPatch):
    """7: ``u3_plainshare`` has no ``shares_credits``: its hour limit of 1 is not the owner's; two calls pass, counted
    on the plugin's own row; no group row."""
    register_group(SettingsGroup(name="u3_plainshare", label="U3 plain share", fields=(_limit_field("hour", default=1),)))
    code = _code("plainmember")
    FXProviderRegistry.auto_discover()
    monkeypatch.setitem(FXProviderRegistry._get_storage(), FXProviderRegistry._normalize_lookup_code(code), _fx_class(code, groups=("u3_plainshare",)))

    for _ in range(2):
        provider = await fx_runtime.configured_fx_provider(code)
        calls = _fetch(provider)
        await fx_runtime.call_fx_provider(provider, calls)
        assert calls.count == 1

    assert counter.counts("fx", code) == (2,) * 5
    assert ("group", "u3_plainshare") not in counter.rows()


# =============================================================================
# 8. THE CATALOG
# =============================================================================


class _CountedList:
    """The ``get_supported_currencies`` of one instance, counted; it answers the plugin's own list."""

    def __init__(self, provider: Any) -> None:
        self.calls = 0
        self._real = provider.get_supported_currencies

    async def __call__(self) -> list[str]:
        self.calls += 1
        return await self._real()


@pytest.mark.asyncio
async def test_u3_the_catalog_counts_its_list_and_a_full_limit_answers_like_a_refusal(counter: Counter, cooldowns: Cooldowns, monkeypatch: pytest.MonkeyPatch):
    """8: hour limit 1. The first list asked is counted; the cache entry gone, the full hour answers the last known list,
    the provider not called. A second provider with no list yet, its hour full, answers exactly what a provider that
    refuses for too many requests answers: the empty ``unavailable`` list."""
    code = _code("catalog")
    plugin = _bind(_fx_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 1})
    listing = _CountedList(plugin)
    monkeypatch.setattr(plugin, "get_supported_currencies", listing)

    cold = _code("catalogcold")
    cold_plugin = _bind(_fx_class(cold, fields=(_limit_field("hour"),))(), {"call_limit_hour": 1})
    cold_listing = _CountedList(cold_plugin)
    monkeypatch.setattr(cold_plugin, "get_supported_currencies", cold_listing)

    refusing = _code("catalogrefused")
    refusing_plugin = _bind(_fx_class(refusing, external=False)())

    async def refuse() -> list[str]:
        raise FXRateLimitedError("refused for too many requests (u3)", retry_after=HOUR_WAIT)

    monkeypatch.setattr(refusing_plugin, "get_supported_currencies", refuse)
    keys = [catalog._cache_key(code, plugin), catalog._cache_key(cold, cold_plugin), catalog._cache_key(refusing, refusing_plugin)]
    try:
        first = await catalog.get_supported_currencies_status(code, plugin)
        assert (first.currencies, first.unavailable) == (["CHF", "GBP", "JPY", "USD"], False), "barrier: the provider answered its list"
        assert counter.counts("fx", code) == (1,) * 5, "the list asked was counted"

        catalog._currencies_cache.delete(keys[0])
        again = await catalog.get_supported_currencies_status(code, plugin)
        assert (again.currencies, again.unavailable) == (["CHF", "GBP", "JPY", "USD"], False), "the last known list"
        assert listing.calls == 1, "the full hour never called the provider"
        assert counter.counts("fx", code) == (1,) * 5

        await call_counter.count_and_check("fx", cold, None)  # setup: the cold provider's hour is full
        limited = await catalog.get_supported_currencies_status(cold, cold_plugin)
        refused = await catalog.get_supported_currencies_status(refusing, refusing_plugin)
        assert refused == catalog.SupportedCurrencies([], unavailable=True), "barrier: what a refusal answers before any list"
        assert limited == refused, "a full limit answers like a refusal"
        assert cold_listing.calls == 0
        assert counter.counts("fx", cold) == (1,) * 5
        assert {_source_key(code), _source_key(cold)}.isdisjoint(_state(cooldowns)), "a limit is no source refusal"
    finally:
        for key in keys:
            catalog._currencies_cache.delete(key)
        for name in (code, cold, refusing):
            catalog._last_known.pop(name, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


@pytest.mark.asyncio
async def test_u3_a_limit_refusal_leaves_the_trial_of_an_expired_source_pause_free(counter: Counter, cooldowns: Cooldowns, clock: FakeClock):
    """Review: an expired source pause hands its trial to the caller (step 2); a refusal by the limit (its pause, step 3,
    or a full window, step 5) is no verdict on the source, so the source's trial is freed, never held for its seconds."""
    from backend.app.services.fx.base import FXCallLimitError

    for held in (True, False):
        code = _code("trialfree")
        plugin = _bind(_fx_class(code, fields=(_limit_field("hour"),))(), {"call_limit_hour": 1}, fingerprint="u3-trialfree")
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))  # the hour is now full
        if held:
            with pytest.raises(FXCallLimitError):
                await fx_runtime.call_fx_provider(plugin, _fetch(plugin))  # the limit pause is now running
        record_refusal("fx", code, None, 60.0)
        clock.now += 61  # the source pause is over; the limit pause (870 s) is not
        with pytest.raises(FXCallLimitError):
            await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
        source = next(state for state in cooldowns.snapshot() if state.key == _source_key(code))
        assert not source.trial_in_flight, f"held={held}: the source's trial is free after a limit refusal"


@pytest.mark.asyncio
async def test_u3_parallel_calls_after_an_expired_limit_pause_all_reach_the_counter(counter: Counter, cooldowns: Cooldowns, clock: FakeClock, counter_clock: CounterClock):
    """Review: a limit pause ends exactly with its window (rule 1); after it, calls made at once (a sync's providers, a
    page's reads) all reach the counter, which alone decides: none is told to wait for another's trial."""
    from backend.app.services.fx.base import FXCallLimitError

    code = _code("parallel")
    plugin = _bind(_fx_class(code, fields=(_limit_field("minute"),))(), {"call_limit_minute": 2}, fingerprint="u3-parallel")
    for _ in range(2):
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))
    with pytest.raises(FXCallLimitError):
        await fx_runtime.call_fx_provider(plugin, _fetch(plugin))  # paused until the minute ends, 30 s
    _advance(clock, counter_clock, 31)  # the next minute: the pause is over, the window empty

    calls = [_fetch(plugin), _fetch(plugin)]
    await asyncio.gather(*(fx_runtime.call_fx_provider(plugin, fetch) for fetch in calls))
    assert [fetch.count for fetch in calls] == [1, 1], "both reach the counter and are called"
