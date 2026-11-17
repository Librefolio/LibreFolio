# ruff: noqa: PLC0415 — the new names are imported inside each test on purpose: red on HEAD, every test fails for its own reason
"""Plugin settings, shared groups: one set of fields several plugins read (project 76, lot G1).

Modules under test: ``services/plugin_settings/groups/`` (new), ``contract.py`` (``settings_groups``, the groups in
``BoundSettings``), ``runtime.py`` (``configure_instance``, ``bound_settings_for``), the registries
(``provider_registry.py``) and the asset boundary ``services/assets/core.call_provider``. The contract pinned here:

1. **A group is declared once** (``register_group(SettingsGroup(...))``): its name is a field key (``FIELD_KEY``), its fields
   pass ``validate_declaration(family="group")`` (``FAMILY_RULES["group"]`` = no user scope, secrets allowed), so a
   ``user`` field, a secret with a default, a bad key, a repeated key are refused with ``SettingsDeclarationError``
   and nothing is stored or claimed. Its variables are claimed as ``("group", name)`` and derived as
   ``LIBREFOLIO_PLUGIN_GROUP_<NAME>_<FIELD>``; a variable another owner holds (a plugin's alias) refuses it, in both
   directions. Registering the name again replaces the group; ``release_group`` drops it and its claims;
   ``get_group`` answers ``None`` for an unknown name, ``all_groups`` is a copy.
2. **A plugin names its groups** in ``PluginSettingsMixin.settings_groups`` (a tuple of names, empty by default);
   ``validate_plugin_groups(plugin_class, family=…)`` refuses a value that is not a tuple of ``str`` (the string
   ``"g"``), an unknown name, a name twice, a group field whose key is one of the plugin's own, and a group with a secret
   for a family whose rules forbid secrets (``tool``). The registries call it at registration: the plugin is not stored.
3. **``BoundSettings`` carries the groups' values**: ``group(name)`` is the group's own ``BoundSettings`` (``KeyError`` for
   a group the plugin does not declare); ``missing`` is the plugin's own missing keys then ``"<group>.<key>"`` for each group
   field left without a usable value (required and empty, or its variable invalid); ``secret_values()`` includes the
   groups' secrets; the ``fingerprint`` of a plugin without groups is byte-identical to today's
   (``settings_fingerprint(plain, secrets)``), with groups it follows the group values; an instance nobody configured
   gives each group its defaults and its required fields in ``missing``; a ``BoundSettings`` with groups pickles (the BRIM
   worker gets it by pickle).
4. **Binding** (``configure_instance``, ``bound_settings_for``): a plugin that declares groups gets them bound even with no
   field of its own. Field by field: the group's variable (locks), then the instance's row of ``plugin_system_settings``
   with ``family="group"`` and ``plugin_code=<group>`` (a secret encrypted with ``secret_aad("group", name, key, "system",
   None)``), then the default. A user's row, or a row of another family under the group's name, never applies.
5. **The asset boundary** (``call_provider``) refuses a provider whose group lacks a required value:
   ``AssetSourceError`` ``NOT_CONFIGURED`` with ``details["missing"] == ["<group>.<key>"]``, ``fn`` not called; a group secret
   in an error the provider raises is masked, as the plugin's own.
6. **Gate**: every registered plugin of every settings family names registered groups only, and every registered group
   that is not ``test_only`` is used by one plugin at least (vacuous while no group ships).

Red on HEAD 09d502083: the ``groups`` package, ``settings_groups`` and ``BoundSettings.group`` do not exist yet. Every test
imports the new names inside its body, so each one fails for its own reason.

Pure: a private SQLite file under ``tmp_path`` reached through a private engine in place of ``runtime.get_async_engine``,
a test instance key, a data directory in ``tmp_path``; every variable through ``monkeypatch``. Every group and plugin
code of this module starts with ``g1_``: the teardown releases every group and every claim of those names.
"""

from __future__ import annotations

import json
import pickle
import uuid
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.services.assets import core as asset_core
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.platform.provider_registry import AbstractProviderRegistry
from backend.app.services.plugin_settings import runtime
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import (
    FAMILY_RULES,
    PluginSettingField,
    SettingOption,
    SettingScope,
    SettingsDeclarationError,
    SettingType,
    claim_env_variables,
    claimed_env_variables,
    env_name,
    release_env_variables,
)
from backend.app.services.plugin_settings.resolver import settings_fingerprint
from backend.app.services.plugin_settings.service import FAMILY_REGISTRIES
from backend.app.utils.runtime.secret_masking import MASK, active_secrets
from backend.test_scripts.test_utils import print_section, print_success

