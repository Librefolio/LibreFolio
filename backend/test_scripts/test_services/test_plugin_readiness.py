# ruff: noqa: PLC0415 — the new names are imported inside each test on purpose: red on HEAD, every test fails for its own reason
"""Plugin settings, one readiness check for every plugin (project 76, lot N1).

Modules under test: ``services/plugin_settings/readiness.py`` (new), the schemas ``FAProviderInfo`` and ``FXProviderInfo``, and the
two provider lists ``GET /assets/provider`` and ``GET /fx/providers``. The contract pinned here:

1. **One check, the rule of the call boundary** (``readiness.plugins_readiness(family, codes, *, user_id)``, ``plugin_readiness``):
   ``PluginReadiness(configured, missing)`` is a frozen dataclass; one entry per code asked; a code the family's registry
   (``service.FAMILY_REGISTRIES``) does not know, and a plugin with no field and no group, are ``PluginReadiness(True, ())``.
   ``configured`` is True exactly when ``configure_instance(<new instance>, family, user_id=…).settings.missing`` is empty,
   compared case by case on the same state: a required field unset, set by a row, set by the variable; an invalid variable
   on an optional field; a stored secret the current instance key cannot read; a required group field unset, then set by a
   row and by its variable; own and group fields together (own keys first, ``<group>.<field>``); a user field of the caller,
   of another user, and with no user at all.
2. **How it reads**: the database in ONE short session of its own for all the codes asked (the engine is asked once), never
   a secret decrypted, the instance key only for the key id of a stored secret.
3. **``missing``**: the keys of ``BoundSettings.missing``; in the managed profile (``LIBREFOLIO_PROFILE=managed``) a field
   locked by a variable is hidden (decision N2): ``configured`` still counts it, ``missing`` does not name it, whether the
   variable is valid or not.
4. **Schemas**: ``FAProviderInfo`` and ``FXProviderInfo`` carry ``configured: bool = True`` and ``missing_settings: list[str] = []``.
5. **The provider lists** fill both for the caller (``user.id``) with ONE ``plugins_readiness`` call per request: a plugin that
   needs a key is listed ``configured: false, missing_settings: ["api_key"]`` and, once the key is set, ``true`` and ``[]``;
   a plugin that needs nothing stays ``true`` and ``[]``; a plugin whose group lacks its token names ``"<group>.token"``.

Red on HEAD 588fb33b2: ``readiness.py`` does not exist and the two schemas lack the fields. Every test imports the new names
inside its body, so each one fails for its own reason.

How the tests reach the database: ``runtime.get_async_engine`` is replaced by one that counts its calls and answers the test's
private engine; the same replacement is put on ``readiness.get_async_engine`` when that module has such a name. The check must
open its session through one of the two, and ask for the engine once.

Pure: a private SQLite file under ``tmp_path``, a test instance key, a data directory in ``tmp_path``, every variable through
``monkeypatch``, no server, no network. Every group and plugin code of this module starts with ``n1``; the teardown releases
every group of that name. The family registries are throwaway ones for the readiness tests; the two provider lists run in
process on the real registries, which receive test-only-free plugin classes of this module for the length of a test.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.platform.provider_registry import AbstractProviderRegistry
from backend.app.services.plugin_settings import resolver, runtime, service
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, env_name
from backend.app.services.plugin_settings.groups import SettingsGroup, all_groups, register_group, release_group
from backend.test_scripts.test_utils import print_section, print_success

KEY_A = "LibreFolio-plugin-readiness-test-key-A-0123456789"
KEY_B = "LibreFolio-plugin-readiness-test-key-B-9876543210"
SYSTEM, USER = SettingScope.SYSTEM, SettingScope.USER
STRING, SELECT = SettingType.STRING, SettingType.SELECT
GROUP = "n1_grp"
GROUP_TOKEN_VARIABLE = "LIBREFOLIO_PLUGIN_GROUP_N1_GRP_TOKEN"
GROUP_TIER_VARIABLE = "LIBREFOLIO_PLUGIN_GROUP_N1_GRP_TIER"

KEY_FIELD = PluginSettingField(key="api_key", type=STRING, scope=SYSTEM, label="API key (n1)", secret=True, required=True)
ENDPOINT_FIELD = PluginSettingField(key="endpoint", type=STRING, scope=SYSTEM, label="Endpoint (n1)", required=True)
REGION_FIELD = PluginSettingField(key="region", type=SELECT, scope=SYSTEM, label="Region (n1)", default="eu", options=(SettingOption("eu", "EU"), SettingOption("us", "US")))
HANDLE_FIELD = PluginSettingField(key="handle", type=STRING, scope=USER, label="Handle (n1)", required=True)


class _AssetLab(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_readiness_lab_assets"

    @classmethod
    def settings_family(cls) -> str:
        return "asset"


class _FxLab(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_readiness_lab_fx"

    @classmethod
    def settings_family(cls) -> str:
        return "fx"


def _plugin(code: str, fields: tuple[PluginSettingField, ...] = (), groups: tuple[str, ...] = ()) -> type:
    return type(f"N1Plugin_{code}", (PluginSettingsMixin,), {"provider_code": code, "provider_name": f"Plugin {code}", "settings_fields": fields, "settings_groups": groups})


def _register_group() -> None:
    """The group of this module: ``token`` a required secret, ``tier`` a select with a default."""
    tier = PluginSettingField(key="tier", type=SELECT, scope=SYSTEM, label="Tier (n1)", default="free", options=(SettingOption("free", "Free"), SettingOption("paid", "Paid")))
    token = PluginSettingField(key="token", type=STRING, scope=SYSTEM, label="Token (n1)", secret=True, required=True)
    register_group(SettingsGroup(name=GROUP, label="Group n1", fields=(token, tier)))


# =============================================================================
# FIXTURES AND ROWS
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Key A, a data directory of this test, the self-hosted profile, no ambient variable of the group; no group left behind."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    for variable in (GROUP_TOKEN_VARIABLE, GROUP_TIER_VARIABLE):
        monkeypatch.delenv(variable, raising=False)
        monkeypatch.delenv(variable + "_FILE", raising=False)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    yield
    for name in [name for name in all_groups() if name.startswith("n1")]:
        release_group(name)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'readiness.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield private
    finally:
        await private.dispose()


@pytest_asyncio.fixture
async def people(engine: AsyncEngine) -> dict[str, User]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        created = {name: User(username=name, email=f"{name}@example.test", hashed_password="$argon2id$test") for name in ("alice", "bob")}
        session.add_all(created.values())
        await session.commit()
    return created


@pytest.fixture
def engine_calls(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The runtime (and the readiness module, when it has its own name) get the private engine; every ask is counted."""
    calls: list[int] = []

    def private_engine() -> AsyncEngine:
        calls.append(1)
        return engine

    monkeypatch.setattr(runtime, "get_async_engine", private_engine)
    try:
        from backend.app.services.plugin_settings import readiness

        monkeypatch.setattr(readiness, "get_async_engine", private_engine, raising=False)
    except ImportError:  # red on HEAD
        pass
    return calls


