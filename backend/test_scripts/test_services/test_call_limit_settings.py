# ruff: noqa: PLC0415 — the U4 names are imported inside each test on purpose: red on HEAD, every test fails for its own reason
"""The instance's call limits become settings of the core, owned by whoever owns the count (project 76, lot U4; plan 76
§3.5 «Il limite»).

Modules under test: the new ``services/plugin_settings/call_limits.py``; ``AbstractPluginRegistry.register``
(``services/platform/provider_registry.py``) and ``register_group`` (``services/plugin_settings/groups``), which hand
out the fields; ``readiness.plugin_may_be_unconfigured`` (replacing N2's ``plugin_declares_settings``); the catalogue's
usage block (``schemas/plugin_settings.py``, ``service.read_catalogue``) and ``call_counter.read_counts_many``; the
test-only counting asset provider ``asset_source_providers/mockcount``.

The contract pinned here, by the numbers of the brief:

1. **Core fields.** ``CALL_LIMIT_KEYS`` (``call_limit_<window>``, the five windows in order) and ``CALL_LIMIT_FIELDS``:
   optional system integers, no default, minimum 0, never secret, English label «Calls per <window>», a description,
   no i18n key yet. ``with_call_limits(fields)`` returns a tuple: the given fields, then the core fields whose key is
   missing (a key already declared is kept as declared). The module imports no registry.
2. **Who gets them** (the predicate of ``call_counter.call_owner``): ``register`` gives a class with
   ``calls_external_service`` True that reads no ``shares_credits`` group the missing fields, before validation and
   the claim of the variables; ``register_group`` gives a ``shares_credits`` group the missing fields. Nobody else.
   Pinned on the real registries: every shipped provider that calls out declares the five keys exactly once; the
   local ones and the doubles none; BRIM and tools none. Registering again duplicates nothing.
3. **Their variables** are claimed like any system field's: a valid one locks the field and is the boundary's limit;
   an invalid one (``abc``, ``-1``) leaves the provider not configured.
4. **The fingerprint carries the limits**, through the real binding: for a plugin and for a credit-sharing group's
   reader.
5. **The readiness skip** (``plugin_may_be_unconfigured(family, code, plugin_class)``): True iff a group, a required
   field, or a field whose variable is set; ``plugins_readiness`` answers READY without the database otherwise.
6. **The usage block** of the catalogue (``call_usage``), only on the entry that owns the count, five windows from ONE
   ``now``, counts read once (``read_counts_many``, one SELECT), a database error → every block None and one warning;
   managed profile: a hidden limit is null, ``full`` still judged on it.
8. **mockcount**: registered in test mode only, a double of its own (no other plugin imported, the layout gate's rule
   (d)) that answers as mockprov does (100 USD every day) and calls out, its five core fields, counted.

(Point 7, the frontend filter, is pinned in ``frontend/src/lib/features/plugin-settings/pluginSettingsApi.callLimits.test.ts``.)

Pure: a private SQLite file under ``tmp_path`` built with ``create_all`` stands behind every engine the U4 paths may
ask for (``runtime``, ``readiness`` and ``call_counter``'s ``get_async_engine``); the counter's clock is frozen at
``NOW`` by patching ``call_counter._utc`` — **the catalogue takes its one ``now`` from ``call_counter._utc(None)``**
(directly, or through ``read_counts_many(now=None)``), or the windows are not deterministic. The real asset and FX
registries are read after their discovery and written only through ``monkeypatch.setitem``; the registration tests use
throwaway registries of the base (``_AssetLab``, ``_FxLab``, ``_NoFamilyLab``); groups and claims of this module
(every name starts with ``u4``) are released at teardown. No server, no network: no call ever leaves for a real source.

Red on HEAD c4cf8ae36: no ``call_limits`` module, no fields handed out at registration, no ``plugin_may_be_unconfigured``,
no ``call_usage`` nor ``read_counts_many``, no ``mockcount``. Every negative stands beside a positive in the same test.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import sqlite3
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import IdentifierType
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import PluginCallCounter, PluginSystemSetting, User
from backend.app.schemas.plugin_settings import PluginSettingsPluginRead
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform import call_counter, provider_cooldown
from backend.app.services.platform.provider_registry import AbstractProviderRegistry
from backend.app.services.plugin_settings import readiness, resolver, runtime, service
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.fields import (
    PluginSettingField,
    SettingOption,
    SettingScope,
    SettingsDeclarationError,
    SettingType,
    claimed_env_variables,
    env_name,
    release_env_variables,
    validate_declaration,
)
from backend.app.services.plugin_settings.groups import SettingsGroup, all_groups, get_group, register_group, release_group
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

TEST_INSTANCE_KEY = "u4-call-limit-settings-test-instance-key-0123456789"
WINDOWS = ("minute", "hour", "day", "week", "month")
KEYS = tuple(f"call_limit_{window}" for window in WINDOWS)
LABELS = {f"call_limit_{window}": f"Calls per {window}" for window in WINDOWS}
#: The counter's frozen clock: a Tuesday, 13:45:30 UTC.
NOW = datetime(2026, 11, 17, 13, 45, 30, tzinfo=UTC)
#: The end of each window of ``NOW``.
RESETS = {
    "minute": datetime(2026, 11, 17, 13, 46, tzinfo=UTC),
    "hour": datetime(2026, 11, 17, 14, 0, tzinfo=UTC),
    "day": datetime(2026, 11, 18, 0, 0, tzinfo=UTC),
    "week": datetime(2026, 11, 23, 0, 0, tzinfo=UTC),
    "month": datetime(2026, 12, 1, 0, 0, tzinfo=UTC),
}
#: The shipped providers that reach an external service, and those that do not (U2/U3 pins of their flags).
ASSET_CALLING = ("yfinance", "justetf", "borsa_italiana", "css_scraper")
ASSET_LOCAL = ("scheduled_investment", "mockprov")
FX_CALLING = ("ECB", "FED", "BOE", "SNB", "BDI", "BCB", "NORGES", "NBU", "BOC")
FX_LOCAL = ("MANUAL", "MOCKFX", "MOCKFX_FAIL")
MOCKCOUNT_MODULE = "backend.app.services.asset_source_providers.mockcount.plugin"
YF_DAY_VARIABLE = env_name("asset", "yfinance", "call_limit_day")
YF_HOUR_VARIABLE = env_name("asset", "yfinance", "call_limit_hour")
ECB_MINUTE_VARIABLE = env_name("fx", "ECB", "call_limit_minute")
_ABSENT = object()


# =============================================================================
# THROWAWAY REGISTRIES AND CLASSES
# =============================================================================


class _AssetLab(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "u4_call_limit_lab_assets"

    @classmethod
    def settings_family(cls) -> str:
        return "asset"


class _FxLab(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "u4_call_limit_lab_fx"

    @classmethod
    def settings_family(cls) -> str:
        return "fx"


class _NoFamilyLab(AbstractProviderRegistry):
    """A registry whose plugins declare no settings (``settings_family()`` None), as signals and risk."""

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "u4_call_limit_lab_nofamily"


def _code(label: str) -> str:
    return f"u4_{label}_{uuid.uuid4().hex[:8]}"


def _limit_field(window: str, default: int | None = None) -> PluginSettingField:
    """A limit field a test declares itself, as the U2/U3 test plugins do."""
    return PluginSettingField(key=f"call_limit_{window}", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label=f"Calls per {window} (u4)", default=default, minimum=0)


OWN_FIELD = PluginSettingField(key="region", type=SettingType.SELECT, scope=SettingScope.SYSTEM, label="Region (u4)", default="eu", options=(SettingOption("eu", "EU"), SettingOption("us", "US")))
USER_FIELD = PluginSettingField(key="nickname", type=SettingType.STRING, scope=SettingScope.USER, label="Nickname (u4)")
REQUIRED_FIELD = PluginSettingField(key="endpoint", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="Endpoint (u4)", required=True)
TIER_FIELD = PluginSettingField(key="tier", type=SettingType.SELECT, scope=SettingScope.SYSTEM, label="Tier (u4)", default="free", options=(SettingOption("free", "Free"), SettingOption("paid", "Paid")))


def _lab_class(code: str, *, external: Any = _ABSENT, fields: tuple[PluginSettingField, ...] = (), groups: tuple[str, ...] = ()) -> type:
    """A bare plugin class of the settings mixin: ``external`` is its ``calls_external_service`` (absent by default)."""
    attrs: dict[str, Any] = {"provider_code": code, "provider_name": f"U4 {code}", "settings_fields": fields, "settings_groups": groups}
    if external is not _ABSENT:
        attrs["calls_external_service"] = external
    return type(f"U4Plugin_{code}", (PluginSettingsMixin,), attrs)


def _reader_class(code: str, group: str) -> type:
    """An asset plugin with mockprov's answers that reads ``group`` and declares nothing of its own, calling out."""
    return type(
        f"U4Reader_{code}",
        (MockProvider,),
        {"provider_code": property(lambda self: code), "provider_name": f"U4 {code}", "test_only": False, "calls_external_service": True, "settings_fields": (), "settings_groups": (group,)},
    )