KEY_A = "LibreFolio-plugin-settings-test-key-A-0123456789"
SYSTEM, USER = SettingScope.SYSTEM, SettingScope.USER
STRING, SELECT = SettingType.STRING, SettingType.SELECT
PREFIX = "g1_"
GROUP = "g1_a"
API_KEY_VARIABLE = "LIBREFOLIO_PLUGIN_GROUP_G1_A_API_KEY"
REGION_VARIABLE = "LIBREFOLIO_PLUGIN_GROUP_G1_A_REGION"


def _marker(prefix: str = "lfgroupsecret") -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}"


def _api_key(**extra) -> PluginSettingField:
    return PluginSettingField(key="api_key", type=STRING, scope=SYSTEM, label="API key", secret=True, required=True, **extra)


def _region(**extra) -> PluginSettingField:
    return PluginSettingField(key="region", type=SELECT, scope=SYSTEM, label="Region", default="eu", options=tuple(SettingOption(v, v.upper()) for v in ("eu", "us", "jp")), **extra)


def _own(key: str, **extra) -> PluginSettingField:
    return PluginSettingField(key=key, type=STRING, scope=SYSTEM, label=key, **extra)


def _group(name: str = GROUP, fields: tuple | None = None, **extra):
    """Register (and return) a group of this module: ``api_key`` secret required, ``region`` select with a default."""
    from backend.app.services.plugin_settings.groups import SettingsGroup, register_group

    group = SettingsGroup(name=name, label=f"Group {name}", fields=(_api_key(), _region()) if fields is None else fields, **extra)
    register_group(group)
    return group


def _plugin(code: str, groups: tuple | str | list = (GROUP,), fields: tuple = ()) -> type:
    return type(f"G1Plugin_{code}", (PluginSettingsMixin,), {"provider_code": code, "settings_groups": groups, "settings_fields": fields})


class _GroupLabRegistry(AbstractProviderRegistry):
    """A throwaway registry of the asset family: its own storage, a folder that does not exist."""

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_settings_groups_lab_assets"

    @classmethod
    def settings_family(cls) -> str:
        return "asset"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Test key A, a data directory of this test, and no group or claim of this module left behind, however the test ended."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    yield
    try:
        from backend.app.services.plugin_settings.groups import all_groups, release_group

        for name in [name for name in all_groups() if name.startswith(PREFIX)]:
            release_group(name)
    except ImportError:  # red on HEAD: nothing was registered
        pass
    for family, code in {owner for owner in claimed_env_variables().values() if owner[1].startswith(PREFIX)}:
        release_env_variables(family, code)


@pytest_asyncio.fixture
async def private_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'groups.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def through_private_engine(private_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> AsyncEngine:
    monkeypatch.setattr(runtime, "get_async_engine", lambda: private_engine)
    return private_engine


def _system_row(code: str, key: str, *, value: object = None, secret: str | None = None, family: str = "group") -> PluginSystemSetting:
    if secret is None:
        return PluginSystemSetting(family=family, plugin_code=code, field_key=key, value_json=json.dumps(value))
    subkey = settings_subkey()
    blob = encrypt_secret(subkey, secret_aad(family, code, key, "system", None), secret)
    return PluginSystemSetting(family=family, plugin_code=code, field_key=key, secret_ciphertext=blob, key_id=key_id_of(subkey))


async def _store(engine: AsyncEngine, *rows) -> None:
    async with AsyncSession(engine) as session:
        session.add_all(rows)
        await session.commit()


async def _configured(plugin_class: type, code: str, *, user_id: int | None = None):
    instance = plugin_class()
    await runtime.configure_instance(instance, "asset", user_id=user_id, plugin_code=code)
    return instance


# =============================================================================
# 1. DECLARING AND REGISTERING A GROUP
# =============================================================================


def test_g1_family_rules_of_a_group_are_the_instances_with_secrets():
    """1: ``FAMILY_RULES["group"]`` has no user scope and allows secrets; the group modules import no registry."""
    from backend.app.services.plugin_settings.fields import FamilyRules
    from backend.app.services.plugin_settings.groups import GROUP_FAMILY

    assert GROUP_FAMILY == "group"
    assert FAMILY_RULES["group"] == FamilyRules(user_scope=False, secrets=True)