@pytest.fixture
def lab(monkeypatch: pytest.MonkeyPatch, engine_calls: list[int]) -> Callable[..., None]:
    """The service reads the asset and FX families from two throwaway registries; ``add(family, plugin_class)`` fills them."""
    stores: dict[str, dict[str, type]] = {"asset": {}, "fx": {}}
    for family, registry in (("asset", _AssetLab), ("fx", _FxLab)):
        monkeypatch.setattr(registry, "_providers", stores[family])
        monkeypatch.setattr(registry, "_discovery_done", True)
        monkeypatch.setitem(service.FAMILY_REGISTRIES, family, registry)

    def add(family: str, plugin_class: type) -> None:
        stores[family][plugin_class.provider_code] = plugin_class

    return add


def _secret_row(family: str, code: str, key: str, value: str, *, user_id: int | None = None) -> PluginSystemSetting | PluginUserSetting:
    subkey = settings_subkey()
    scope = "user" if user_id is not None else "system"
    blob = encrypt_secret(subkey, secret_aad(family, code, key, scope, user_id), value)
    common = {"family": family, "plugin_code": code, "field_key": key, "secret_ciphertext": blob, "key_id": key_id_of(subkey)}
    return PluginUserSetting(user_id=user_id, **common) if user_id is not None else PluginSystemSetting(**common)