def _keys(plugin_class: type | None) -> list[str]:
    return [declared.key for declared in getattr(plugin_class, "settings_fields", ())]


def _limit_keys(plugin_class: type | None) -> list[str]:
    return [key for key in _keys(plugin_class) if key.startswith("call_limit_")]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Test mode, a test instance key and data directory, the self-hosted profile, no ambient limit variable, no allow-list;
    every u4 group and every claim of a u4 code released at teardown."""
    for name in list(os.environ):
        if "_CALL_LIMIT_" in name or name.endswith("_PROVIDERS_ENABLED") or name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", TEST_INSTANCE_KEY)
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "60")
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "3600")
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    yield
    for name in [name for name in all_groups() if name.startswith("u4")]:
        release_group(name)
    for family, code in set(claimed_env_variables().values()):
        if code.lower().startswith("u4"):
            release_env_variables(family, code)


@pytest.fixture(autouse=True)
def labs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each throwaway registry starts empty, its discovery done."""
    for registry in (_AssetLab, _FxLab, _NoFamilyLab):
        monkeypatch.setattr(registry, "_providers", {})
        monkeypatch.setattr(registry, "_discovery_done", True)


@pytest.fixture(autouse=True)
def cooldowns(monkeypatch: pytest.MonkeyPatch) -> Cooldowns:
    """A private pause table without jitter, in place of the process's: a limit pause never outlives the test."""
    private = Cooldowns(60, 3600, jitter=0.0)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


@pytest.fixture
def discovered() -> None:
    """The real asset and FX registries discovered (read only)."""
    AssetProviderRegistry.auto_discover()
    FXProviderRegistry.auto_discover()


@dataclass(frozen=True)
class Db:
    """The private file, its engine, and how many times the engine was asked for."""

    path: Path
    engine: AsyncEngine
    asks: list[int]

    def execute(self, sql: str, params: tuple = ()) -> None:
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(sql, params)
            connection.commit()
        finally:
            connection.close()


@pytest_asyncio.fixture
async def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Db]:
    """A private file with the whole schema behind every engine the U4 paths ask for; the counter's clock at ``NOW``."""
    path = tmp_path / "u4_call_limit_settings.db"
    sync_engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    asks: list[int] = []

    def private() -> AsyncEngine:
        asks.append(1)
        return engine

    monkeypatch.setattr(runtime, "get_async_engine", private)
    monkeypatch.setattr(readiness, "get_async_engine", private)
    monkeypatch.setattr(call_counter, "get_async_engine", private)
    real_utc = call_counter._utc
    monkeypatch.setattr(call_counter, "_utc", lambda now=None: real_utc(NOW if now is None else now))
    try:
        yield Db(path, engine, asks)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def admin(db: Db) -> User:
    async with AsyncSession(db.engine, expire_on_commit=False) as session:
        user = User(username="u4admin", email="u4admin@example.test", hashed_password="$argon2id$test", is_superuser=True)
        session.add(user)
        await session.commit()
    return user


async def _store(db: Db, family: str, code: str, key: str, value: Any) -> None:
    """An instance row of a plain field, as a write leaves it."""
    async with AsyncSession(db.engine, expire_on_commit=False) as session:
        session.add(PluginSystemSetting(family=family, plugin_code=code, field_key=key, value_json=json.dumps(value)))
        await session.commit()


async def _clear(db: Db, family: str, code: str, key: str) -> None:
    db.execute("DELETE FROM plugin_system_settings WHERE family = ? AND plugin_code = ? AND field_key = ?", (family, code, key))


async def _count_row(db: Db, family: str, code: str, counts: dict[str, int], *, stale: tuple[str, ...] = ()) -> None:
    """A counter row in the windows of ``NOW``; a window named in ``stale`` belongs to the window before."""
    starts = call_counter.window_starts(NOW)
    values: dict[str, Any] = {"family": family, "plugin_code": code, "updated_at": NOW}
    for window in WINDOWS:
        values[f"{window}_since"] = starts[window] - (10 * 86400 * 40 if window in stale else 0)
        values[f"{window}_count"] = counts.get(window, 0)
    async with AsyncSession(db.engine, expire_on_commit=False) as session:
        session.add(PluginCallCounter(**values))
        await session.commit()


async def _catalogue(db: Db, user: User, **filters: Any):
    async with AsyncSession(db.engine, expire_on_commit=False) as session:
        return await service.read_catalogue(session, user, **filters)


def _entry(catalogue, family: str, code: str) -> PluginSettingsPluginRead:
    found = [entry for entry in catalogue.plugins if entry.family == family and entry.plugin_code == code]
    assert len(found) == 1, f"{family}/{code}: {len(found)} entries in the catalogue, expected one: {[(e.family, e.plugin_code) for e in catalogue.plugins]}"
    return found[0]


def _usage(entry: PluginSettingsPluginRead):
    assert "call_usage" in type(entry).model_fields, "PluginSettingsPluginRead has no call_usage"
    return entry.call_usage  # type: ignore[attr-defined]


def _windows(usage) -> list[tuple]:
    return [(window.window, window.count, window.limit, window.resets_at, window.full) for window in usage.windows]