def test_g1_a_settings_group_is_a_frozen_value_with_defaults():
    """1: only ``name`` and ``label`` are required; ``test_only`` is off; the value cannot be changed."""
    import dataclasses

    from backend.app.services.plugin_settings.groups import SettingsGroup

    group = SettingsGroup(name="g1_plain", label="Plain")

    assert (group.description, group.fields, group.label_key, group.description_key, group.test_only) == ("", (), None, None, False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        group.label = "other"  # type: ignore[misc]


def test_g1_a_registered_group_is_found_and_claims_its_derived_variables():
    """1: ``LIBREFOLIO_PLUGIN_GROUP_<NAME>_<FIELD>`` for each system field, owned by ``("group", name)``."""
    from backend.app.services.plugin_settings.groups import all_groups, get_group

    group = _group()

    assert get_group(GROUP) is group and get_group("g1_unknown") is None
    assert all_groups()[GROUP] is group
    assert env_name("group", GROUP, "api_key") == API_KEY_VARIABLE
    claims = claimed_env_variables()
    assert claims[API_KEY_VARIABLE] == ("group", GROUP) and claims[REGION_VARIABLE] == ("group", GROUP)


def test_g1_all_groups_is_a_copy():
    from backend.app.services.plugin_settings.groups import all_groups, get_group

    _group()
    snapshot = all_groups()
    snapshot.clear()

    assert get_group(GROUP) is not None and GROUP in all_groups()


def test_g1_registering_a_name_again_replaces_the_group_and_its_claims():
    """1: the second declaration stands; a variable only the first one had is no longer claimed."""
    from backend.app.services.plugin_settings.groups import get_group

    _group(fields=(_api_key(), _region()))
    second = _group(fields=(_api_key(),))

    assert get_group(GROUP) is second
    assert API_KEY_VARIABLE in claimed_env_variables() and REGION_VARIABLE not in claimed_env_variables()


def test_g1_release_group_drops_the_group_and_its_claims():
    from backend.app.services.plugin_settings.groups import get_group, release_group

    _group()
    release_group(GROUP)
    release_group(GROUP)  # a second release changes nothing

    assert get_group(GROUP) is None
    assert API_KEY_VARIABLE not in claimed_env_variables() and REGION_VARIABLE not in claimed_env_variables()


@pytest.mark.parametrize(
    ("name", "fields", "rule"),
    [
        pytest.param("Bad-Name", (_region(),), "", id="name-not-a-field-key"),
        pytest.param("", (_region(),), "", id="empty-name"),
        pytest.param("g1_" + "x" * 70, (_region(),), "", id="name-too-long"),
        pytest.param("g1_user", (PluginSettingField(key="limit", type=SettingType.INTEGER, scope=USER, label="Limit", default=1),), "'limit'", id="user-field"),
        pytest.param("g1_secdef", (PluginSettingField(key="api_key", type=STRING, scope=SYSTEM, label="Key", secret=True, default="a-default-secret"),), "a secret has no default", id="secret-with-default"),
        pytest.param("g1_twice", (_region(), _region()), "declared twice", id="field-twice"),
        pytest.param("g1_file", (_own("token_file"),), "_file", id="field-key-ends-in-file"),
        pytest.param("g1_list", [_region()], "tuple", id="fields-not-a-tuple"),
    ],
)
def test_g1_register_group_refuses_a_bad_declaration_and_stores_nothing(name, fields, rule):
    """1: ``SettingsDeclarationError``; no group stored, no variable claimed."""
    from backend.app.services.plugin_settings.groups import SettingsGroup, get_group, register_group

    before = dict(claimed_env_variables())

    with pytest.raises(SettingsDeclarationError, match=rule):
        register_group(SettingsGroup(name=name, label="Bad", fields=fields))

    assert get_group(name) is None
    assert claimed_env_variables() == before


def test_g1_a_variable_a_plugin_holds_refuses_the_group_and_the_reverse():
    """1: one owner per variable across owners: a plugin's alias against a group's derived name, both ways."""
    from backend.app.services.plugin_settings.groups import SettingsGroup, get_group, register_group

    # a plugin first: its alias equals the group's derived variable
    claim_env_variables("asset", "g1_rival", (PluginSettingField(key="token", type=STRING, scope=SYSTEM, label="Token", secret=True, env="LIBREFOLIO_G1_RIVAL_ALIAS"),))
    owner_of_alias = SettingsGroup(name="g1_alias", label="Alias", fields=(PluginSettingField(key="token", type=STRING, scope=SYSTEM, label="Token", secret=True, env="LIBREFOLIO_G1_RIVAL_ALIAS"),))

    with pytest.raises(SettingsDeclarationError, match="LIBREFOLIO_G1_RIVAL_ALIAS"):
        register_group(owner_of_alias)

    assert get_group("g1_alias") is None
    assert claimed_env_variables()["LIBREFOLIO_G1_RIVAL_ALIAS"] == ("asset", "g1_rival")
    # a group first: a plugin cannot take its alias
    _group("g1_holder", (PluginSettingField(key="token", type=STRING, scope=SYSTEM, label="Token", secret=True, env="LIBREFOLIO_G1_HOLDER_ALIAS"),))
    with pytest.raises(SettingsDeclarationError, match="LIBREFOLIO_G1_HOLDER_ALIAS"):
        claim_env_variables("asset", "g1_latecomer", (PluginSettingField(key="token", type=STRING, scope=SYSTEM, label="Token", secret=True, env="LIBREFOLIO_G1_HOLDER_ALIAS"),))
    assert claimed_env_variables()["LIBREFOLIO_G1_HOLDER_ALIAS"] == ("group", "g1_holder")


# =============================================================================
# 2. THE PLUGIN'S DECLARATION: settings_groups and validate_plugin_groups
# =============================================================================


def test_g1_the_mixin_declares_no_group_by_default():
    assert PluginSettingsMixin.settings_groups == ()


def test_g1_a_valid_declaration_passes_for_every_family_that_can_hold_it():
    """2: an empty tuple, a known group, two known groups; a group without a secret is fine for a tool."""
    from backend.app.services.plugin_settings.groups import validate_plugin_groups

    _group()
    _group("g1_plainonly", (_region(),))

    validate_plugin_groups(_plugin("g1_ok0", ()), family="asset")
    validate_plugin_groups(_plugin("g1_ok1", (GROUP,)), family="asset")
    validate_plugin_groups(_plugin("g1_ok2", (GROUP, "g1_plainonly")), family="fx")
    validate_plugin_groups(_plugin("g1_ok3", ("g1_plainonly",)), family="tool")


@pytest.mark.parametrize(
    ("declared", "rule"),
    [
        pytest.param("g", "tuple", id="the-string-g"),
        pytest.param(f"{GROUP}", "tuple", id="a-name-as-a-string"),
        pytest.param([GROUP], "tuple", id="a-list"),
        pytest.param((GROUP, 3), "str", id="a-non-string-name"),
        pytest.param(("g1_nope",), "g1_nope", id="unknown-name"),
        pytest.param((GROUP, GROUP), GROUP, id="name-twice"),
    ],
)
def test_g1_validate_plugin_groups_refuses_a_bad_names_value(declared, rule):
    from backend.app.services.plugin_settings.groups import validate_plugin_groups

    _group()

    with pytest.raises(SettingsDeclarationError, match=rule):
        validate_plugin_groups(_plugin("g1_bad", declared), family="asset")


def test_g1_validate_plugin_groups_refuses_a_group_field_the_plugin_also_declares():
    """2: a group field key equal to one of the plugin's own ``settings_fields`` keys."""
    from backend.app.services.plugin_settings.groups import validate_plugin_groups

    _group()

    with pytest.raises(SettingsDeclarationError, match="region"):
        validate_plugin_groups(_plugin("g1_dup", (GROUP,), fields=(_own("region"),)), family="asset")
    validate_plugin_groups(_plugin("g1_nodup", (GROUP,), fields=(_own("endpoint"),)), family="asset")


def test_g1_validate_plugin_groups_refuses_a_group_with_a_secret_for_a_family_without_secrets():
    """2: ``tool`` calls no external source: a group that holds a secret cannot be used by a tool."""
    from backend.app.services.plugin_settings.groups import validate_plugin_groups

    _group()

    with pytest.raises(SettingsDeclarationError, match="secret"):
        validate_plugin_groups(_plugin("g1_tool", (GROUP,)), family="tool")


@pytest.mark.parametrize(
    "declared",
    [pytest.param(("g1_nope",), id="unknown-group"), pytest.param("g", id="the-string-g"), pytest.param((GROUP, GROUP), id="group-twice")],
)
def test_g1_a_registry_refuses_a_plugin_with_a_bad_groups_declaration(declared):
    """2: ``register`` raises ``SettingsDeclarationError`` naming the class; not stored, nothing claimed."""
    _group()
    plugin = _plugin("g1_refused", declared)

    with pytest.raises(SettingsDeclarationError) as refused:
        _GroupLabRegistry.register(plugin)

    assert plugin.__qualname__ in str(refused.value)
    assert _GroupLabRegistry.get_plugin("g1_refused") is None
    assert not [variable for variable, owner in claimed_env_variables().items() if owner == ("asset", "g1_refused")]


def test_g1_a_registry_registers_a_plugin_with_known_groups_and_no_field_of_its_own():
    _group()
    plugin = _plugin("g1_accepted", (GROUP,))

    _GroupLabRegistry.register(plugin)

    assert _GroupLabRegistry.get_plugin("g1_accepted") is plugin


# =============================================================================
# 3 + 4. BINDING: env, row, default; no field of the plugin's own
# =============================================================================


@pytest.mark.asyncio
async def test_g1_a_plugin_with_no_field_of_its_own_gets_its_group_from_the_environment(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """4: the group's variables bind on a plugin whose ``settings_fields`` is empty; nothing is missing."""
    print_section("4: group values from the environment")
    _group()
    secret = _marker()
    monkeypatch.setenv(API_KEY_VARIABLE, secret)
    monkeypatch.setenv(REGION_VARIABLE, "jp")

    instance = await _configured(_plugin("g1_envplug"), "g1_envplug")

    group = instance.settings.group(GROUP)
    assert (group.secret("api_key"), group.get("region")) == (secret, "jp")
    assert instance.settings.missing == ()
    assert secret in instance.settings.secret_values()
    print_success("env value delivered, nothing missing")


@pytest.mark.asyncio
async def test_g1_the_groups_row_applies_then_the_default(through_private_engine: AsyncEngine):
    """4: the ``family="group"`` row of the group (secret decrypted, plain value), the default for what has no row; decoys never apply."""
    _group()
    secret = _marker()
    await _store(
        through_private_engine,
        _system_row(GROUP, "api_key", secret=secret),
        _system_row(GROUP, "region", value="us", family="group"),
        _system_row(GROUP, "region", value="jp", family="asset"),  # the same name under another family
        _system_row("g1_other", "region", value="jp"),  # another group
    )
    plugin = _plugin("g1_rowplug")

    with_rows = (await _configured(plugin, "g1_rowplug")).settings.group(GROUP)
    assert (with_rows.secret("api_key"), with_rows.get("region")) == (secret, "us")


@pytest.mark.asyncio
async def test_g1_a_field_without_a_row_takes_its_default(through_private_engine: AsyncEngine):
    _group()
    await _store(through_private_engine, _system_row(GROUP, "api_key", secret=_marker()))

    group = (await _configured(_plugin("g1_defplug"), "g1_defplug")).settings.group(GROUP)

    assert group.get("region") == "eu"


@pytest.mark.asyncio
async def test_g1_a_variable_wins_over_the_row_field_by_field(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """4: ``api_key`` locked by the variable, ``region`` still from its row."""
    _group()
    from_env, from_row = _marker("lfenv"), _marker("lfrow")
    await _store(through_private_engine, _system_row(GROUP, "api_key", secret=from_row), _system_row(GROUP, "region", value="us"))
    monkeypatch.setenv(API_KEY_VARIABLE, from_env)

    group = (await _configured(_plugin("g1_lockplug"), "g1_lockplug")).settings.group(GROUP)

    assert (group.secret("api_key"), group.get("region")) == (from_env, "us")


@pytest.mark.asyncio
async def test_g1_a_users_row_never_applies_to_a_group(through_private_engine: AsyncEngine):
    """4: a ``plugin_user_settings`` row under the group's name, for the user making the call, changes nothing."""
    _group()
    async with AsyncSession(through_private_engine, expire_on_commit=False) as session:
        alice = User(username="g1alice", email="g1alice@example.test", hashed_password="$argon2id$test")
        session.add(alice)
        await session.commit()
    await _store(through_private_engine, PluginUserSetting(user_id=alice.id, family="group", plugin_code=GROUP, field_key="region", value_json=json.dumps("us")))

    group = (await _configured(_plugin("g1_userplug"), "g1_userplug", user_id=alice.id)).settings.group(GROUP)

    assert group.get("region") == "eu"


@pytest.mark.asyncio
async def test_g1_bound_settings_for_binds_the_groups_of_a_plugin_with_no_field(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """4: ``bound_settings_for`` (the BRIM parent) answers for a plugin that has groups only, and still ``None`` for one with neither."""
    _group()
    secret = _marker()
    monkeypatch.setenv(API_KEY_VARIABLE, secret)
    _GroupLabRegistry.register(_plugin("g1_forbrim"))
    _GroupLabRegistry.register(_plugin("g1_neither", ()))

    bound = await runtime.bound_settings_for(_GroupLabRegistry, "g1_forbrim")

    assert bound is not None and bound.group(GROUP).secret("api_key") == secret
    assert await runtime.bound_settings_for(_GroupLabRegistry, "g1_neither") is None


# =============================================================================
# 3. BoundSettings: group(), missing, secret_values, unbound
# =============================================================================


@pytest.mark.asyncio
async def test_g1_group_of_an_undeclared_name_is_a_key_error(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    _group()
    _group("g1_b", (_region(),))
    monkeypatch.setenv(API_KEY_VARIABLE, _marker())

    configured = (await _configured(_plugin("g1_kerr"), "g1_kerr")).settings
    unbound = _plugin("g1_kerr2")().settings

    for settings in (configured, unbound):
        with pytest.raises(KeyError):
            settings.group("g1_b")
        with pytest.raises(KeyError):
            settings.group("nonexistent")


@pytest.mark.asyncio
async def test_g1_a_group_field_without_a_value_is_missing_as_group_dot_key(through_private_engine: AsyncEngine):
    """3: after the plugin's own missing keys, ``"g1_a.api_key"``."""
    _group()
    plugin = _plugin("g1_missing", (GROUP,), fields=(_own("endpoint", required=True),))

    settings = (await _configured(plugin, "g1_missing")).settings

    assert settings.missing == ("endpoint", f"{GROUP}.api_key")


@pytest.mark.asyncio
async def test_g1_an_invalid_group_variable_is_missing_even_when_optional(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """3: a set but invalid variable leaves the field without a usable value, never the default."""
    _group()
    monkeypatch.setenv(API_KEY_VARIABLE, _marker())
    monkeypatch.setenv(REGION_VARIABLE, "mars")

    settings = (await _configured(_plugin("g1_invalid"), "g1_invalid")).settings

    assert settings.missing == (f"{GROUP}.region",)


@pytest.mark.asyncio
async def test_g1_nothing_is_missing_when_the_groups_are_complete(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    _group()
    monkeypatch.setenv(API_KEY_VARIABLE, _marker())

    assert (await _configured(_plugin("g1_complete"), "g1_complete")).settings.missing == ()


def test_g1_an_instance_nobody_configured_gets_each_groups_defaults_and_its_required_fields_missing():
    """3: ``PluginSettingsMixin.settings`` unbound: defaults, no secret, the required field in ``missing``."""
    _group()
    _group("g1_b", (_region(), _own("endpoint", required=True)))
    plugin = _plugin("g1_unbound", (GROUP, "g1_b"), fields=(_own("endpoint", required=True),))

    settings = plugin().settings

    assert settings.group(GROUP).get("region") == "eu" and settings.group(GROUP).secret("api_key") is None
    assert settings.group("g1_b").get("region") == "eu"
    assert set(settings.missing) == {"endpoint", f"{GROUP}.api_key", "g1_b.endpoint"}
    assert settings.missing[0] == "endpoint", "the plugin's own keys come first"


# =============================================================================
# 3. MASKING AND FINGERPRINT
# =============================================================================


@pytest.mark.asyncio
async def test_g1_secret_values_include_the_groups_secrets(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    _group()
    group_secret, own_secret = _marker("lfgroup"), _marker("lfown")
    monkeypatch.setenv(API_KEY_VARIABLE, group_secret)
    monkeypatch.setenv(env_name("asset", "g1_secvals", "own_key"), own_secret)
    plugin = _plugin("g1_secvals", fields=(_own("own_key", secret=True),))

    assert (await _configured(plugin, "g1_secvals")).settings.secret_values() == frozenset({group_secret, own_secret})


@pytest.mark.asyncio
async def test_g1_a_group_secret_is_in_flight_and_masked_in_the_error_a_provider_raises(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """5: as the plugin's own secrets: in flight during the call, masked in the error that leaves."""
    _group()
    secret = _marker()
    monkeypatch.setenv(API_KEY_VARIABLE, secret)
    instance = await _configured(_plugin("g1_mask"), "g1_mask")
    seen: dict[str, object] = {}

    async def body():
        seen["in_flight"] = active_secrets()
        raise AssetSourceError(f"upstream refused the key {secret}", "PROVIDER_ERROR")

    with pytest.raises(AssetSourceError) as raised:
        await asset_core.call_provider(instance, lambda: body(), timeout=5)

    assert seen["in_flight"] == frozenset({secret})
    assert secret not in str(raised.value) and secret not in repr(raised.value.args) and MASK in str(raised.value)
    assert active_secrets() == frozenset()


@pytest.mark.asyncio
async def test_g1_the_fingerprint_of_a_plugin_without_groups_is_the_one_of_today(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """3: byte-identical to ``settings_fingerprint(plain, secrets)``, with and without a secret."""
    secret = _marker()
    monkeypatch.setenv(env_name("asset", "g1_nogroup", "own_key"), secret)
    with_secret = _plugin("g1_nogroup", (), fields=(_own("own_key", secret=True), _own("endpoint", default="https://x.example")))
    plain_only = _plugin("g1_nogroup2", (), fields=(_own("endpoint", default="https://x.example"),))

    secret_fp = (await _configured(with_secret, "g1_nogroup")).settings.fingerprint
    plain_fp = (await _configured(plain_only, "g1_nogroup2")).settings.fingerprint

    assert secret_fp == settings_fingerprint({"endpoint": "https://x.example"}, {"own_key": secret})
    assert plain_fp == settings_fingerprint({"endpoint": "https://x.example"}, {})


@pytest.mark.asyncio
async def test_g1_the_fingerprint_follows_the_group_values(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """3: equal for equal values, different when a group secret or a group plain value changes."""
    _group()
    plugin = _plugin("g1_fp")
    first, other = _marker("lfone"), _marker("lftwo")

    async def fingerprint() -> str:
        return (await _configured(plugin, "g1_fp")).settings.fingerprint

    monkeypatch.setenv(API_KEY_VARIABLE, first)
    base, again = await fingerprint(), await fingerprint()
    monkeypatch.setenv(API_KEY_VARIABLE, other)
    other_secret = await fingerprint()
    monkeypatch.setenv(API_KEY_VARIABLE, first)
    monkeypatch.setenv(REGION_VARIABLE, "jp")
    other_plain = await fingerprint()

    assert base and base == again
    assert len({base, other_secret, other_plain}) == 3
    assert first not in base and other not in other_secret


@pytest.mark.asyncio
async def test_g1_a_bound_settings_with_groups_survives_pickle(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    """3: the BRIM worker receives it by pickle: values, secrets, missing and fingerprint of the groups come back."""
    _group()
    secret = _marker()
    monkeypatch.setenv(API_KEY_VARIABLE, secret)
    monkeypatch.setenv(REGION_VARIABLE, "us")
    _GroupLabRegistry.register(_plugin("g1_pickled"))
    bound = await runtime.bound_settings_for(_GroupLabRegistry, "g1_pickled")

    clone = pickle.loads(pickle.dumps(bound))

    group = clone.group(GROUP)
    assert (group.secret("api_key"), group.get("region")) == (secret, "us")
    assert clone.missing == bound.missing == ()
    assert clone.fingerprint == bound.fingerprint and clone.secret_values() == bound.secret_values()
    with pytest.raises(KeyError):
        clone.group("g1_nope")


# =============================================================================
# 5. THE ASSET BOUNDARY
# =============================================================================


class _Spy:
    def __init__(self, body: Callable):
        self.calls = 0
        self.body = body

    def __call__(self):
        self.calls += 1
        return self.body()


async def _returns(value):
    return value


@pytest.mark.asyncio
async def test_g1_call_provider_refuses_a_provider_whose_group_lacks_a_required_value(through_private_engine: AsyncEngine):
    """5: ``NOT_CONFIGURED`` with ``details["missing"] == ["g1_a.api_key"]``, the provider not called."""
    print_section("5: NOT_CONFIGURED for a group's required field")
    _group()
    instance = await _configured(_plugin("g1_refuse"), "g1_refuse")
    spy = _Spy(lambda: _returns("reached"))

    with pytest.raises(AssetSourceError) as refused:
        await asset_core.call_provider(instance, spy, timeout=5)

    assert refused.value.error_code == "NOT_CONFIGURED"
    assert refused.value.details == {"missing": [f"{GROUP}.api_key"]}
    assert spy.calls == 0
    print_success("refused before the provider ran")


@pytest.mark.asyncio
async def test_g1_call_provider_calls_a_provider_whose_groups_are_complete(monkeypatch: pytest.MonkeyPatch, through_private_engine: AsyncEngine):
    _group()
    monkeypatch.setenv(API_KEY_VARIABLE, _marker())
    instance = await _configured(_plugin("g1_allowed"), "g1_allowed")
    spy = _Spy(lambda: _returns("reached"))

    assert await asset_core.call_provider(instance, spy, timeout=5) == "reached"
    assert spy.calls == 1


# =============================================================================
# 6. THE GATE: every plugin names registered groups; every shipped group is used
# =============================================================================


def groups_not_registered(plugins: list[tuple[str, str, type]], known: set[str]) -> list[str]:
    """``family/code: name`` for every group a plugin names that is not registered."""
    return [f"{family}/{code}: {name}" for family, code, plugin in plugins for name in getattr(plugin, "settings_groups", ()) if name not in known]


def groups_unused(groups: dict, plugins: list[tuple[str, str, type]]) -> list[str]:
    """The registered groups that are not ``test_only`` and no plugin names."""
    used = {name for _family, _code, plugin in plugins for name in getattr(plugin, "settings_groups", ())}
    return sorted(name for name, group in groups.items() if not group.test_only and name not in used)


def _registered() -> list[tuple[str, str, type]]:
    return [(family, code, registry.get_plugin(code)) for family, registry in FAMILY_REGISTRIES.items() for code in registry.list_plugin_codes()]


def test_g1_the_gate_flags_an_unknown_group_and_an_unused_one_and_skips_a_test_only_group():
    """6, barrier: each guard sees on synthetic input what it must see."""
    from backend.app.services.plugin_settings.groups import all_groups

    _group("g1_used", (_region(),))
    _group("g1_unused", (_region(),))
    _group("g1_lab", (_region(),), test_only=True)
    plugins = [("asset", "g1_p", _plugin("g1_p", ("g1_used", "g1_ghost")))]

    assert groups_not_registered(plugins, set(all_groups())) == ["asset/g1_p: g1_ghost"]
    unused = groups_unused({name: group for name, group in all_groups().items() if name.startswith(PREFIX)}, plugins)
    assert unused == ["g1_unused"], "a test-only group is not demanded to be used"


def test_g1_every_registered_plugin_names_registered_groups_and_every_shipped_group_is_used():
    """6: over the real registries after their discovery (vacuous today: no group ships in G1)."""
    from backend.app.services.plugin_settings.groups import all_groups

    plugins = _registered()
    assert plugins, "barrier: the registries were walked"

    groups = all_groups()
    assert not groups_not_registered(plugins, set(groups)), groups_not_registered(plugins, set(groups))
    assert not groups_unused(groups, plugins), f"groups no plugin uses: {groups_unused(groups, plugins)}"


def test_g1_the_default_baseline_of_a_plugin_with_groups_is_its_grouped_fingerprint():
    """3 (the stale-parse rule, CP12): a result that recorded no fingerprint was drawn over the defaults. For a plugin with
    groups the baseline is the GROUPED fingerprint of the defaults, its groups' included: otherwise every unrecorded result of
    such a plugin would read as stale for ever."""
    from backend.app.services.plugin_settings.groups import SettingsGroup
    from backend.app.services.plugin_settings.resolver import build_bound_settings, default_settings_fingerprint, settings_changed_since

    print_section("G1: the default baseline with groups")
    group = SettingsGroup(name="g1_base", label="Base", fields=(PluginSettingField(key="plan", type=SettingType.SELECT, scope=SettingScope.SYSTEM, label="Plan", default="demo", options=(SettingOption("demo", "Demo"), SettingOption("pro", "Pro"))),))
    fields = (PluginSettingField(key="limit", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label="Limit", default=5),)
    bound = build_bound_settings("asset", "g1_base_plugin", fields, {}, None, user_id=None, groups=[(group, {})])

    assert default_settings_fingerprint(fields, (group,)) == bound.fingerprint
    assert not settings_changed_since(None, bound, fields, (group,))
    assert default_settings_fingerprint(fields) == settings_fingerprint({"limit": 5}, {}), "without groups: unchanged"
    print_success("the defaults' baseline includes the groups")