def _plain_row(family: str, code: str, key: str, value: Any, *, user_id: int | None = None) -> PluginSystemSetting | PluginUserSetting:
    common = {"family": family, "plugin_code": code, "field_key": key, "value_json": json.dumps(value)}
    return PluginUserSetting(user_id=user_id, **common) if user_id is not None else PluginSystemSetting(**common)


async def _store(engine: AsyncEngine, *rows: Any) -> None:
    async with AsyncSession(engine) as session:
        session.add_all(rows)
        await session.commit()


@dataclass
class _Ctx:
    """What a scenario's setup works with."""

    engine: AsyncEngine
    mp: pytest.MonkeyPatch
    people: dict[str, User]
    code: str


async def _noop(ctx: _Ctx) -> int | None:
    return None


async def _key_row(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _secret_row("asset", ctx.code, "api_key", "a-secret-value"))
    return None


async def _key_env(ctx: _Ctx) -> int | None:
    ctx.mp.setenv(env_name("asset", ctx.code, "api_key"), "a-secret-value")
    return None


async def _region_invalid_env(ctx: _Ctx) -> int | None:
    ctx.mp.setenv(env_name("asset", ctx.code, "region"), "zz")
    return None


async def _key_row_then_other_instance_key(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _secret_row("asset", ctx.code, "api_key", "a-secret-value"))
    ctx.mp.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)
    return None


async def _group_token_row(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _secret_row("group", GROUP, "token", "a-group-token"))
    return None


async def _group_token_env(ctx: _Ctx) -> int | None:
    ctx.mp.setenv(GROUP_TOKEN_VARIABLE, "a-group-token")
    return None


async def _endpoint_row_only(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _plain_row("asset", ctx.code, "endpoint", "https://example.test"))
    return None


async def _group_token_row_and_tier_invalid_env(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _secret_row("group", GROUP, "token", "a-group-token"))
    ctx.mp.setenv(GROUP_TIER_VARIABLE, "zz")
    return None


async def _handle_row_of_alice(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _plain_row("asset", ctx.code, "handle", "ali", user_id=ctx.people["alice"].id))
    return ctx.people["alice"].id


async def _handle_row_of_bob_caller_alice(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _plain_row("asset", ctx.code, "handle", "bob", user_id=ctx.people["bob"].id))
    return ctx.people["alice"].id


async def _handle_row_of_alice_no_caller(ctx: _Ctx) -> int | None:
    await _store(ctx.engine, _plain_row("asset", ctx.code, "handle", "ali", user_id=ctx.people["alice"].id))
    return None


# (id, fields, groups, setup, expected missing on the boundary)
_SCENARIOS = [
    pytest.param((KEY_FIELD,), (), _noop, ("api_key",), id="required-unset"),
    pytest.param((KEY_FIELD,), (), _key_row, (), id="required-set-by-a-row"),
    pytest.param((KEY_FIELD,), (), _key_env, (), id="required-set-by-the-variable"),
    pytest.param((REGION_FIELD,), (), _region_invalid_env, ("region",), id="optional-field-invalid-variable"),
    pytest.param((KEY_FIELD,), (), _key_row_then_other_instance_key, ("api_key",), id="secret-the-current-key-cannot-read"),
    pytest.param((), (GROUP,), _noop, (f"{GROUP}.token",), id="group-only-unset"),
    pytest.param((), (GROUP,), _group_token_row, (), id="group-only-set-by-a-row"),
    pytest.param((), (GROUP,), _group_token_env, (), id="group-only-set-by-the-variable"),
    pytest.param((), (GROUP,), _group_token_row_and_tier_invalid_env, (f"{GROUP}.tier",), id="group-field-invalid-variable"),
    pytest.param((ENDPOINT_FIELD,), (GROUP,), _noop, ("endpoint", f"{GROUP}.token"), id="own-and-group-unset-own-first"),
    pytest.param((ENDPOINT_FIELD,), (GROUP,), _endpoint_row_only, (f"{GROUP}.token",), id="own-set-group-unset"),
    pytest.param((HANDLE_FIELD,), (), _handle_row_of_alice, (), id="user-field-row-of-the-caller"),
    pytest.param((HANDLE_FIELD,), (), _handle_row_of_bob_caller_alice, ("handle",), id="user-field-row-of-another-user"),
    pytest.param((HANDLE_FIELD,), (), _handle_row_of_alice_no_caller, ("handle",), id="user-field-no-caller"),
    pytest.param((), (), _noop, (), id="no-field-no-group"),
]