def _counter_selects(engine: AsyncEngine) -> tuple[list[str], Any]:
    """The statements that read the counter table, recorded on the engine; the listener to remove."""
    seen: list[str] = []

    def listener(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, ARG001 — SQLAlchemy's signature
        if "plugin_call_counters" in statement and statement.lstrip().upper().startswith("SELECT"):
            seen.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", listener)
    return seen, listener


# =============================================================================
# 1. THE CORE FIELDS
# =============================================================================


def test_u4_the_core_declares_five_optional_integer_limit_fields():
    """1: the keys in window order; each field an optional system integer, no default, minimum 0, never secret, the
    English label «Calls per <window>», a description, no i18n key yet; valid for every family that holds settings."""
    print_section("U4 1: the core fields")
    from backend.app.services.plugin_settings import call_limits

    assert call_limits.CALL_LIMIT_KEYS == KEYS
    fields = call_limits.CALL_LIMIT_FIELDS
    assert isinstance(fields, tuple) and [declared.key for declared in fields] == list(KEYS)
    for declared in fields:
        assert isinstance(declared, PluginSettingField)
        shape = (declared.type, declared.scope, declared.required, declared.default, declared.minimum, declared.maximum, declared.secret, declared.env)
        assert shape == (SettingType.INTEGER, SettingScope.SYSTEM, False, None, 0, None, False, None), f"{declared.key}: {shape}"
        assert declared.label == LABELS[declared.key]
        assert isinstance(declared.description, str) and declared.description.strip(), f"{declared.key}: no description"
        assert (declared.label_key, declared.description_key) == (None, None), "i18n keys come with U5's interface"
    for family in ("asset", "fx", "group"):
        validate_declaration(fields, family=family)
    print_success("five fields, valid for asset, fx and group")


def test_u4_with_call_limits_adds_only_the_missing_keys_after_the_given_fields():
    """1: a tuple; the given fields first, as given; then the core fields whose key is missing, in window order; a key
    already declared is kept as declared (the same object); idempotent."""
    from backend.app.services.plugin_settings import call_limits

    core_fields = call_limits.CALL_LIMIT_FIELDS
    by_key = {declared.key: declared for declared in core_fields}
    assert call_limits.with_call_limits(()) == core_fields
    assert isinstance(call_limits.with_call_limits(()), tuple)

    own = call_limits.with_call_limits((OWN_FIELD,))
    assert own == (OWN_FIELD, *core_fields)

    custom_hour = _limit_field("hour", default=7)
    mixed = call_limits.with_call_limits((OWN_FIELD, custom_hour))
    assert [declared.key for declared in mixed] == ["region", "call_limit_hour", "call_limit_minute", "call_limit_day", "call_limit_week", "call_limit_month"]
    assert mixed[1] is custom_hour, "a key already declared is kept as declared, default included"
    assert all(mixed[index] is by_key[mixed[index].key] for index in range(2, 6))

    assert call_limits.with_call_limits(mixed) == mixed, "idempotent"
    assert call_limits.with_call_limits(core_fields) == core_fields


def test_u4_the_call_limits_module_imports_no_registry():
    """1: ``call_limits.py`` is imported by the registry base and by the groups: it imports only the settings fields
    (and the standard library), never a registry, a family runtime or the settings service."""
    from backend.app.services.plugin_settings import call_limits

    tree = ast.parse(Path(call_limits.__file__).read_text(encoding="utf-8"))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module} | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    project = {name for name in imported if name.startswith("backend.")}
    assert project <= {"backend.app.services.plugin_settings.fields"}, f"call_limits.py imports {sorted(project)}"


# =============================================================================
# 2. WHO GETS THEM: REGISTRATION
# =============================================================================


def test_u4_register_gives_a_calling_plugin_the_missing_fields_and_claims_their_variables():
    """2: flag True, no group: its own fields first, then the five; the variables of the five claimed for it."""
    print_section("U4 2: a calling plugin")
    code = _code("calling")
    plugin_class = _lab_class(code, external=True, fields=(OWN_FIELD,))

    _AssetLab.register(plugin_class)

    assert _keys(_AssetLab.get_plugin(code)) == ["region", *KEYS]
    claims = claimed_env_variables()
    for key in KEYS:
        assert claims.get(env_name("asset", code, key)) == ("asset", code), f"{key}: its variable is not claimed for the plugin"
    print_success("five fields, five variables claimed")


def test_u4_register_keeps_a_limit_field_the_plugin_declares():
    """2: a plugin that declares ``call_limit_hour`` (with a default, as the U2/U3 test plugins) keeps it, the same
    object; the other four are added, each key once."""
    code = _code("own_hour")
    custom_hour = _limit_field("hour", default=7)
    plugin_class = _lab_class(code, external=True, fields=(custom_hour,))

    _AssetLab.register(plugin_class)

    fields = _AssetLab.get_plugin(code).settings_fields
    assert sorted(declared.key for declared in fields) == sorted(KEYS)
    assert next(declared for declared in fields if declared.key == "call_limit_hour") is custom_hour


@pytest.mark.parametrize("external", [False, _ABSENT], ids=["flag-false", "flag-absent"])
def test_u4_register_gives_nothing_to_a_plugin_that_does_not_call_out(external: Any):
    """2: flag False or absent → its fields as declared (BRIM, tools, the local providers); beside it, a calling sibling
    gets the five (the positive control of the same registry)."""
    quiet = _lab_class(_code("quiet"), external=external, fields=(OWN_FIELD,))
    calling = _lab_class(_code("loud"), external=True, fields=(OWN_FIELD,))

    _AssetLab.register(quiet)
    _AssetLab.register(calling)

    assert _limit_keys(calling) == list(KEYS), "control: the calling sibling gets the five"
    assert _keys(quiet) == ["region"]


def test_u4_a_plugin_reading_a_credit_sharing_group_gets_none_a_plain_group_reader_does():
    """2: the count of a plugin reading a ``shares_credits`` group is the group's: the plugin gets no limit field; a
    plugin reading only a plain group is its own owner and gets the five."""
    register_group(SettingsGroup(name="u4_sharing", label="U4 sharing", shares_credits=True, fields=(TIER_FIELD,)))
    register_group(SettingsGroup(name="u4_plain", label="U4 plain", fields=(TIER_FIELD,)))
    sharing_reader = _lab_class(_code("sharing_reader"), external=True, groups=("u4_sharing",))
    plain_reader = _lab_class(_code("plain_reader"), external=True, groups=("u4_plain",))

    _AssetLab.register(sharing_reader)
    _AssetLab.register(plain_reader)

    assert _limit_keys(plain_reader) == list(KEYS)
    assert _keys(sharing_reader) == []


def test_u4_registering_again_duplicates_no_key():
    """2: the same class registered twice, and a subclass of a registered class under a code of its own: each key once
    (a duplicated key would be refused by ``validate_declaration``)."""
    code = _code("twice")
    plugin_class = _lab_class(code, external=True, fields=(OWN_FIELD,))
    _AssetLab.register(plugin_class)
    _AssetLab.register(plugin_class)
    assert _keys(_AssetLab.get_plugin(code)) == ["region", *KEYS]

    child_code = _code("child")
    child = type(f"U4Child_{child_code}", (plugin_class,), {"provider_code": child_code})
    _AssetLab.register(child)
    assert _keys(_AssetLab.get_plugin(child_code)) == ["region", *KEYS]
    assert claimed_env_variables().get(env_name("asset", child_code, "call_limit_day")) == ("asset", child_code)


@pytest.mark.parametrize(
    ("fields", "groups"),
    [
        ([OWN_FIELD], ()),  # a list, not a tuple
        ((OWN_FIELD, "not a field"), ()),
        ((), "u4_a_string"),  # a string, not a tuple of names
        ((), ("u4_no_such_group",)),
    ],
    ids=["fields-a-list", "fields-hold-a-non-field", "groups-a-string", "groups-unknown-name"],
)
def test_u4_a_wrong_declaration_of_a_calling_plugin_is_still_refused_as_a_declaration_error(fields: Any, groups: Any):
    """2: the fields are handed out BEFORE validation, so a calling plugin's wrong declaration reaches them first: it is
    still refused with ``SettingsDeclarationError`` — never an ``AttributeError`` or a ``TypeError`` of the hand-out,
    never made valid by it (a list silently turned into a tuple) — and it is not registered. Beside it, the control: a
    valid calling sibling gets the five."""
    valid = _lab_class(_code("valid"), external=True, fields=(OWN_FIELD,))
    wrong = _lab_class(_code("wrong"), external=True, fields=fields, groups=groups)

    _AssetLab.register(valid)
    assert _limit_keys(valid) == list(KEYS), "control: a valid calling plugin gets the five"
    with pytest.raises(SettingsDeclarationError):
        _AssetLab.register(wrong)
    assert _AssetLab.get_plugin(wrong.provider_code) is None