# =============================================================================
# 1. THE RULE OF THE BOUNDARY
# =============================================================================


@pytest.mark.parametrize(("fields", "groups", "setup", "expected_missing"), _SCENARIOS)
@pytest.mark.asyncio
async def test_n1_configured_is_the_rule_of_the_call_boundary(fields, groups, setup, expected_missing, engine, people, lab, monkeypatch):
    """1: on one state, ``configured`` equals «the boundary's ``settings.missing`` is empty» and ``missing`` its keys."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugin_readiness, plugins_readiness

    print_section("N1 1: readiness against the boundary")
    _register_group()
    code = "n1_scenario"
    lab("asset", _plugin(code, fields, groups))
    user_id = await setup(_Ctx(engine, monkeypatch, people, code))

    instance = service.FAMILY_REGISTRIES["asset"].get_plugin(code)()
    await runtime.configure_instance(instance, "asset", user_id=user_id, plugin_code=code)
    boundary_missing = tuple(instance.settings.missing)
    assert boundary_missing == expected_missing, "barrier: the scenario builds the state it names"

    batch = await plugins_readiness("asset", [code], user_id=user_id)
    single = await plugin_readiness("asset", code, user_id=user_id)

    assert batch == {code: PluginReadiness(configured=not boundary_missing, missing=boundary_missing)}
    assert single == batch[code]
    assert isinstance(batch[code].missing, tuple)
    print_success(f"{code}: configured={batch[code].configured} missing={batch[code].missing}")


@pytest.mark.asyncio
async def test_n1_the_same_rule_holds_for_the_fx_family(engine, lab, monkeypatch):
    """1: the family is a parameter: an FX plugin with a required key, unset then set, answers like the boundary."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness

    lab("fx", _plugin("N1FX", (KEY_FIELD,)))

    assert await plugins_readiness("fx", ["N1FX"], user_id=None) == {"N1FX": PluginReadiness(False, ("api_key",))}
    await _store(engine, _secret_row("fx", "N1FX", "api_key", "a-secret-value"))
    assert await plugins_readiness("fx", ["N1FX"], user_id=None) == {"N1FX": PluginReadiness(True, ())}