def test_u4_a_registry_without_settings_gives_no_field():
    """2: a registry whose plugins declare no settings (``settings_family()`` None) registers a calling class as it is:
    a field there would make the registration refuse it. The same class shape in an asset registry gets the five."""
    nofamily = _lab_class(_code("nofamily"), external=True)
    asset = _lab_class(_code("asset"), external=True)

    _AssetLab.register(asset)
    _NoFamilyLab.register(nofamily)

    assert _limit_keys(asset) == list(KEYS), "control: the asset registry hands them out"
    assert _NoFamilyLab.get_plugin(nofamily.provider_code) is nofamily
    assert _keys(nofamily) == []


def test_u4_an_fx_plugin_gets_them_too():
    """2: the rule is the registry base's, for every settings family: an FX lab plugin that calls out gets the five, its
    variables named for ``fx``."""
    code = _code("fxcalling").upper()
    _FxLab.register(_lab_class(code, external=True))
    assert _limit_keys(_FxLab.get_plugin(code)) == list(KEYS)
    assert claimed_env_variables().get(env_name("fx", code, "call_limit_week")) == ("fx", code)


def test_u4_a_credit_sharing_group_gets_the_missing_fields_a_plain_group_none():
    """2: ``register_group`` hands the missing fields to a ``shares_credits`` group (its own first, a declared limit kept)
    and claims their ``LIBREFOLIO_PLUGIN_GROUP_<NAME>_…`` variables; a plain group stays as declared."""
    print_section("U4 2: groups")
    custom_hour = _limit_field("hour", default=9)
    register_group(SettingsGroup(name="u4_share_g", label="U4 share", shares_credits=True, fields=(TIER_FIELD,)))
    register_group(SettingsGroup(name="u4_share_h", label="U4 share own hour", shares_credits=True, fields=(TIER_FIELD, custom_hour)))
    register_group(SettingsGroup(name="u4_plain_g", label="U4 plain", fields=(TIER_FIELD,)))

    assert [declared.key for declared in get_group("u4_share_g").fields] == ["tier", *KEYS]
    own_hour = get_group("u4_share_h").fields
    assert sorted(declared.key for declared in own_hour) == sorted(["tier", *KEYS]) and own_hour[1] is custom_hour
    assert [declared.key for declared in get_group("u4_plain_g").fields] == ["tier"]
    assert claimed_env_variables().get(env_name("group", "u4_share_g", "call_limit_day")) == ("group", "u4_share_g")
    print_success("the sharing group owns its limits, the plain one has none")


def test_u4_every_shipped_provider_that_calls_out_declares_the_five_keys_once(discovered: None):
    """2, on the real registries: the network providers declare each key exactly once (after their own fields); the
    local ones and the doubles none."""
    print_section("U4 2: the shipped providers")
    asset = {code: AssetProviderRegistry._get_storage().get(code) for code in (*ASSET_CALLING, *ASSET_LOCAL)}
    fx = {code: FXProviderRegistry._get_storage().get(code) for code in (*FX_CALLING, *FX_LOCAL)}
    assert all(asset.values()) and all(fx.values()), f"barrier: a shipped provider is not registered: {[c for c, v in {**asset, **fx}.items() if v is None]}"

    for code in (*ASSET_CALLING,):
        assert _limit_keys(asset[code]) == list(KEYS), f"asset/{code}: {_limit_keys(asset[code])}"
    for code in FX_CALLING:
        assert _limit_keys(fx[code]) == list(KEYS), f"fx/{code}: {_limit_keys(fx[code])}"
    for code in ASSET_LOCAL:
        assert _limit_keys(asset[code]) == [], f"asset/{code} does not call out"
    for code in FX_LOCAL:
        assert _limit_keys(fx[code]) == [], f"fx/{code} does not call out"
    # The ones with fields of their own keep them first
    assert _keys(asset["justetf"])[0] == "preferred_currency" and _keys(asset["borsa_italiana"])[0] == "preferred_language"
    print_success(f"{len(ASSET_CALLING) + len(FX_CALLING)} providers declare the five keys, {len(ASSET_LOCAL) + len(FX_LOCAL)} none")


def test_u4_no_brim_plugin_nor_tool_gets_a_limit_field(discovered: None):
    """2: the import plugins and the tools reach no counted service: none declares a limit key. Beside them, the
    positive control: yfinance does."""
    assert _limit_keys(AssetProviderRegistry._get_storage().get("yfinance")) == list(KEYS), "control: yfinance declares them"
    for family in ("brim", "tool"):
        registry = service.FAMILY_REGISTRIES[family]
        codes = registry.list_plugin_codes()
        assert codes, f"barrier: the {family} registry holds plugins"
        offenders = [code for code in codes if _limit_keys(registry.get_plugin(code))]
        assert offenders == [], f"{family}: {offenders} declare a call limit"


# =============================================================================
# 3. THEIR VARIABLES
# =============================================================================