class _EnricherLab(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_readiness_lab_enrichers"

    @classmethod
    def settings_family(cls) -> str:
        return "enricher"


@pytest.mark.asyncio
async def test_n1_the_same_rule_holds_for_the_enricher_family(engine, engine_calls, monkeypatch):
    """1: the enricher family (lane 68's B2 reads it) answers like its boundary: own key and group, unset then set."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness

    _register_group()
    store: dict[str, type] = {}
    monkeypatch.setattr(_EnricherLab, "_providers", store)
    monkeypatch.setattr(_EnricherLab, "_discovery_done", True)
    monkeypatch.setitem(service.FAMILY_REGISTRIES, "enricher", _EnricherLab)
    store["n1_enricher"] = _plugin("n1_enricher", (KEY_FIELD,), (GROUP,))

    async def boundary() -> tuple[str, ...]:
        instance = store["n1_enricher"]()
        await runtime.configure_instance(instance, "enricher", plugin_code="n1_enricher")
        return tuple(instance.settings.missing)

    assert await boundary() == ("api_key", f"{GROUP}.token"), "barrier: nothing set"
    assert await plugins_readiness("enricher", ["n1_enricher"], user_id=None) == {"n1_enricher": PluginReadiness(False, ("api_key", f"{GROUP}.token"))}
    await _store(engine, _secret_row("enricher", "n1_enricher", "api_key", "a-secret-value"), _secret_row("group", GROUP, "token", "a-group-token"))
    assert await boundary() == (), "barrier: both set"
    assert await plugins_readiness("enricher", ["n1_enricher"], user_id=None) == {"n1_enricher": PluginReadiness(True, ())}


@pytest.mark.asyncio
async def test_n1_a_database_error_reads_like_the_boundary(tmp_path, lab, monkeypatch):
    """1: when the rows cannot be read, the check falls back as the boundary does (the environment and the defaults only):
    a key set by its variable is configured, a key only a row could give is missing. Same answer as a call, never an error."""
    from backend.app.services.plugin_settings import readiness
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness

    broken = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'no-such-dir' / 'x.db'}", poolclass=NullPool)
    monkeypatch.setattr(runtime, "get_async_engine", lambda: broken)
    monkeypatch.setattr(readiness, "get_async_engine", lambda: broken)
    lab("asset", _plugin("n1_rowkey", (KEY_FIELD,)))
    lab("asset", _plugin("n1_envkey", (KEY_FIELD,)))
    monkeypatch.setenv(env_name("asset", "n1_envkey", "api_key"), "a-key-from-the-environment")
    try:
        answers = await plugins_readiness("asset", ["n1_rowkey", "n1_envkey"], user_id=None)
        for code in ("n1_rowkey", "n1_envkey"):
            instance = service.FAMILY_REGISTRIES["asset"].get_plugin(code)()
            await runtime.configure_instance(instance, "asset", plugin_code=code)
            assert answers[code] == PluginReadiness(not instance.settings.missing, tuple(instance.settings.missing))
        assert answers == {"n1_rowkey": PluginReadiness(False, ("api_key",)), "n1_envkey": PluginReadiness(True, ())}
    finally:
        await broken.dispose()


def test_n1_plugin_readiness_is_a_frozen_value():
    """1: ``PluginReadiness(configured, missing)``, compared by value, cannot be changed."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness

    ready = PluginReadiness(True, ())

    assert ready == PluginReadiness(configured=True, missing=()) and ready != PluginReadiness(False, ("api_key",))
    assert [field.name for field in dataclasses.fields(PluginReadiness)] == ["configured", "missing"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        ready.configured = False  # type: ignore[misc]


# =============================================================================
# 1b. THE BATCH
# =============================================================================


@pytest.mark.asyncio
async def test_n1_one_entry_per_code_asked_and_unknown_or_fieldless_codes_are_ready(engine, lab):
    """1: every code asked is answered, nothing else; an unknown code and a plugin with no field and no group are ready."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness

    _register_group()
    lab("asset", _plugin("n1_needs", (KEY_FIELD,)))
    lab("asset", _plugin("n1_plain"))
    lab("asset", _plugin("n1_grouped", (), (GROUP,)))
    lab("asset", _plugin("n1_not_asked", (KEY_FIELD,)))
    asked = ["n1_needs", "n1_plain", "n1_grouped", "n1_unknown"]

    answer = await plugins_readiness("asset", asked, user_id=None)

    assert set(answer) == set(asked)
    assert answer["n1_needs"] == PluginReadiness(False, ("api_key",))
    assert answer["n1_grouped"] == PluginReadiness(False, (f"{GROUP}.token",))
    assert answer["n1_plain"] == PluginReadiness(True, ())
    assert answer["n1_unknown"] == PluginReadiness(True, ())
    assert await plugins_readiness("asset", [], user_id=None) == {}


@pytest.mark.asyncio
async def test_n1_the_batch_reads_the_database_in_one_session(engine, people, lab, engine_calls):
    """2: three plugins (own fields, a group, a user field) are judged with ONE ask for the engine, not one per plugin."""
    from backend.app.services.plugin_settings.readiness import plugins_readiness

    _register_group()
    lab("asset", _plugin("n1_a", (KEY_FIELD,)))
    lab("asset", _plugin("n1_b", (), (GROUP,)))
    lab("asset", _plugin("n1_c", (HANDLE_FIELD,)))
    engine_calls.clear()

    await plugins_readiness("asset", ["n1_a", "n1_b", "n1_c"], user_id=people["alice"].id)

    assert len(engine_calls) == 1, f"the engine was asked {len(engine_calls)} times"


@pytest.mark.asyncio
async def test_n1_a_stored_secret_is_judged_by_its_key_id_and_never_decrypted(engine, lab, monkeypatch):
    """2: a stored secret counts as set without decrypting it; one the current key cannot read, as not set."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness

    lab("asset", _plugin("n1_secret", (KEY_FIELD,)))
    await _store(engine, _secret_row("asset", "n1_secret", "api_key", "a-secret-value"))

    def refuse(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("readiness decrypted a secret")

    monkeypatch.setattr(resolver, "decrypt_secret", refuse)

    assert await plugins_readiness("asset", ["n1_secret"], user_id=None) == {"n1_secret": PluginReadiness(True, ())}
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)
    assert await plugins_readiness("asset", ["n1_secret"], user_id=None) == {"n1_secret": PluginReadiness(False, ("api_key",))}


@pytest.mark.asyncio
async def test_n1_a_plugin_with_no_field_and_no_group_needs_no_database(engine, lab, engine_calls):
    """1: a plugin that declares nothing is ready without reading anything, as the boundary lets it through."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness

    lab("asset", _plugin("n1_plain"))
    engine_calls.clear()

    assert await plugins_readiness("asset", ["n1_plain", "n1_unknown"], user_id=None) == {"n1_plain": PluginReadiness(True, ()), "n1_unknown": PluginReadiness(True, ())}
    assert engine_calls == []


# =============================================================================
# 3. THE MANAGED PROFILE
# =============================================================================


async def _managed_key_env(ctx: _Ctx) -> None:
    ctx.mp.setenv(env_name("asset", ctx.code, "api_key"), "a-secret-value")


async def _managed_region_invalid(ctx: _Ctx) -> None:
    ctx.mp.setenv(env_name("asset", ctx.code, "region"), "zz")


async def _managed_group_token_env(ctx: _Ctx) -> None:
    ctx.mp.setenv(GROUP_TOKEN_VARIABLE, "a-group-token")


async def _managed_own_unset_group_locked(ctx: _Ctx) -> None:
    ctx.mp.setenv(GROUP_TOKEN_VARIABLE, "a-group-token")


async def _managed_group_field_invalid(ctx: _Ctx) -> None:
    await _store(ctx.engine, _secret_row("group", GROUP, "token", "a-group-token"))
    ctx.mp.setenv(GROUP_TIER_VARIABLE, "zz")


# (fields, groups, setup, configured, missing)
_MANAGED = [
    pytest.param((KEY_FIELD,), (), _managed_key_env, True, (), id="locked-valid-field-is-hidden-and-counted"),
    pytest.param((REGION_FIELD,), (), _managed_region_invalid, False, (), id="locked-invalid-field-unconfigures-without-a-name"),
    pytest.param((), (GROUP,), _managed_group_token_env, True, (), id="locked-group-field-is-hidden-and-counted"),
    pytest.param((ENDPOINT_FIELD,), (GROUP,), _managed_own_unset_group_locked, False, ("endpoint",), id="an-unlocked-field-is-still-named"),
    pytest.param((), (GROUP,), _managed_group_field_invalid, False, (), id="locked-invalid-group-field-unconfigures-without-a-name"),
]


@pytest.mark.parametrize(("fields", "groups", "setup", "configured", "missing"), _MANAGED)
@pytest.mark.asyncio
async def test_n1_in_the_managed_profile_a_locked_field_counts_but_is_not_named(fields, groups, setup, configured, missing, engine, people, lab, monkeypatch):
    """3 (decision N2): ``configured`` is the boundary's; ``missing`` leaves out the fields a variable locks."""
    from backend.app.services.plugin_settings.readiness import PluginReadiness, plugins_readiness

    print_section("N1 3: managed profile")
    _register_group()
    code = "n1_managed"
    lab("asset", _plugin(code, fields, groups))
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    assert service._is_managed(), "barrier: the service reads the managed profile"
    await setup(_Ctx(engine, monkeypatch, people, code))

    instance = service.FAMILY_REGISTRIES["asset"].get_plugin(code)()
    await runtime.configure_instance(instance, "asset", user_id=None, plugin_code=code)
    assert (not instance.settings.missing) is configured, "barrier: the boundary agrees on whether it is configured"

    assert await plugins_readiness("asset", [code], user_id=None) == {code: PluginReadiness(configured, missing)}
    print_success(f"managed {code}: configured={configured} missing={missing}")


# =============================================================================
# 4. THE SCHEMAS
# =============================================================================


def test_n1_the_provider_schemas_default_to_configured():
    """4: ``configured`` True and ``missing_settings`` [] when nobody says otherwise; each instance its own list."""
    from backend.app.schemas.fx import FXProviderInfo
    from backend.app.schemas.provider import FAProviderInfo

    for model in (FAProviderInfo, FXProviderInfo):
        assert model.model_fields["configured"].default is True and model.model_fields["configured"].annotation is bool
        assert model.model_fields["missing_settings"].annotation == list[str]
        assert not model.model_fields["missing_settings"].is_required() and not model.model_fields["configured"].is_required()

    fx = FXProviderInfo(code="N1FX", name="n1", base_currency="EUR", base_currencies=["EUR"], description="d")
    fa = FAProviderInfo(code="n1", name="n1", description="d", supports_search=False)
    assert (fx.configured, fx.missing_settings, fa.configured, fa.missing_settings) == (True, [], True, [])
    other = FXProviderInfo(code="N1FX", name="n1", base_currency="EUR", base_currencies=["EUR"], description="d", configured=False, missing_settings=["api_key"])
    assert (other.configured, other.missing_settings, fx.missing_settings) == (False, ["api_key"], [])


# =============================================================================
# 5. THE PROVIDER LISTS
# =============================================================================


class _ReadinessSpy:
    """Wraps ``plugins_readiness`` wherever the routes may hold it, and records each call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str], int | None]] = []


@pytest.fixture
def readiness_spy(monkeypatch: pytest.MonkeyPatch) -> _ReadinessSpy:
    spy = _ReadinessSpy()
    try:
        from backend.app.api.v1.assets import providers as asset_routes
        from backend.app.api.v1.fx import providers as fx_routes
        from backend.app.services.plugin_settings import readiness
    except ImportError:  # red on HEAD
        return spy
    original = readiness.plugins_readiness

    async def recording(family: str, codes: Any, *, user_id: int | None):
        spy.calls.append((family, list(codes), user_id))
        return await original(family, codes, user_id=user_id)

    monkeypatch.setattr(readiness, "plugins_readiness", recording)
    for module in (asset_routes, fx_routes):
        monkeypatch.setattr(module, "plugins_readiness", recording, raising=False)
    return spy


def _asset_plugin(code: str, fields: tuple = (), groups: tuple = ()) -> type:
    """A listed (not test-only) asset provider: the mock, under another code and with the settings of the test."""
    return type(f"N1Asset_{code}", (MockProvider,), {"provider_code": property(lambda self: code), "provider_name": f"N1 {code}", "test_only": False, "settings_fields": fields, "settings_groups": groups})


def _fx_plugin(code: str, fields: tuple = ()) -> type:
    return type(f"N1Fx_{code}", (MockFXProvider,), {"code": property(lambda self: code), "name": property(lambda self: f"N1 {code}"), "test_only": False, "settings_fields": fields})


@pytest.mark.asyncio
async def test_n1_the_asset_provider_list_says_what_each_provider_lacks(engine, people, engine_calls, readiness_spy, monkeypatch):
    """5: ``GET /assets/provider`` lists ``configured``/``missing_settings`` for the caller with ONE readiness call."""
    from backend.app.api.v1.assets.providers import list_providers

    print_section("N1 5: GET /assets/provider")
    _register_group()
    AssetProviderRegistry.auto_discover()
    storage = AssetProviderRegistry._get_storage()
    for code, plugin_class in (("n1_needskey", _asset_plugin("n1_needskey", (KEY_FIELD,))), ("n1_plain", _asset_plugin("n1_plain")), ("n1_grouped", _asset_plugin("n1_grouped", (), (GROUP,)))):
        monkeypatch.setitem(storage, AssetProviderRegistry._normalize_lookup_code(code), plugin_class)
    caller = people["alice"]

    async def listed() -> dict[str, Any]:
        readiness_spy.calls.clear()
        answer = await list_providers(providers="n1_needskey,n1_plain,n1_grouped", _current_user=caller)
        return {item.code: item for item in answer}

    before = await listed()
    assert set(before) == {"n1_needskey", "n1_plain", "n1_grouped"}
    assert (before["n1_needskey"].configured, before["n1_needskey"].missing_settings) == (False, ["api_key"])
    assert (before["n1_grouped"].configured, before["n1_grouped"].missing_settings) == (False, [f"{GROUP}.token"])
    assert (before["n1_plain"].configured, before["n1_plain"].missing_settings) == (True, [])
    assert len(readiness_spy.calls) == 1, f"one readiness call per request, got {len(readiness_spy.calls)}"
    family, codes, user_id = readiness_spy.calls[0]
    assert family == "asset" and user_id == caller.id and {"n1_needskey", "n1_plain", "n1_grouped"} <= set(codes)

    await _store(engine, _secret_row("asset", "n1_needskey", "api_key", "a-secret-value"), _secret_row("group", GROUP, "token", "a-group-token"))
    after = await listed()
    assert all((item.configured, item.missing_settings) == (True, []) for item in after.values())
    assert len(readiness_spy.calls) == 1
    print_success("asset list: false/[api_key] then true/[]")


@pytest.mark.asyncio
async def test_n1_the_fx_provider_list_says_what_each_provider_lacks(engine, people, engine_calls, readiness_spy, monkeypatch):
    """5: ``GET /fx/providers`` lists ``configured``/``missing_settings`` for the caller with ONE readiness call."""
    from backend.app.api.v1.fx.providers import list_providers

    print_section("N1 5: GET /fx/providers")
    FXProviderRegistry.auto_discover()
    storage = FXProviderRegistry._get_storage()
    for code, plugin_class in (("N1FXKEY", _fx_plugin("N1FXKEY", (KEY_FIELD,))), ("N1FXPLAIN", _fx_plugin("N1FXPLAIN"))):
        monkeypatch.setitem(storage, FXProviderRegistry._normalize_lookup_code(code), plugin_class)
    caller = people["bob"]

    async def listed() -> dict[str, Any]:
        readiness_spy.calls.clear()
        answer = await list_providers(providers=["N1FXKEY", "N1FXPLAIN"], _current_user=caller)
        return {item.code: item for item in answer}

    before = await listed()
    assert set(before) == {"N1FXKEY", "N1FXPLAIN"}
    assert (before["N1FXKEY"].configured, before["N1FXKEY"].missing_settings) == (False, ["api_key"])
    assert (before["N1FXPLAIN"].configured, before["N1FXPLAIN"].missing_settings) == (True, [])
    assert len(readiness_spy.calls) == 1, f"one readiness call per request, got {len(readiness_spy.calls)}"
    family, codes, user_id = readiness_spy.calls[0]
    assert family == "fx" and user_id == caller.id and {"N1FXKEY", "N1FXPLAIN"} <= set(codes)

    await _store(engine, _secret_row("fx", "N1FXKEY", "api_key", "a-secret-value"))
    after = await listed()
    assert (after["N1FXKEY"].configured, after["N1FXKEY"].missing_settings) == (True, [])
    assert (after["N1FXPLAIN"].configured, after["N1FXPLAIN"].missing_settings) == (True, [])
    assert len(readiness_spy.calls) == 1
    print_success("fx list: false/[api_key] then true/[]")