@pytest.mark.asyncio
async def test_u4_a_limit_variable_locks_the_field_and_is_the_boundary_limit(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """3: ``LIBREFOLIO_PLUGIN_ASSET_YFINANCE_CALL_LIMIT_DAY=2000``: claimed by yfinance, the field locked with source
    ``env`` and value 2000, and the boundary's owner and limits ``("asset", "yfinance", CallLimits(day=2000))``."""
    print_section("U4 3: a limit variable")
    monkeypatch.setenv(YF_DAY_VARIABLE, "2000")

    assert claimed_env_variables().get(YF_DAY_VARIABLE) == ("asset", "yfinance")
    entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")
    day = next(field for field in entry.fields if field.key == "call_limit_day")
    assert (day.locked, day.source, day.value, day.env_variable, day.editable) == (True, "env", 2000, YF_DAY_VARIABLE, False)
    assert entry.configured is True

    provider = await core.configured_provider("yfinance")
    assert call_counter.call_owner(provider, "asset") == ("asset", "yfinance", call_counter.CallLimits(day=2000))
    print_success("locked, and the boundary's limit")


@pytest.mark.asyncio
async def test_u4_an_fx_limit_variable_is_the_fx_boundary_limit(db: Db, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """3: the same through the FX runtime: ``…_FX_ECB_CALL_LIMIT_MINUTE=3`` → ``("fx", "ECB", CallLimits(minute=3))``."""
    monkeypatch.setenv(ECB_MINUTE_VARIABLE, "3")
    provider = await fx_runtime.configured_fx_provider("ECB")
    assert call_counter.call_owner(provider, "fx") == ("fx", "ECB", call_counter.CallLimits(minute=3))


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["abc", "-1"])
async def test_u4_an_invalid_limit_variable_leaves_the_provider_not_configured(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch, value: str):
    """3: an invalid value (not a whole number, below the minimum 0) is the rule of every field: the field is missing,
    the provider not configured — at the binding, in the readiness check and in the catalogue (``invalid_env``)."""
    monkeypatch.setenv(YF_DAY_VARIABLE, value)

    provider = await core.configured_provider("yfinance")
    assert provider.settings.missing == ("call_limit_day",)
    assert (await readiness.plugin_readiness("asset", "yfinance", user_id=None)).configured is False
    entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")
    day = next(field for field in entry.fields if field.key == "call_limit_day")
    assert (entry.configured, day.problem, day.locked) == (False, "invalid_env", True)


# =============================================================================
# 4. THE FINGERPRINT CARRIES THE LIMITS
# =============================================================================


@pytest.mark.asyncio
async def test_u4_a_stored_limit_changes_a_plugins_fingerprint(db: Db, discovered: None):
    """4: yfinance and ECB through the real binding: a stored ``call_limit_hour`` of 1, of 2, and none give three different
    fingerprints."""
    print_section("U4 4: fingerprints")
    for family, code, configure in (("asset", "yfinance", core.configured_provider), ("fx", "ECB", fx_runtime.configured_fx_provider)):
        seen = []
        for value in (1, 2, None):
            await _clear(db, family, code, "call_limit_hour")
            if value is not None:
                await _store(db, family, code, "call_limit_hour", value)
            provider = await configure(code)
            seen.append(provider.settings.fingerprint)
        await _clear(db, family, code, "call_limit_hour")
        assert len(set(seen)) == 3, f"{family}/{code}: fingerprints {seen}"
    print_success("three values, three fingerprints, for an asset and an FX provider")


@pytest.mark.asyncio
async def test_u4_a_credit_sharing_groups_limit_changes_its_readers_fingerprint(db: Db, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """4: the group's row (``family="group"``) changes the fingerprint of the plugin that reads it."""
    register_group(SettingsGroup(name="u4_fp_group", label="U4 fingerprint", shares_credits=True, fields=(TIER_FIELD,)))
    code = _code("fp_reader")
    monkeypatch.setitem(AssetProviderRegistry._get_storage(), code, _reader_class(code, "u4_fp_group"))

    seen = []
    for value in (1, 2, None):
        await _clear(db, "group", "u4_fp_group", "call_limit_hour")
        if value is not None:
            await _store(db, "group", "u4_fp_group", "call_limit_hour", value)
        provider = await core.configured_provider(code)
        seen.append(provider.settings.fingerprint)
    assert len(set(seen)) == 3, f"reader fingerprints {seen}"
    await _store(db, "group", "u4_fp_group", "call_limit_hour", 4)
    provider = await core.configured_provider(code)
    assert call_counter.call_owner(provider, "asset") == ("group", "u4_fp_group", call_counter.CallLimits(hour=4))


# =============================================================================
# 5. THE READINESS SKIP
# =============================================================================


def test_u4_plugin_may_be_unconfigured_is_true_only_for_a_group_a_required_field_or_a_set_variable(monkeypatch: pytest.MonkeyPatch):
    """5: False for nothing, for optional fields only (the core five, a user field); True for a group (even a plain one),
    a required field, an optional system field whose variable is set (valid or not); False for no class."""
    print_section("U4 5: the skip predicate")
    from backend.app.services.plugin_settings import call_limits
    from backend.app.services.plugin_settings.readiness import plugin_may_be_unconfigured

    register_group(SettingsGroup(name="u4_ready_plain", label="U4 plain", fields=(TIER_FIELD,)))
    core_only = _lab_class(_code("core_only"), external=True, fields=call_limits.with_call_limits(()))
    with_user = _lab_class(_code("with_user"), external=True, fields=call_limits.with_call_limits((USER_FIELD,)))
    required = _lab_class(_code("required"), fields=(REQUIRED_FIELD,))
    grouped = _lab_class(_code("grouped"), groups=("u4_ready_plain",))
    bare = _lab_class(_code("bare"))

    assert plugin_may_be_unconfigured("asset", core_only.provider_code, core_only) is False
    assert plugin_may_be_unconfigured("asset", with_user.provider_code, with_user) is False
    assert plugin_may_be_unconfigured("asset", bare.provider_code, bare) is False
    assert plugin_may_be_unconfigured("asset", "u4_nobody", None) is False
    assert plugin_may_be_unconfigured("asset", required.provider_code, required) is True
    assert plugin_may_be_unconfigured("asset", grouped.provider_code, grouped) is True

    variable = env_name("asset", core_only.provider_code, "call_limit_day")
    for value in ("500", "abc"):
        monkeypatch.setenv(variable, value)
        assert plugin_may_be_unconfigured("asset", core_only.provider_code, core_only) is True, f"a variable set to {value!r}"
    monkeypatch.delenv(variable)
    monkeypatch.setenv(variable + "_FILE", "/nonexistent/u4-limit")
    assert plugin_may_be_unconfigured("asset", core_only.provider_code, core_only) is True, "a _FILE variable is set too"
    print_success("the predicate")


def test_u4_the_shipped_providers_with_only_optional_fields_are_cleared(discovered: None, monkeypatch: pytest.MonkeyPatch):
    """5: every shipped calling provider (core fields, and optional user fields of justetf and borsa_italiana) → False;
    mockprov, which reads a group, → True; yfinance with its day limit variable set (even invalid) → True."""
    from backend.app.services.plugin_settings.readiness import plugin_may_be_unconfigured

    asset_storage, fx_storage = AssetProviderRegistry._get_storage(), FXProviderRegistry._get_storage()
    assert _limit_keys(asset_storage["yfinance"]) == list(KEYS), "barrier: yfinance declares the five keys"
    for code in ASSET_CALLING:
        assert plugin_may_be_unconfigured("asset", code, asset_storage[code]) is False, f"asset/{code}"
    for code in FX_CALLING:
        assert plugin_may_be_unconfigured("fx", code, fx_storage[code]) is False, f"fx/{code}"
    assert plugin_may_be_unconfigured("asset", "mockprov", asset_storage["mockprov"]) is True
    monkeypatch.setenv(YF_DAY_VARIABLE, "abc")
    assert plugin_may_be_unconfigured("asset", "yfinance", asset_storage["yfinance"]) is True


def test_u4_plugin_declares_settings_is_replaced_at_both_call_sites():
    """5: N2's ``plugin_declares_settings`` is gone; the asset assignment write and the FX routes write use the new
    predicate (the ``api fx-unit`` tests that count ``execute`` pin the effect)."""
    root = Path(readiness.__file__).resolve().parents[3]
    assert hasattr(readiness, "plugin_may_be_unconfigured"), "readiness.plugin_may_be_unconfigured is missing"
    assert not hasattr(readiness, "plugin_declares_settings"), "N2's plugin_declares_settings is still there"
    for relative in ("app/services/assets/provider_management.py", "app/api/v1/fx/providers.py"):
        text = (root / relative).read_text(encoding="utf-8")
        assert "plugin_may_be_unconfigured" in text and "plugin_declares_settings" not in text, relative


@pytest.mark.asyncio
async def test_u4_plugins_readiness_answers_ready_without_the_database_for_a_cleared_plugin(db: Db, monkeypatch: pytest.MonkeyPatch):
    """5: a plugin with only optional limit fields and no variable is READY and the engine is never asked for; the same
    plugin with a variable set is read (one ask) and judged."""
    code = _code("cleared")
    plugin_class = _lab_class(code, external=True, fields=tuple(_limit_field(window) for window in WINDOWS))
    monkeypatch.setitem(service.FAMILY_REGISTRIES, "asset", _AssetLab)
    _AssetLab._get_storage()[code] = plugin_class

    db.asks.clear()
    answer = await readiness.plugins_readiness("asset", [code], user_id=None)
    assert answer == {code: readiness.READY}
    assert db.asks == [], f"the engine was asked {len(db.asks)} time(s) for a plugin nothing can leave unconfigured"

    monkeypatch.setenv(env_name("asset", code, "call_limit_day"), "abc")
    answer = await readiness.plugins_readiness("asset", [code], user_id=None)
    assert answer[code].configured is False and answer[code].missing == ("call_limit_day",)


# =============================================================================
# 6. THE USAGE BLOCK
# =============================================================================


def test_u4_the_usage_schemas():
    """6: ``PluginCallWindow`` {window, count, limit | None, resets_at, full}, the window one of the five; ``PluginCallUsage``
    {family, plugin_code, windows}; ``PluginSettingsPluginRead.call_usage`` None by default."""
    from backend.app.schemas.plugin_settings import PluginCallUsage, PluginCallWindow

    assert PluginSettingsPluginRead.model_fields["call_usage"].default is None
    windows = [PluginCallWindow(window=window, count=1, limit=None, resets_at=RESETS[window], full=False) for window in WINDOWS]
    usage = PluginCallUsage(family="asset", plugin_code="yfinance", windows=windows)
    assert [window.window for window in usage.windows] == list(WINDOWS)
    assert PluginCallUsage(family="group", plugin_code="u4_g", windows=[]).plugin_code == "u4_g"
    with pytest.raises(ValidationError):
        PluginCallWindow(window="year", count=1, limit=None, resets_at=RESETS["day"], full=False)
    dumped = usage.model_dump(mode="json")
    assert set(dumped) == {"family", "plugin_code", "windows"}
    assert set(dumped["windows"][0]) == {"window", "count", "limit", "resets_at", "full"}


@pytest.mark.asyncio
async def test_u4_read_counts_many_reads_every_pair_in_one_select(db: Db):
    """6: one SELECT for every pair asked; a current row's counts, a stale window 0, a pair without a row all zeros."""
    rows = [("asset", "u4_rc_a"), ("asset", "u4_rc_b"), ("group", "u4_rc_g")]
    await _count_row(db, "asset", "u4_rc_a", {"minute": 1, "hour": 2, "day": 3, "week": 4, "month": 5})
    await _count_row(db, "group", "u4_rc_g", {"minute": 6, "hour": 7, "day": 8, "week": 9, "month": 10}, stale=("minute", "hour"))
    selects, listener = _counter_selects(db.engine)
    try:
        counts = await call_counter.read_counts_many(rows, now=NOW)
    finally:
        event.remove(db.engine.sync_engine, "before_cursor_execute", listener)

    assert counts == {
        ("asset", "u4_rc_a"): call_counter.CallCounts(1, 2, 3, 4, 5),
        ("asset", "u4_rc_b"): call_counter.ZERO,
        ("group", "u4_rc_g"): call_counter.CallCounts(0, 0, 8, 9, 10),
    }
    assert len(selects) == 1, f"{len(selects)} SELECTs on the counter table"


@pytest.mark.asyncio
async def test_u4_the_catalogue_shows_the_usage_of_a_calling_plugin(db: Db, admin: User, discovered: None):
    """6: yfinance, limits hour 5 and day 2000 stored, counts minute stale, hour 5, day 7, week 9, month 11 → the five
    windows in order, each with its count, its limit (None where none), the end of its window of NOW (aware UTC) and
    ``full`` (hour only)."""
    print_section("U4 6: the usage block")
    await _store(db, "asset", "yfinance", "call_limit_hour", 5)
    await _store(db, "asset", "yfinance", "call_limit_day", 2000)
    await _count_row(db, "asset", "yfinance", {"minute": 2, "hour": 5, "day": 7, "week": 9, "month": 11}, stale=("minute",))

    usage = _usage(_entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance"))

    assert usage is not None and (usage.family, usage.plugin_code) == ("asset", "yfinance")
    assert _windows(usage) == [
        ("minute", 0, None, RESETS["minute"], False),
        ("hour", 5, 5, RESETS["hour"], True),
        ("day", 7, 2000, RESETS["day"], False),
        ("week", 9, None, RESETS["week"], False),
        ("month", 11, None, RESETS["month"], False),
    ]
    assert all(window.resets_at.utcoffset() == timedelta(0) for window in usage.windows)
    print_success("five windows, one now")


@pytest.mark.asyncio
async def test_u4_the_catalogue_reads_the_counts_once_and_shows_usage_only_on_the_owner(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """6: the whole catalogue reads the counter table with ONE SELECT (``read_counts_many`` once, never ``read_counts``);
    every calling provider has a block (no row reads zeros); a plugin that does not call out (mockprov, named) has none;
    the test-only mockcount, named, has one."""
    assert hasattr(call_counter, "read_counts_many"), "call_counter.read_counts_many is missing"
    many_calls: list[list] = []
    real_many = call_counter.read_counts_many

    async def counted_many(pairs, *, now=None):
        many_calls.append(list(pairs))
        return await real_many(pairs, now=now)

    async def no_single(*_args, **_kwargs):
        raise AssertionError("the catalogue reads the counts per entry")

    monkeypatch.setattr(call_counter, "read_counts_many", counted_many)
    monkeypatch.setattr(call_counter, "read_counts", no_single)
    await _count_row(db, "fx", "ECB", {"minute": 1, "hour": 1, "day": 1, "week": 1, "month": 1})
    selects, listener = _counter_selects(db.engine)
    try:
        everything = await _catalogue(db, admin)
    finally:
        event.remove(db.engine.sync_engine, "before_cursor_execute", listener)

    assert len(many_calls) == 1 and len(selects) == 1, f"read_counts_many called {len(many_calls)} time(s), {len(selects)} SELECTs"
    for code in ASSET_CALLING:
        usage = _usage(_entry(everything, "asset", code))
        assert usage is not None and [window.count for window in usage.windows] == [0, 0, 0, 0, 0], f"asset/{code}"
    for code in FX_CALLING:
        assert _usage(_entry(everything, "fx", code)) is not None, f"fx/{code}"
    assert [window.count for window in _usage(_entry(everything, "fx", "ECB")).windows] == [1, 1, 1, 1, 1]
    assert _usage(_entry(everything, "brim", "broker_generic_csv")) is None, "an import plugin calls nothing out"

    assert _usage(_entry(await _catalogue(db, admin, plugin_code="mockprov"), "asset", "mockprov")) is None
    counted = _usage(_entry(await _catalogue(db, admin, plugin_code="mockcount"), "asset", "mockcount"))
    assert counted is not None and (counted.family, counted.plugin_code) == ("asset", "mockcount")


@pytest.mark.asyncio
async def test_u4_a_credit_sharing_group_owns_the_usage_block_of_its_readers(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """6: the reader of a ``shares_credits`` group has no block; the group's entry has it, ``family="group"``, its counts
    and the limits of the group's rows."""
    register_group(SettingsGroup(name="u4_usage_group", label="U4 usage", shares_credits=True, fields=(TIER_FIELD,)))
    code = _code("usage_reader")
    monkeypatch.setitem(AssetProviderRegistry._get_storage(), code, _reader_class(code, "u4_usage_group"))
    await _store(db, "group", "u4_usage_group", "call_limit_hour", 4)
    await _count_row(db, "group", "u4_usage_group", {"minute": 1, "hour": 4, "day": 4, "week": 4, "month": 4})

    group_usage = _usage(_entry(await _catalogue(db, admin, plugin_code="u4_usage_group"), "group", "u4_usage_group"))
    reader = _entry(await _catalogue(db, admin, plugin_code=code), "asset", code)

    assert group_usage is not None and (group_usage.family, group_usage.plugin_code) == ("group", "u4_usage_group")
    assert _windows(group_usage)[1] == ("hour", 4, 4, RESETS["hour"], True)
    assert [window.count for window in group_usage.windows] == [1, 4, 4, 4, 4]
    assert _usage(reader) is None, "the reader's count is the group's"


@pytest.mark.asyncio
async def test_u4_a_database_error_reading_the_counts_leaves_every_block_none_with_one_warning(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """6: the counter table missing (a dev database that reached 006 before U1): the catalogue answers, every block None,
    and exactly one warning more than the same catalogue with the table."""
    with capture_logs() as healthy_logs:
        healthy = await _catalogue(db, admin)
    assert _usage(_entry(healthy, "asset", "yfinance")) is not None, "barrier: with the table, yfinance has a block"

    db.execute("DROP TABLE plugin_call_counters")
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    with capture_logs() as broken_logs:
        broken = await _catalogue(db, admin)

    assert {(entry.family, entry.plugin_code) for entry in broken.plugins} == {(entry.family, entry.plugin_code) for entry in healthy.plugins}
    assert all(_usage(entry) is None for entry in broken.plugins)
    healthy_warnings = [entry for entry in healthy_logs if entry.get("log_level") == "warning"]
    broken_warnings = [entry for entry in broken_logs if entry.get("log_level") == "warning"]
    assert len(broken_warnings) == len(healthy_warnings) + 1, f"warnings: {[entry.get('event') for entry in broken_warnings]}"


@pytest.mark.asyncio
async def test_u4_the_usage_block_follows_the_lock_in_the_self_hosted_profile(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """6, control of the managed case: a limit the variable locks is shown, the field locked, the window full on it."""
    monkeypatch.setenv(YF_HOUR_VARIABLE, "5")
    await _count_row(db, "asset", "yfinance", {"hour": 5})

    entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")

    assert next(field for field in entry.fields if field.key == "call_limit_hour").locked is True
    assert _windows(_usage(entry))[1] == ("hour", 5, 5, RESETS["hour"], True)


@pytest.mark.asyncio
async def test_u4_in_the_managed_profile_a_hidden_limit_is_null_and_full_is_still_judged_on_it(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """6: managed, the hour limit locked by its variable → the field hidden, the window's ``limit`` null (the value is
    never shown) and ``full`` true on the real limit; a stored day limit, not hidden, is shown."""
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    assert service._is_managed(), "barrier: the service reads the managed profile"
    monkeypatch.setenv(YF_HOUR_VARIABLE, "5")
    await _store(db, "asset", "yfinance", "call_limit_day", 2000)
    await _count_row(db, "asset", "yfinance", {"hour": 5, "day": 6})

    entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")

    keys = [field.key for field in entry.fields]
    assert "call_limit_hour" not in keys and "call_limit_day" in keys
    windows = _windows(_usage(entry))
    assert windows[1] == ("hour", 5, None, RESETS["hour"], True)
    assert windows[2] == ("day", 6, 2000, RESETS["day"], False)
    assert "5" not in json.dumps([window[2] for window in windows]), "the hidden value never travels"


# =============================================================================
# 8. MOCKCOUNT
# =============================================================================


def test_u4_mockcount_is_a_calling_mock_with_the_five_core_fields(discovered: None):
    """8: registered in test mode, from its own package (``__init__.py`` a docstring only, ``plugin.py``), a direct
    ``AssetSourceProvider`` (a plugin never imports another plugin: no ``MockProvider`` subclass), test-only, calling out
    in its own class, no group, its fields the five core ones."""
    plugin_class = AssetProviderRegistry.get_plugin("mockcount")
    assert plugin_class is not None, "mockcount is not registered in test mode"
    assert plugin_class.__module__ == MOCKCOUNT_MODULE
    assert plugin_class.__bases__ == (AssetSourceProvider,), f"its own double, no other plugin's class: {plugin_class.__bases__}"
    assert not issubclass(plugin_class, MockProvider)
    assert getattr(plugin_class, "test_only", False) is True
    assert vars(plugin_class).get("calls_external_service") is True
    assert tuple(plugin_class.settings_groups) == ()
    assert _keys(plugin_class) == list(KEYS), "its fields are the five core ones (mockprov's api_key alias is mockprov's own)"
    assert plugin_class().provider_code == "mockcount"
    tree = ast.parse(Path(inspect.getfile(plugin_class)).with_name("__init__.py").read_text(encoding="utf-8"))
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str), "__init__.py holds its docstring only"


def test_u4_mockcount_is_withheld_outside_test_mode(discovered: None, monkeypatch: pytest.MonkeyPatch):
    """8: served in test mode (barrier), absent from every door outside it, as every test-only provider."""
    assert AssetProviderRegistry.get_plugin("mockcount") is not None and "mockcount" in AssetProviderRegistry.list_plugin_codes(), "barrier: served in test mode"
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE")
    assert AssetProviderRegistry.get_plugin("mockcount") is None
    assert "mockcount" not in AssetProviderRegistry.list_plugin_codes()


@pytest.mark.asyncio
async def test_u4_mockcount_is_counted_at_the_boundary_and_refused_at_its_stored_limit(db: Db, discovered: None):
    """8: each call through ``call_provider`` counts on ``("asset", "mockcount")``; with ``call_limit_minute`` stored at 2,
    the third call is refused (``RATE_LIMITED``, reason ``call_limit``) and not counted."""
    print_section("U4 8: mockcount at the boundary")
    await _store(db, "asset", "mockcount", "call_limit_minute", 2)

    for expected in (1, 2):
        provider = await core.configured_provider("mockcount")
        assert provider is not None, "mockcount is not configured"
        quote = await core.call_provider(provider, lambda provider=provider: provider.get_current_value("MOCK", IdentifierType.TICKER, {}), timeout=10)
        assert quote.value == 100
        assert (await call_counter.read_counts("asset", "mockcount")).minute == expected

    provider = await core.configured_provider("mockcount")
    with pytest.raises(AssetRateLimitedError) as refused:
        await core.call_provider(provider, lambda: provider.get_current_value("MOCK", IdentifierType.TICKER, {}), timeout=10)
    assert refused.value.error_code == "RATE_LIMITED" and (refused.value.details or {}).get("reason") == "call_limit"
    assert (await call_counter.read_counts("asset", "mockcount")).minute == 2
    print_success("two counted, the third refused at the stored limit")


# =============================================================================
# 9. ONE READ OF A PLUGIN'S SETTINGS PER OPERATION (the coordinator's measure)
# =============================================================================


@pytest.mark.asyncio
async def test_u4_inside_one_operation_a_plugins_settings_are_read_once(db: Db, discovered: None):
    """U4 made every provider that calls out declare settings, so ``configure_instance`` reads the rows at each
    ``configured_provider``: N per-asset reads of one provider would open N sessions. Inside
    ``runtime.one_binding_per_plugin()`` (opened by the live read and the refresh) the binding of a plugin is read once
    and reused: five configurations of css_scraper and three of yfinance open two sessions; outside it, each opens one."""
    await _store(db, "asset", "css_scraper", "call_limit_hour", 9)
    db.asks.clear()
    with runtime.one_binding_per_plugin():
        providers = [await core.configured_provider("css_scraper") for _ in range(5)] + [await core.configured_provider("yfinance") for _ in range(3)]
    assert len(db.asks) == 2, f"{len(db.asks)} sessions for 8 configurations of 2 plugins"
    assert all(provider.settings.get("call_limit_hour") == 9 for provider in providers[:5]), "the reused binding is the plugin's"
    assert len({provider.settings.fingerprint for provider in providers[:5]}) == 1

    db.asks.clear()
    for _ in range(3):
        await core.configured_provider("css_scraper")
    assert len(db.asks) == 3, "outside the operation each configuration reads its rows, as before"


@pytest.mark.asyncio
async def test_u4_the_live_read_and_the_refresh_open_one_binding_scope(monkeypatch: pytest.MonkeyPatch):
    """The two per-asset paths run inside ``runtime.one_binding_per_plugin()``: ``get_current_prices_bulk`` and
    ``bulk_refresh_prices`` (their source names it)."""
    from backend.app.services.assets import price_query, refresh

    assert "one_binding_per_plugin" in inspect.getsource(price_query.AssetSourceManager.get_current_prices_bulk if hasattr(price_query, "AssetSourceManager") else price_query)
    assert "one_binding_per_plugin" in inspect.getsource(refresh)


@pytest.mark.asyncio
async def test_u4_configurations_started_together_share_one_read(db: Db, discovered: None):
    """Review: the live read configures its per-asset providers at once (``asyncio.gather``): configurations of one
    plugin started together inside the operation share the first one's read, not one each."""
    import asyncio

    await _store(db, "asset", "css_scraper", "call_limit_hour", 9)
    db.asks.clear()
    with runtime.one_binding_per_plugin():
        providers = await asyncio.gather(*(core.configured_provider("css_scraper") for _ in range(6)))
    assert len(db.asks) == 1, f"{len(db.asks)} sessions for 6 configurations started together"
    assert {provider.settings.get("call_limit_hour") for provider in providers} == {9}


# =============================================================================
# U4b. THE MANAGED PROFILE WITH EVERY LIMIT LOCKED: THE USAGE BLOCK STAYS
# =============================================================================


@pytest.mark.asyncio
async def test_u4b_a_managed_entry_whose_limits_are_all_locked_keeps_its_usage_block(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """The consultant's rule after U4: in the managed profile, yfinance with its five limits locked by the hoster's
    variables lists no field, yet its entry stays, read-only, with its usage block — every count shown, every limit
    null, and ``full`` judged on the real limit (here the hour: 3 counted, limit 3)."""
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    for window, value in zip(WINDOWS, (100, 3, 1000, 5000, 20000), strict=True):
        monkeypatch.setenv(env_name("asset", "yfinance", f"call_limit_{window}"), str(value))
    await _count_row(db, "asset", "yfinance", {"minute": 1, "hour": 3, "day": 4, "week": 5, "month": 6})

    entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")

    assert entry.fields == [], "every limit field hidden in the managed profile"
    windows = _windows(_usage(entry))
    assert [window[1] for window in windows] == [1, 3, 4, 5, 6]
    assert [window[2] for window in windows] == [None] * 5, "no locked value is shown"
    assert [window[4] for window in windows] == [False, True, False, False, False]


@pytest.mark.asyncio
async def test_u4b_a_managed_credit_sharing_group_whose_limits_are_all_locked_keeps_its_usage_block(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """The same rule for the owner of a shared count: a ``shares_credits`` group whose every field (the five limits) the
    hoster locks stays listed with no field and its usage block; its reader, which has nothing of its own, names no
    hidden group and so is not listed (N2: no dead link) — the group's block is where its count shows."""
    register_group(SettingsGroup(name="u4b_locked_group", label="U4b locked", shares_credits=True, fields=()))
    code = _code("u4b_reader")
    monkeypatch.setitem(AssetProviderRegistry._get_storage(), code, _reader_class(code, "u4b_locked_group"))
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    for window, value in zip(WINDOWS, (10, 2, 100, 500, 2000), strict=True):
        monkeypatch.setenv(env_name("group", "u4b_locked_group", f"call_limit_{window}"), str(value))
    await _count_row(db, "group", "u4b_locked_group", {"minute": 1, "hour": 2, "day": 2, "week": 2, "month": 2})

    catalogue = await _catalogue(db, admin)
    group = _entry(catalogue, "group", "u4b_locked_group")

    assert group.fields == [], "every limit field hidden in the managed profile"
    windows = _windows(_usage(group))
    assert [window[1] for window in windows] == [1, 2, 2, 2, 2]
    assert [window[2] for window in windows] == [None] * 5, "no locked value is shown"
    assert [window[4] for window in windows] == [False, True, False, False, False]
    assert not [entry for entry in catalogue.plugins if entry.plugin_code == code], "the reader names no hidden group"


# =============================================================================
# 9. U5b — THE CATALOGUE CARRIES THE READINESS REASON (the consultant, 19/11)
# =============================================================================


@pytest.mark.asyncio
async def test_u5b_a_managed_entry_with_an_invalid_limit_variable_says_invalid_locked_setting_even_with_some_limits_shown(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """U5b: the entry carries the reason the readiness check gives (N1/N2), not one guessed by the interface. In the
    managed profile, one limit locked by an invalid variable and the others free: ``reason`` is
    ``invalid_locked_setting``, while some limit fields are still listed."""
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv(YF_HOUR_VARIABLE, "not-a-number")
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())

    entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")

    assert entry.configured is False
    assert [field.key for field in entry.fields if field.key.startswith("call_limit_")], "barrier: some limits are still listed"
    assert entry.reason == "invalid_locked_setting"


@pytest.mark.asyncio
async def test_u5b_a_configured_entry_has_no_reason(db: Db, admin: User, discovered: None):
    entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")
    assert (entry.configured, entry.reason) == (True, None)


@pytest.mark.asyncio
async def test_u5b_the_reason_is_the_readiness_checks_own(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """The same answer as the boundary's check (``plugins_readiness``), whatever the case: invalid variable, then valid."""
    for value, expected in (("not-a-number", "invalid_locked_setting"), ("5", None)):
        monkeypatch.setenv(YF_HOUR_VARIABLE, value)
        monkeypatch.setattr(resolver, "_warned_invalid_env", set())
        entry = _entry(await _catalogue(db, admin, family="asset", plugin_code="yfinance"), "asset", "yfinance")
        check = (await readiness.plugins_readiness("asset", ["yfinance"], user_id=admin.id))["yfinance"]
        assert entry.reason == check.reason == expected, value


@pytest.mark.asyncio
async def test_u5b_a_reader_of_a_credit_sharing_group_gets_the_groups_reason_as_the_boundary_does(db: Db, admin: User, discovered: None, monkeypatch: pytest.MonkeyPatch):
    """CoinGecko's shape: the invalid variable is a limit of the shared group, not of the plugin. The reader's entry and
    the group's entry say ``invalid_locked_setting``, and the reader's is the boundary check's own answer."""
    register_group(SettingsGroup(name="u4_u5b_group", label="U5b group", shares_credits=True, fields=()))
    code = _code("u5b_reader")
    monkeypatch.setitem(AssetProviderRegistry._get_storage(), code, _reader_class(code, "u4_u5b_group"))
    monkeypatch.setenv(env_name("group", "u4_u5b_group", "call_limit_hour"), "not-a-number")
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())

    catalogue = await _catalogue(db, admin)
    reader = _entry(catalogue, "asset", code)
    group = _entry(catalogue, "group", "u4_u5b_group")
    check = (await readiness.plugins_readiness("asset", [code], user_id=admin.id))[code]

    assert check.reason == "invalid_locked_setting", "barrier: the boundary refuses the reader"
    assert reader.reason == check.reason
    assert group.reason == "invalid_locked_setting"
