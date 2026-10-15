"""Plugin settings, resolution and delivery: the value each field takes, and what a plugin call receives (plan 03, CP10).

Modules under test: ``services/plugin_settings/resolver.py`` and ``runtime.py``, the asset boundary in
``services/assets/core.py`` (``configured_provider``, ``call_provider``, ``settings_cache_part(_for)``) and the FX one in
``services/fx/runtime.py``. The contract pinned here:

1. **Precedence**, field by field: the derived variable, then its ``_FILE``, then the alias (a secret's only), then its
   ``_FILE``, then the stored row, then the default. Only a ``system`` field is set by the environment. A set variable wins and locks
   the field **even when its value is invalid**: the field then has the problem ``invalid_env`` and no value — never a
   silent fallback to the row or the default; a ``_FILE`` that cannot be read is the same. The plugin is then not
   configured: the field counts as missing, required or not, and the log says why, once per variable and process,
   never with the value. A blank variable is unset.
2. **Rows**: a secret is decrypted only for a call (``decrypt=True``); one this key cannot read — another key, a blob
   moved from another user — has the problem ``unreadable`` (logged once per process, without the value); the
   catalogue (``decrypt=False``) judges a secret by its key id and never decrypts. A row the field refuses now (a bad
   value, a secret where a plain value is due, the reverse) counts as unset with the problem ``invalid_stored``. The
   ``user`` rows apply only when the values are for a user.
3. **Fingerprints**: a plugin that declares no field has none (the empty string in its cache keys); plain values only
   give a SHA-256 of their canonical JSON, the same under any instance key; with secrets an HMAC under the fingerprint
   subkey, different under another instance key, and never the secret. **An unusable instance key** (a
   ``LIBREFOLIO_INSTANCE_KEY_FILE`` that is gone) raises nothing: every stored secret is ``unreadable`` for the catalogue
   and for a call, one error is logged per process, no key file is made in its place, the environment's secrets still
   reach the calls, and the fingerprint is a SHA-256 of the plain values and the sorted secret names, never a value. ``build_bound_settings`` binds the plain values,
   the secrets, the required fields left without a usable value, and that fingerprint.
4. **Delivery** (``configure_instance``): a plugin without fields comes back untouched, with no database access, and so
   does an object that declares none — a test double without the mixin or a ``settings_fields`` attribute, also when
   ``configured_provider`` / ``configured_fx_provider`` hand it out; a
   plugin with ``user`` fields only reads nothing without a user; otherwise the instance's rows of that plugin and,
   for a user, that user's rows, and nobody else's; a database error leaves the environment and the defaults and logs a
   warning. ``configured_provider`` / ``configured_fx_provider`` hand back a configured new instance (``None`` for an
   unknown code), and the settings part of a cache key follows the instance's values only.
5. **The boundaries** (``call_provider``, ``call_fx_provider``): a required field without a value refuses the call
   with ``NOT_CONFIGURED`` (asset: ``AssetSourceError`` with ``details["missing"]``; FX: ``FXNotConfiguredError``)
   **before** ``fn`` is called; during the call the secrets are in flight, in the provider's thread too; an error the
   plugin raises reaches the caller masked in place — the very object, its type and its chain —, unless it still shows
   a secret after masking (a ``__str__`` over ``__slots__``, a group's own message): an ``Exception`` is then replaced by
   ``AssetSourceError`` ``PROVIDER_ERROR`` / ``FXServiceError`` carrying its masked description and no ``__cause__`` or
   ``__context__``, while a ``BaseException`` that is no ``Exception`` (a cancellation) is never replaced; an object
   that is not a plugin goes through unchecked.

Pure: the rows live in a private SQLite file under ``tmp_path`` (``create_all``), reached through a private engine put
in place of ``runtime.get_async_engine``; the instance key is a test key set with ``monkeypatch`` and the data
directory points into ``tmp_path``; every variable a test sets goes through ``monkeypatch``.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.services.asset_source_providers.mockprov.plugin import SETTINGS_ECHO_QUERY, MockProvider
from backend.app.services.assets import core as asset_core
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx.base import FXNotConfiguredError, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.plugin_settings import resolver, runtime
from backend.app.services.plugin_settings.contract import BoundSettings, PluginSettingsMixin
from backend.app.services.plugin_settings.crypto import encrypt_secret, fingerprint_subkey, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, env_name, env_variables
from backend.app.services.plugin_settings.resolver import FieldState, StoredValue, build_bound_settings, resolve_plugin_fields, settings_fingerprint
from backend.app.utils.runtime.secret_masking import MASK, active_secrets, exception_renders_secret, mask_text, masked_description
from backend.test_scripts.test_utils import print_section, print_success

KEY_A = "LibreFolio-plugin-settings-test-key-A-0123456789"
KEY_B = "LibreFolio-plugin-settings-test-key-B-9876543210"
FOREIGN_SUBKEY = bytes([9]) * 32
STAMP = datetime(2026, 10, 15, 12, 0, 0)
SYSTEM, USER = SettingScope.SYSTEM, SettingScope.USER
STRING, NUMBER, INTEGER, BOOLEAN, SELECT = SettingType.STRING, SettingType.NUMBER, SettingType.INTEGER, SettingType.BOOLEAN, SettingType.SELECT

REGIONS = ("eu", "us", "jp", "uk", "ca", "au")
LAB_FIELDS = (
    PluginSettingField(key="api_key", type=STRING, scope=SYSTEM, label="API key", secret=True, required=True, env="LIBREFOLIO_LAB_API_KEY"),
    PluginSettingField(key="region", type=SELECT, scope=SYSTEM, label="Region", default="eu", options=tuple(SettingOption(value, value.upper()) for value in REGIONS)),
    PluginSettingField(key="tolerance", type=NUMBER, scope=SYSTEM, label="Tolerance", default=0.5, minimum=0, maximum=10),
    PluginSettingField(key="verbose", type=BOOLEAN, scope=SYSTEM, label="Verbose", default=False),
    PluginSettingField(key="endpoint", type=STRING, scope=SYSTEM, label="Endpoint", required=True),
    PluginSettingField(key="limit", type=INTEGER, scope=USER, label="Limit", default=10, minimum=1, maximum=50),
    PluginSettingField(key="token", type=STRING, scope=USER, label="Token", secret=True),
)
DERIVED_REGION = "LIBREFOLIO_PLUGIN_ASSET_LAB_REGION"
DERIVED_API_KEY, ALIAS_API_KEY = "LIBREFOLIO_PLUGIN_ASSET_LAB_API_KEY", "LIBREFOLIO_LAB_API_KEY"


class _LabPlugin(PluginSettingsMixin):
    """An asset-family plugin of the tests: the lab fields, and nothing else of a provider."""

    provider_code = "lab"
    settings_fields = LAB_FIELDS


class _BarePlugin(PluginSettingsMixin):
    provider_code = "bare"


class _UserOnlyPlugin(PluginSettingsMixin):
    provider_code = "user_only"
    settings_fields = (PluginSettingField(key="limit", type=INTEGER, scope=USER, label="Limit", default=3, minimum=1),)


class _NotAPlugin:
    """A test double of the suites: no settings mixin, so the boundaries call it as it is."""

    provider_code = "double"


class _SuiteDouble:
    """A provider double as the other suites write theirs (``PartialProvider``, ``_DummyProvider``, ``FakeProbeProvider``).

    A plain class: no settings mixin, no ``settings_fields`` attribute at all, not even a ``provider_code``.
    """


class _SlotsLeak(Exception):
    """A plugin's error whose text a ``__str__`` builds from state outside ``__dict__``: masking cannot rewrite it."""

    __slots__ = ("_hidden",)

    def __init__(self, hidden: str):
        super().__init__("opaque")
        self._hidden = hidden

    def __str__(self) -> str:
        return f"failed with {self._hidden}"


class _AttributeLeak(Exception):
    """A plugin's error whose ``__str__`` reads a normal attribute: masked in place, so it keeps its type."""

    def __init__(self, hidden: str):
        super().__init__("attribute")
        self.hidden = hidden

    def __str__(self) -> str:
        return f"failed with {self.hidden}"


class _SlotsHalt(BaseException):
    """A ``BaseException`` that is no ``Exception`` and still shows a secret: never replaced by a boundary."""

    __slots__ = ("_hidden",)

    def __init__(self, hidden: str):
        super().__init__("halt")
        self._hidden = hidden

    def __str__(self) -> str:
        return f"halted with {self._hidden}"


class _SlotsCancelled(asyncio.CancelledError):
    """A cancellation that still shows a secret: never replaced by a boundary either."""

    __slots__ = ("_hidden",)

    def __init__(self, hidden: str):
        super().__init__("cancelled")
        self._hidden = hidden

    def __str__(self) -> str:
        return f"cancelled with {self._hidden}"


def _marker(prefix: str = "lfsecret") -> str:
    return f"{prefix}{uuid.uuid4().hex[:16]}"


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The test key A as the instance key, a data directory of this test, and no ambient variable of the lab, mockprov or MOCKFX fields."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(data_dir))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    declared = [("asset", "lab", field) for field in LAB_FIELDS] + [("asset", "mockprov", field) for field in MockProvider.settings_fields] + [("fx", "MOCKFX", field) for field in MockFXProvider.settings_fields]
    for family, code, field in declared:
        for name in {*env_variables(family, code, field), env_name(family, code, field.key)}:
            monkeypatch.delenv(name, raising=False)
            monkeypatch.delenv(name + "_FILE", raising=False)
    # The once-per-process logs start empty for each test: what a test asserts about them is about its own resolution.
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    return data_dir


def _make_the_key_unusable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The instance key as an operator can break it: ``LIBREFOLIO_INSTANCE_KEY_FILE`` naming a file that is gone.

    ``derive_key`` then raises ``InstanceKeyError`` for every purpose, and never generates a key in its place.
    """
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY_FILE", str(tmp_path / "gone-instance.key"))


def _plain(value: object, updated_at: datetime = STAMP) -> StoredValue:
    return StoredValue(json.dumps(value), None, None, updated_at)


def _secret_row(plaintext: str, key: str, scope: str = "system", user_id: int | None = None, *, subkey: bytes | None = None, family: str = "asset", code: str = "lab") -> StoredValue:
    """A stored secret of the lab plugin, under the current subkey unless another one is given."""
    subkey = settings_subkey() if subkey is None else subkey
    blob = encrypt_secret(subkey, secret_aad(family, code, key, scope, user_id), plaintext)
    return StoredValue(None, blob, key_id_of(subkey), STAMP)


def _resolve(system: dict | None = None, user: dict | None = None, *, user_id: int | None = 1, decrypt: bool = True) -> dict[str, FieldState]:
    states = resolve_plugin_fields("asset", "lab", LAB_FIELDS, system or {}, user, user_id=user_id, decrypt=decrypt)
    assert [state.field.key for state in states] == [field.key for field in LAB_FIELDS], "the states come in declaration order"
    return {state.field.key: state for state in states}


def _summary(state: FieldState) -> tuple:
    return (state.source, state.value, state.is_set, state.locked, state.env_variable, state.problem)


# =============================================================================
# 1. PRECEDENCE
# =============================================================================

#: The layers that can set the secret ``api_key``, from the first read to the last, each with its own value.
_SECRET_LAYERS = ("derived", "derived_file", "alias", "alias_file", "row")
#: The layers of the plain ``region``: a plain field has its derived variable only.
_PLAIN_LAYERS = ("derived", "derived_file", "row")
_REGION_VALUES = {"derived": "us", "derived_file": "jp", "row": "au"}


def _set_layer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, layer: str, variable: str, value: str) -> None:
    """Set one environment layer: the variable itself, or its ``_FILE`` naming a file that holds the value."""
    if layer.endswith("_file"):
        path = tmp_path / f"{layer}.txt"
        path.write_text(f"{value}\n", encoding="utf-8")
        monkeypatch.setenv(variable + "_FILE", str(path))
    else:
        monkeypatch.setenv(variable, value)


@pytest.mark.parametrize(
    ("top", "source", "variable"),
    [
        pytest.param("derived", "env", DERIVED_API_KEY, id="the-derived-variable-first"),
        pytest.param("derived_file", "env", DERIVED_API_KEY, id="then-its-_FILE"),
        pytest.param("alias", "env", ALIAS_API_KEY, id="then-the-alias"),
        pytest.param("alias_file", "env", ALIAS_API_KEY, id="then-the-alias-_FILE"),
        pytest.param("row", "db", None, id="then-the-row"),
        pytest.param(None, "none", None, id="then-nothing-a-secret-has-no-default"),
    ],
)
def test_the_precedence_of_a_secret_system_field(top, source, variable, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """1: every layer from ``top`` down is set, each with its own secret: the one of ``top`` is delivered, and an env layer locks."""
    print_section(f"1: precedence of a secret, {top or 'nothing set'} on top")
    values = {layer: _marker(f"lf{layer.replace('_', '')}") for layer in _SECRET_LAYERS}
    layers = _SECRET_LAYERS[_SECRET_LAYERS.index(top) :] if top else ()
    for layer in layers:
        if layer != "row":
            _set_layer(monkeypatch, tmp_path, layer, DERIVED_API_KEY if layer.startswith("derived") else ALIAS_API_KEY, values[layer])
    system = {"api_key": _secret_row(values["row"], "api_key")} if "row" in layers else {}

    state = _resolve(system)["api_key"]

    expected_value = values[top] if top else None
    assert _summary(state) == (source, expected_value, top is not None, source == "env", variable, None)
    print_success(f"api_key from {state.source} ({variable or 'no variable'})")


@pytest.mark.parametrize(
    ("top", "expected"),
    [
        pytest.param("derived", ("env", "us", True, True, DERIVED_REGION, None), id="the-derived-variable-first"),
        pytest.param("derived_file", ("env", "jp", True, True, DERIVED_REGION, None), id="then-its-_FILE"),
        pytest.param("row", ("db", "au", True, False, None, None), id="then-the-row"),
        pytest.param(None, ("default", "eu", False, False, None, None), id="then-the-default"),
    ],
)
def test_the_precedence_of_a_plain_system_field(top, expected, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """1: the derived variable, its ``_FILE``, the row, the default; the ``_FILE`` locks under the variable's own name."""
    layers = _PLAIN_LAYERS[_PLAIN_LAYERS.index(top) :] if top else ()
    for layer in layers:
        if layer != "row":
            _set_layer(monkeypatch, tmp_path, layer, DERIVED_REGION, _REGION_VALUES[layer])
    system = {"region": _plain(_REGION_VALUES["row"])} if "row" in layers else {}

    assert _summary(_resolve(system)["region"]) == expected


@pytest.mark.parametrize(
    ("variable", "value", "key"),
    [
        pytest.param(DERIVED_REGION, "xx", "region", id="select-not-an-option"),
        pytest.param(ALIAS_API_KEY, "short", "api_key", id="secret-alias-too-short"),
        pytest.param(DERIVED_API_KEY, "has\ta-tab-inside", "api_key", id="secret-with-a-control-character"),
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", "11", "tolerance", id="number-above-its-maximum"),
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", "nan", "tolerance", id="number-not-finite"),
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_VERBOSE", "maybe", "verbose", id="boolean-word-unknown"),
    ],
)
def test_a_set_variable_locks_the_field_even_when_its_value_is_invalid(variable, value, key, monkeypatch: pytest.MonkeyPatch):
    """1: an invalid variable gives ``invalid_env`` and no value: neither the row nor the default stand in for it."""
    monkeypatch.setenv(variable, value)
    rows = {"region": _plain("au"), "tolerance": _plain(2.5), "verbose": _plain(True), "api_key": _secret_row(_marker(), "api_key")}

    state = _resolve(rows)[key]

    assert _summary(state) == ("env", None, True, True, variable, "invalid_env"), _summary(state)


def test_an_invalid_derived_variable_wins_over_a_valid_alias(monkeypatch: pytest.MonkeyPatch):
    """1: the first set variable decides: a valid alias below an invalid derived variable is not used."""
    monkeypatch.setenv(DERIVED_API_KEY, "short")
    monkeypatch.setenv(ALIAS_API_KEY, _marker())

    assert _summary(_resolve()["api_key"]) == ("env", None, True, True, DERIVED_API_KEY, "invalid_env")


@pytest.mark.parametrize("variable", [DERIVED_REGION, DERIVED_API_KEY, ALIAS_API_KEY])
def test_a_file_variable_that_cannot_be_read_locks_the_field(variable, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """1: ``NAME_FILE`` naming a missing file: ``invalid_env``, locked under ``NAME``, and the row is not used."""
    monkeypatch.setenv(variable + "_FILE", str(tmp_path / "missing.txt"))
    key = "region" if variable == DERIVED_REGION else "api_key"

    state = _resolve({"region": _plain("au"), "api_key": _secret_row(_marker(), "api_key")})[key]

    assert _summary(state) == ("env", None, True, True, variable, "invalid_env")


def test_a_blank_variable_is_unset(monkeypatch: pytest.MonkeyPatch):
    """1: a blank value, or a blank ``_FILE``, is no setting: the next layer applies."""
    secret = _marker()
    monkeypatch.setenv(DERIVED_REGION, "   ")
    monkeypatch.setenv(DERIVED_REGION + "_FILE", "  ")
    monkeypatch.setenv(DERIVED_API_KEY, "  ")
    monkeypatch.setenv(ALIAS_API_KEY + "_FILE", " ")

    states = _resolve({"region": _plain("au"), "api_key": _secret_row(secret, "api_key")})

    assert _summary(states["region"]) == ("db", "au", True, False, None, None)
    assert _summary(states["api_key"]) == ("db", secret, True, False, None, None)


def test_the_derived_name_of_a_plain_field_has_no_alias_to_fall_back_on(monkeypatch: pytest.MonkeyPatch):
    """1: an alias is a secret field's only: a variable named like one for ``region`` sets nothing."""
    monkeypatch.setenv("LIBREFOLIO_LAB_REGION", "jp")

    assert _summary(_resolve({"region": _plain("au")})["region"]) == ("db", "au", True, False, None, None)


@pytest.mark.parametrize(
    ("variable", "text", "key", "value"),
    [
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_VERBOSE", " Yes ", "verbose", True, id="boolean-word"),
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", "1.5", "tolerance", 1.5, id="number"),
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_ENDPOINT", " https://api.example/v1 ", "endpoint", "https://api.example/v1", id="text-stripped"),
    ],
)
def test_a_variable_is_parsed_for_its_type(variable, text, key, value, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(variable, text)
    assert _summary(_resolve()[key]) == ("env", value, True, True, variable, None)


def test_a_secret_from_the_environment_is_delivered_but_never_shown_in_the_catalogue(monkeypatch: pytest.MonkeyPatch):
    """1: the alias of the secret: the plaintext for a call, nothing but ``is_set`` and the lock for the catalogue."""
    secret = _marker()
    monkeypatch.setenv("LIBREFOLIO_LAB_API_KEY", secret)

    for_a_call = _resolve(decrypt=True)["api_key"]
    for_the_catalogue = _resolve(decrypt=False)["api_key"]

    assert _summary(for_a_call) == ("env", secret, True, True, "LIBREFOLIO_LAB_API_KEY", None)
    assert _summary(for_the_catalogue) == ("env", None, True, True, "LIBREFOLIO_LAB_API_KEY", None)


def test_the_environment_never_sets_a_user_field(monkeypatch: pytest.MonkeyPatch):
    """1: ``LIBREFOLIO_PLUGIN_ASSET_LAB_LIMIT`` is no variable of the field: the user's row, or the default, applies."""
    monkeypatch.setenv("LIBREFOLIO_PLUGIN_ASSET_LAB_LIMIT", "5")
    monkeypatch.setenv("LIBREFOLIO_PLUGIN_ASSET_LAB_TOKEN", "an-env-token-value")

    with_row = _resolve(user={"limit": _plain(7)})
    without = _resolve(user={})

    assert _summary(with_row["limit"]) == ("db", 7, True, False, None, None)
    assert _summary(without["limit"]) == ("default", 10, False, False, None, None)
    assert _summary(without["token"]) == ("none", None, False, False, None, None)


# =============================================================================
# 2. ROWS
# =============================================================================


def test_the_user_rows_apply_only_when_the_values_are_for_a_user():
    """2: ``user_rows=None`` (a scheduled sync): the user fields take their defaults; a system row never fills a user field."""
    token = _marker()
    user_rows = {"limit": _plain(7), "token": _secret_row(token, "token", "user", 1)}

    for_the_user = _resolve({"limit": _plain(42)}, user_rows, user_id=1)
    for_nobody = _resolve({"limit": _plain(42)}, None, user_id=None)

    assert (for_the_user["limit"].value, for_the_user["token"].value) == (7, token)
    assert (for_nobody["limit"].value, for_nobody["limit"].source, for_nobody["token"].source) == (10, "default", "none")


def test_a_readable_secret_is_decrypted_for_a_call_and_only_judged_for_the_catalogue(monkeypatch: pytest.MonkeyPatch):
    """2: ``decrypt=True`` gives the plaintext; ``decrypt=False`` never decrypts, and compares the key id only."""
    secret = _marker()
    system = {"api_key": _secret_row(secret, "api_key")}

    for_a_call = _resolve(system)["api_key"]
    monkeypatch.setattr(resolver, "decrypt_secret", lambda *_args: pytest.fail("the catalogue must not decrypt"))
    for_the_catalogue = _resolve(system, decrypt=False)["api_key"]

    assert _summary(for_a_call) == ("db", secret, True, False, None, None) and for_a_call.updated_at == STAMP
    assert _summary(for_the_catalogue) == ("db", None, True, False, None, None)


def test_the_catalogue_judges_by_key_id_a_damaged_blob_under_the_current_key_is_set():
    """2: the catalogue cannot see damage it does not decrypt; a call does, and reports it unreadable."""
    blob = bytearray(_secret_row(_marker(), "api_key").secret_ciphertext)
    blob[-1] ^= 1
    system = {"api_key": StoredValue(None, bytes(blob), key_id_of(settings_subkey()), STAMP)}

    assert _resolve(system, decrypt=False)["api_key"].problem is None
    assert _resolve(system, decrypt=True)["api_key"].problem == "unreadable"


@pytest.mark.parametrize("decrypt", [True, False], ids=["for-a-call", "for-the-catalogue"])
def test_a_secret_under_another_key_is_unreadable(decrypt: bool):
    """2: set, but unreadable: no value, no fallback; a call reports it, the catalogue too (by key id)."""
    system = {"api_key": _secret_row(_marker(), "api_key", subkey=FOREIGN_SUBKEY)}

    assert _summary(_resolve(system, decrypt=decrypt)["api_key"]) == ("db", None, True, False, None, "unreadable")


def test_a_secret_moved_from_another_user_is_unreadable():
    """2: alice's ciphertext copied into bob's row decrypts for nobody: bob's call gets no value."""
    alices = _secret_row(_marker(), "token", "user", 1)

    state = _resolve(user={"token": alices}, user_id=2)["token"]

    assert _summary(state) == ("db", None, True, False, None, "unreadable")


def test_an_unreadable_secret_is_logged_once_without_its_value():
    """2: one warning per process for one row, naming the field and the plugin, never the value."""
    secret = _marker()
    system = {"api_key": _secret_row(secret, "api_key", subkey=FOREIGN_SUBKEY)}

    with capture_logs() as logs:
        _resolve(system)
        _resolve(system)

    warnings = [entry for entry in logs if entry["event"].startswith("Plugin setting unreadable")]
    assert len(warnings) == 1, f"one warning per process, got {warnings}"
    assert {key: warnings[0].get(key) for key in ("log_level", "family", "plugin", "field", "scope")} == {"log_level": "warning", "family": "asset", "plugin": "lab", "field": "api_key", "scope": "system"}
    assert secret not in repr(logs)


@pytest.mark.parametrize(
    ("key", "stored", "expected"),
    [
        pytest.param("region", _plain("xx"), ("default", "eu", False, False, None, "invalid_stored"), id="value-not-an-option"),
        pytest.param("tolerance", _plain(99), ("default", 0.5, False, False, None, "invalid_stored"), id="number-out-of-bounds"),
        pytest.param("verbose", _plain("true"), ("default", False, False, False, None, "invalid_stored"), id="boolean-stored-as-text"),
        pytest.param("region", StoredValue("{not json", None, None, STAMP), ("default", "eu", False, False, None, "invalid_stored"), id="malformed-json"),
        pytest.param("region", StoredValue(None, b"\x01" + bytes(40), "ab" * 16, STAMP), ("default", "eu", False, False, None, "invalid_stored"), id="a-secret-where-a-value-is-due"),
        pytest.param("api_key", _plain("a-plain-api-key"), ("none", None, False, False, None, "invalid_stored"), id="a-value-where-a-secret-is-due"),
        pytest.param("endpoint", _plain(""), ("none", None, False, False, None, "invalid_stored"), id="empty-text-without-default"),
    ],
)
def test_a_row_the_field_refuses_now_counts_as_unset(key, stored, expected):
    """2: ``invalid_stored``: the default applies (or nothing), and the row's date is kept for the interface."""
    state = _resolve({key: stored})[key]

    assert _summary(state) == expected
    assert state.updated_at == STAMP


# =============================================================================
# 3. FINGERPRINTS AND BINDINGS
# =============================================================================


def _canonical(plain: dict, secrets: dict) -> bytes:
    return json.dumps({"plain": plain, "secret": secrets}, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def test_plain_values_only_give_a_sha256_under_any_instance_key(monkeypatch: pytest.MonkeyPatch):
    """3: no key is derived for plain values; the order of the keys does not matter, a different value does."""
    plain = {"region": "us", "limit": 7}
    expected = hashlib.sha256(_canonical(plain, {})).hexdigest()[:32]
    monkeypatch.setattr(resolver, "fingerprint_subkey", lambda: pytest.fail("no key may be derived for plain values"))

    fingerprint = settings_fingerprint(plain, {})
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)

    assert fingerprint == expected and len(fingerprint) == 32
    assert settings_fingerprint({"limit": 7, "region": "us"}, {}) == fingerprint
    assert settings_fingerprint({"region": "us", "limit": 8}, {}) != fingerprint


def test_with_secrets_the_fingerprint_is_an_hmac_that_depends_on_the_instance_key(monkeypatch: pytest.MonkeyPatch):
    """3: nobody can test a guess of a secret against a cache key: HMAC under the fingerprint subkey, never the secret."""
    print_section("3: the fingerprint with secrets")
    secret = _marker()
    plain, secrets = {"region": "us"}, {"api_key": secret}

    under_a = settings_fingerprint(plain, secrets)
    expected = hmac.new(fingerprint_subkey(), _canonical(plain, secrets), hashlib.sha256).hexdigest()[:32]
    other_secret = settings_fingerprint(plain, {"api_key": secret + "x"})
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)
    under_b = settings_fingerprint(plain, secrets)

    assert under_a == expected
    assert under_a != hashlib.sha256(_canonical(plain, secrets)).hexdigest()[:32], "a plain hash of the secret would let a guess be tested"
    assert under_b != under_a and other_secret != under_a
    assert secret not in under_a
    print_success("HMAC under the fingerprint subkey; another instance key or secret, another fingerprint")


def test_a_plugin_without_fields_has_no_fingerprint():
    """3: nothing bound, nothing in the cache key: the empty string, for the asset and the FX boundary alike."""
    assert BoundSettings.unbound(()).fingerprint == ""
    assert asset_core.settings_cache_part(_BarePlugin()) == "" and fx_runtime.settings_cache_part(_BarePlugin()) == ""
    assert asset_core.settings_cache_part(_NotAPlugin()) == "" and fx_runtime.settings_cache_part(_NotAPlugin()) == ""


def test_build_bound_settings_binds_values_secrets_missing_and_the_fingerprint(monkeypatch: pytest.MonkeyPatch):
    """3: the plain values with a value, the secrets, the required fields without a usable value; the fingerprint of both."""
    print_section("3: build_bound_settings")
    token = _marker()
    monkeypatch.setenv("LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", "2")
    system = {"region": _plain("us"), "api_key": _secret_row(_marker(), "api_key", subkey=FOREIGN_SUBKEY)}
    user = {"limit": _plain(7), "token": _secret_row(token, "token", "user", 1)}

    bound = build_bound_settings("asset", "lab", LAB_FIELDS, system, user, user_id=1)

    plain = {"region": "us", "tolerance": 2.0, "verbose": False, "limit": 7}
    assert bound.plain_values() == plain
    assert bound.secret("token") == token and bound.secret("api_key") is None
    assert bound.missing == ("api_key", "endpoint"), "an unreadable required secret and an unset required field are missing"
    assert bound.fingerprint == settings_fingerprint(plain, {"token": token})
    print_success(f"missing {bound.missing}, fingerprint {bound.fingerprint}")


def _configured_rows() -> dict[str, StoredValue]:
    """Rows that configure the lab plugin completely: whatever is missing afterwards, a variable made it so."""
    return {"endpoint": _plain("https://api.example"), "api_key": _secret_row(_marker(), "api_key")}


def test_an_invalid_variable_leaves_its_required_field_missing(monkeypatch: pytest.MonkeyPatch):
    """3: no silent fallback: a required field locked by an invalid variable is missing even with a valid row."""
    monkeypatch.setenv("LIBREFOLIO_PLUGIN_ASSET_LAB_ENDPOINT", "has\na control character")
    bound = build_bound_settings("asset", "lab", LAB_FIELDS, _configured_rows(), None, user_id=None)

    assert bound.missing == ("endpoint",)


@pytest.mark.parametrize(
    ("variable", "value", "key"),
    [
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", "abc", "tolerance", id="optional-number"),
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_VERBOSE", "maybe", "verbose", id="optional-boolean"),
        pytest.param(DERIVED_REGION, "atlantis", "region", id="optional-select"),
    ],
)
def test_an_invalid_variable_leaves_even_an_optional_field_missing(variable, value, key, monkeypatch: pytest.MonkeyPatch):
    """3: the plugin is not configured until the variable is fixed: the field is missing, its default never stands in."""
    monkeypatch.setenv(variable, value)
    bound = build_bound_settings("asset", "lab", LAB_FIELDS, _configured_rows(), None, user_id=None)

    assert bound.missing == (key,)
    assert key not in bound.plain_values(), "an invalid variable never falls back to the default"


def test_an_invalid_variable_is_logged_once_with_a_reason_and_never_its_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """3: one warning per variable and process, naming the variable, the plugin and the field, and why — never the value."""
    print_section("3: the log of an invalid variable")
    number, short_secret = _marker("lfnumber"), "Q" + uuid.uuid4().hex[:6]
    monkeypatch.setenv("LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", number)
    monkeypatch.setenv(ALIAS_API_KEY, short_secret)
    monkeypatch.setenv(DERIVED_REGION + "_FILE", str(tmp_path / "missing-region.txt"))

    with capture_logs() as logs:
        _resolve(decrypt=False)
        _resolve(decrypt=True)
        build_bound_settings("asset", "lab", LAB_FIELDS, {}, None, user_id=None)

    warnings = {entry["variable"]: entry for entry in logs if entry["event"] == "Plugin setting variable invalid: the plugin is not configured until it is fixed"}
    assert len([entry for entry in logs if entry["event"].startswith("Plugin setting variable invalid")]) == 3, "once per variable, however many resolutions"
    assert set(warnings) == {"LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", ALIAS_API_KEY, DERIVED_REGION}
    for entry in warnings.values():
        assert set(entry) == {"event", "log_level", "variable", "family", "plugin", "field", "reason"} and entry["log_level"] == "warning", entry
        assert (entry["family"], entry["plugin"]) == ("asset", "lab")
    assert (warnings["LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE"]["field"], warnings["LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE"]["reason"]) == ("tolerance", "expected a number")
    assert (warnings[ALIAS_API_KEY]["field"], warnings[ALIAS_API_KEY]["reason"]) == ("api_key", "too short: at least 8 characters")
    assert warnings[DERIVED_REGION]["field"] == "region" and DERIVED_REGION + "_FILE" in warnings[DERIVED_REGION]["reason"]
    assert number not in repr(logs) and short_secret not in repr(logs)
    print_success("three variables, three warnings, no value")


# -----------------------------------------------------------------------------
# An unusable instance key: the stored secrets are unreadable, nothing raises
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("decrypt", [False, True], ids=["for-the-catalogue", "for-a-call"])
def test_with_an_unusable_key_every_stored_secret_is_unreadable_and_nothing_raises(decrypt: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_environment: Path):
    """3: «set but unreadable», the plain values as they are, one error in the log, and no key file made in its place."""
    print_section(f"3: an unusable instance key, {'a call' if decrypt else 'the catalogue'}")
    system = {"api_key": _secret_row(_marker(), "api_key"), "region": _plain("us")}
    user = {"token": _secret_row(_marker(), "token", "user", 1), "limit": _plain(7)}
    _make_the_key_unusable(monkeypatch, tmp_path)

    with capture_logs() as logs:
        first = _resolve(system, user, decrypt=decrypt)
        _resolve(system, user, decrypt=decrypt)

    assert _summary(first["api_key"]) == ("db", None, True, False, None, "unreadable")
    assert _summary(first["token"]) == ("db", None, True, False, None, "unreadable")
    assert (first["region"].value, first["limit"].value) == ("us", 7)
    errors = [entry for entry in logs if entry["event"].startswith("Plugin secrets unreadable: the instance key cannot be used")]
    assert [entry["log_level"] for entry in errors] == ["error"], f"one error per process: {logs}"
    assert not (isolated_environment / "secrets").exists(), "an unusable configured key is never replaced by a generated one"
    print_success("secrets unreadable, plain values delivered, one error")


def test_with_an_unusable_key_the_environments_secrets_still_reach_a_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """3: a secret from the environment needs no key: delivered; its fingerprint is made without the key, never of the value."""
    secret = _marker()
    rows = _configured_rows()
    _make_the_key_unusable(monkeypatch, tmp_path)
    monkeypatch.setenv(ALIAS_API_KEY, secret)

    bound = build_bound_settings("asset", "lab", LAB_FIELDS, rows, None, user_id=None)

    assert bound.secret("api_key") == secret and bound.missing == ()
    assert len(bound.fingerprint) == 32 and secret not in bound.fingerprint


def test_with_an_unusable_key_a_required_stored_secret_leaves_the_plugin_not_configured(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    rows = _configured_rows()
    _make_the_key_unusable(monkeypatch, tmp_path)

    bound = build_bound_settings("asset", "lab", LAB_FIELDS, rows, None, user_id=None)

    assert bound.missing == ("api_key",) and bound.secret("api_key") is None


def test_without_a_usable_key_the_fingerprint_takes_the_secret_names_never_their_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """3: a SHA-256 of the plain values and the sorted secret names: the same for any value of a secret, unlike the keyed HMAC."""
    plain = {"region": "eu"}
    keyed = settings_fingerprint(plain, {"api_key": "first-secret-value"})
    _make_the_key_unusable(monkeypatch, tmp_path)

    first = settings_fingerprint(plain, {"api_key": "first-secret-value"})
    second = settings_fingerprint(plain, {"api_key": "another-secret-value"})
    two = settings_fingerprint(plain, {"api_key": "x-secret-value", "token": "y-secret-value"})
    two_reversed = settings_fingerprint(plain, {"token": "z-secret-value", "api_key": "w-secret-value"})
    others = {
        "keyed": keyed,
        "another plain value": settings_fingerprint({"region": "us"}, {"api_key": "first-secret-value"}),
        "another secret name": settings_fingerprint(plain, {"token": "first-secret-value"}),
        "no secret": settings_fingerprint(plain, {}),
        "two secrets": two,
    }

    assert first == second, "the value of a secret never shows in, nor changes, the fingerprint"
    assert two == two_reversed, "the names are sorted"
    assert len({first, *others.values()}) == len(others) + 1, f"each of these must differ from the others and from {first}: {others}"
    assert len(first) == 32 and "first-secret-value" not in first


# =============================================================================
# 4. DELIVERY: configure_instance
# =============================================================================


@pytest_asyncio.fixture
async def private_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema, opened as production opens its own; disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def users(private_engine: AsyncEngine) -> dict[str, int]:
    async with AsyncSession(private_engine, expire_on_commit=False) as session:
        created = {name: User(username=name, email=f"{name}@example.test", hashed_password="$argon2id$test") for name in ("alice", "bob")}
        session.add_all(created.values())
        await session.commit()
    return {name: user.id for name, user in created.items()}


@pytest.fixture
def through_private_engine(private_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """``configure_instance`` reads its rows through the private engine; the list counts the reads."""
    reads: list[int] = []

    def engine() -> AsyncEngine:
        reads.append(1)
        return private_engine

    monkeypatch.setattr(runtime, "get_async_engine", engine)
    return reads


def _no_database() -> AsyncEngine:
    raise AssertionError("the database was reached: a plugin without fields to read must not open a session")


def _nothing_to_resolve(*_args: object, **_kwargs: object) -> BoundSettings:
    raise AssertionError("the fields were resolved: an object that declares none has nothing to resolve or bind")


def _hand_out(monkeypatch: pytest.MonkeyPatch, registry: type, code: str, double: object) -> None:
    """``registry`` hands ``double`` out for ``code`` — on the class itself, as the suites patch it — and nothing else."""
    monkeypatch.setattr(registry, "get_provider_instance", classmethod(lambda _cls, requested, **_kwargs: double if requested == code else None))


def _system(code: str, key: str, *, value: object = None, secret: str | None = None, family: str = "asset") -> PluginSystemSetting:
    if secret is None:
        return PluginSystemSetting(family=family, plugin_code=code, field_key=key, value_json=json.dumps(value))
    subkey = settings_subkey()
    return PluginSystemSetting(family=family, plugin_code=code, field_key=key, secret_ciphertext=encrypt_secret(subkey, secret_aad(family, code, key, "system", None), secret), key_id=key_id_of(subkey))


def _user(user_id: int, code: str, key: str, *, value: object = None, secret: str | None = None, family: str = "asset") -> PluginUserSetting:
    if secret is None:
        return PluginUserSetting(user_id=user_id, family=family, plugin_code=code, field_key=key, value_json=json.dumps(value))
    subkey = settings_subkey()
    return PluginUserSetting(user_id=user_id, family=family, plugin_code=code, field_key=key, secret_ciphertext=encrypt_secret(subkey, secret_aad(family, code, key, "user", user_id), secret), key_id=key_id_of(subkey))


async def _store(engine: AsyncEngine, *rows) -> None:
    async with AsyncSession(engine) as session:
        session.add_all(rows)
        await session.commit()


@pytest_asyncio.fixture
async def lab_rows(private_engine: AsyncEngine, users: dict[str, int]) -> dict[str, str]:
    """The lab plugin's rows, and decoys: the same keys for another plugin, the FX family, another user."""
    alice, bob = users["alice"], users["bob"]
    secrets = {"api_key": _marker(), "alice_token": _marker(), "decoy": _marker()}
    await _store(
        private_engine,
        _system("lab", "region", value="us"),
        _system("lab", "api_key", secret=secrets["api_key"]),
        _system("lab", "endpoint", value="https://api.example/v1"),
        _user(alice, "lab", "limit", value=7),
        _user(alice, "lab", "token", secret=secrets["alice_token"]),
        _user(bob, "lab", "limit", value=9),
        _system("other", "region", value="jp"),
        _system("lab", "region", value="uk", family="fx"),
        _user(alice, "other", "limit", value=42),
        _user(alice, "lab", "limit", value=43, family="fx"),
        _system("other", "api_key", secret=secrets["decoy"]),
    )
    return secrets


@pytest.mark.asyncio
async def test_read_plugin_rows_returns_that_plugins_rows_and_that_users_only(private_engine: AsyncEngine, users: dict[str, int], lab_rows: dict[str, str]):
    """4: by family and code; the user rows of the user asked for, ``None`` without one."""
    async with AsyncSession(private_engine) as session:
        system, alices = await runtime.read_plugin_rows(session, "asset", "lab", users["alice"])
        _system_again, nobodys = await runtime.read_plugin_rows(session, "asset", "lab", None)

    assert set(system) == {"region", "api_key", "endpoint"}
    assert json.loads(system["region"].value_json) == "us"
    assert set(alices) == {"limit", "token"} and json.loads(alices["limit"].value_json) == 7
    assert nobodys is None


@pytest.mark.asyncio
async def test_configure_instance_delivers_the_instances_values_and_the_users_own(users: dict[str, int], lab_rows: dict[str, str], through_private_engine: list[int]):
    """4: alice gets her limit and token, bob his limit and no token, a call for nobody the defaults; the system values to all."""
    print_section("4: configure_instance by user")
    alice = await runtime.configure_instance(_LabPlugin(), "asset", user_id=users["alice"])
    bob = await runtime.configure_instance(_LabPlugin(), "asset", user_id=users["bob"])
    nobody = await runtime.configure_instance(_LabPlugin(), "asset")

    for instance in (alice, bob, nobody):
        assert (instance.settings.get("region"), instance.settings.get("endpoint"), instance.settings.secret("api_key")) == ("us", "https://api.example/v1", lab_rows["api_key"])
        assert instance.settings.missing == ()
    assert (alice.settings.get("limit"), alice.settings.secret("token")) == (7, lab_rows["alice_token"])
    assert (bob.settings.get("limit"), bob.settings.secret("token")) == (9, None)
    assert (nobody.settings.get("limit"), nobody.settings.secret("token")) == (10, None)
    assert len({alice.settings.fingerprint, bob.settings.fingerprint, nobody.settings.fingerprint}) == 3, "different values, different fingerprints"
    assert len(through_private_engine) == 3, "one short session per configured instance"
    print_success("each user gets their own values, nobody gets the defaults")


@pytest.mark.asyncio
async def test_a_plugin_without_fields_is_returned_untouched_without_the_database(monkeypatch: pytest.MonkeyPatch):
    """4: no field, no session: the same instance, nothing bound, an empty fingerprint."""
    monkeypatch.setattr(runtime, "get_async_engine", _no_database)
    bare = _BarePlugin()

    configured = await runtime.configure_instance(bare, "asset", user_id=1)

    assert configured is bare and bare._lf_bound_settings is None
    assert configured.settings.fingerprint == "" and asset_core.settings_cache_part(configured) == ""


@pytest.mark.asyncio
async def test_an_object_without_settings_fields_is_handed_back_untouched_without_the_database(monkeypatch: pytest.MonkeyPatch):
    """4, regression: a double of the suites — no mixin, no ``settings_fields`` attribute at all — made ``configure_instance``
    raise ``AttributeError``. ``configure_instance``, ``configured_provider`` (with or without a user) and
    ``configured_fx_provider`` hand it back as it is: the very object, nothing set on it, no session, nothing resolved."""
    print_section("4: a double without settings_fields, handed back untouched")
    assert not hasattr(_SuiteDouble, "settings_fields") and not issubclass(_SuiteDouble, PluginSettingsMixin), "the shape of the regression"
    monkeypatch.setattr(runtime, "get_async_engine", _no_database)
    monkeypatch.setattr(runtime, "build_bound_settings", _nothing_to_resolve)
    # Both traps stand on the path: an object that does declare fields walks into them.
    with pytest.raises(AssertionError, match="the database was reached"):
        await runtime.configure_instance(_LabPlugin(), "asset")
    with pytest.raises(AssertionError, match="the fields were resolved"):
        await runtime.configure_instance(_UserOnlyPlugin(), "asset")
    direct, asset_double, fx_double = _SuiteDouble(), _SuiteDouble(), _SuiteDouble()
    _hand_out(monkeypatch, AssetProviderRegistry, "suite_double", asset_double)
    _hand_out(monkeypatch, FXProviderRegistry, "SUITE_DOUBLE", fx_double)

    assert await runtime.configure_instance(direct, "asset", user_id=1) is direct
    assert await runtime.configure_instance(direct, "fx") is direct
    assert await asset_core.configured_provider("suite_double") is asset_double
    assert await asset_core.configured_provider("suite_double", user_id=1) is asset_double
    assert await fx_runtime.configured_fx_provider("SUITE_DOUBLE") is fx_double
    assert vars(direct) == vars(asset_double) == vars(fx_double) == {}, "nothing bound or set on a double"
    assert await asset_core.settings_cache_part_for("suite_double") == fx_runtime.settings_cache_part(fx_double) == "", "no settings, no part in the cache keys"
    print_success("the very object back, nothing bound, no session opened, nothing resolved")


@pytest.mark.asyncio
async def test_a_plugin_with_user_fields_only_reads_nothing_without_a_user(monkeypatch: pytest.MonkeyPatch):
    """4: a scheduled call of a plugin whose fields are all personal: the defaults, without opening a session."""
    monkeypatch.setattr(runtime, "get_async_engine", _no_database)

    configured = await runtime.configure_instance(_UserOnlyPlugin(), "asset")

    assert configured.settings.get("limit") == 3 and configured.settings.fingerprint != ""


@pytest.mark.asyncio
async def test_a_database_error_leaves_the_environment_and_the_defaults_and_logs_a_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """4: the rows cannot be read (here a database without the tables): the call still gets env and defaults; a warning, no value."""
    print_section("4: configure_instance on a database error")
    broken = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'no-tables.db'}", poolclass=NullPool)
    monkeypatch.setattr(runtime, "get_async_engine", lambda: broken)
    secret = _marker()
    monkeypatch.setenv("LIBREFOLIO_LAB_API_KEY", secret)
    monkeypatch.setenv(DERIVED_REGION, "jp")
    try:
        with capture_logs() as logs:
            configured = await runtime.configure_instance(_LabPlugin(), "asset", user_id=1)
    finally:
        await broken.dispose()

    assert (configured.settings.get("region"), configured.settings.secret("api_key"), configured.settings.get("limit")) == ("jp", secret, 10)
    assert configured.settings.missing == ("endpoint",)
    warnings = [entry for entry in logs if entry["event"].startswith("Plugin settings not read")]
    assert len(warnings) == 1 and warnings[0]["log_level"] == "warning", logs
    assert (warnings[0]["family"], warnings[0]["plugin"], warnings[0]["error"]) == ("asset", "lab", "OperationalError")
    assert secret not in repr(logs)
    print_success("env and defaults delivered, one warning naming the error type only")


@pytest.mark.asyncio
async def test_configured_provider_hands_mockprov_the_users_settings_through_the_boundary(users: dict[str, int], private_engine: AsyncEngine, through_private_engine: list[int]):
    """4: the real mockprov, configured for alice, answers the echo query with her values and the instance's."""
    print_section("4: mockprov configured for a user")
    await _store(
        private_engine,
        _system("mockprov", "region", value="us"),
        _system("mockprov", "api_key", secret=_marker()),
        _user(users["alice"], "mockprov", "results_limit", value=5),
        _user(users["alice"], "mockprov", "personal_token", secret=_marker()),
    )

    alices = await asset_core.configured_provider("mockprov", user_id=users["alice"])
    bobs = await asset_core.configured_provider("mockprov", user_id=users["bob"])
    alice_echo = await asset_core.call_provider(alices, lambda: alices.search(SETTINGS_ECHO_QUERY), timeout=10)
    bob_echo = await asset_core.call_provider(bobs, lambda: bobs.search(SETTINGS_ECHO_QUERY), timeout=10)

    common = "api_key=set; region=us; price_tolerance=0.5; verbose=False; preferred_language=all"
    assert [item["display_name"] for item in alice_echo] == [f"settings: {common}; results_limit=5; personal_token=set"]
    assert [item["display_name"] for item in bob_echo] == [f"settings: {common}; results_limit=10; personal_token=unset"]
    assert await asset_core.configured_provider("no_such_provider") is None
    print_success("alice's limit and token reach mockprov; bob gets the defaults")


@pytest.mark.asyncio
async def test_the_settings_part_of_a_cache_key_follows_the_instances_values_only(users: dict[str, int], private_engine: AsyncEngine, through_private_engine: list[int]):
    """4: ``settings_cache_part_for`` (no user): a user's row changes nothing, a system row changes it; an unknown code gives ''."""
    before = await asset_core.settings_cache_part_for("mockprov")
    await _store(private_engine, _user(users["alice"], "mockprov", "results_limit", value=5))
    after_user_row = await asset_core.settings_cache_part_for("mockprov")
    await _store(private_engine, _system("mockprov", "verbose", value=True))
    after_system_row = await asset_core.settings_cache_part_for("mockprov")

    assert before and after_user_row == before
    assert after_system_row != before
    assert await asset_core.settings_cache_part_for("no_such_provider") == ""


@pytest.mark.asyncio
async def test_configured_fx_provider_gets_the_instances_values(private_engine: AsyncEngine, through_private_engine: list[int]):
    """4: MOCKFX with its two system rows: the integer and the decrypted secret; its cache part their fingerprint."""
    secret = _marker()
    default = await fx_runtime.configured_fx_provider("MOCKFX")
    await _store(private_engine, _system("MOCKFX", "decimals", value=3, family="fx"), _system("MOCKFX", "api_key", secret=secret, family="fx"))

    configured = await fx_runtime.configured_fx_provider("MOCKFX")

    assert default.settings.get("decimals") == 6 and default.settings.secret("api_key") is None
    assert (configured.settings.get("decimals"), configured.settings.secret("api_key")) == (3, secret)
    assert fx_runtime.settings_cache_part(configured) == configured.settings.fingerprint != fx_runtime.settings_cache_part(default)
    assert await fx_runtime.configured_fx_provider("NO_SUCH_FX") is None


# =============================================================================
# 5. THE BOUNDARIES
# =============================================================================


def _bound_lab(*, api_key: str | None, endpoint: str | None = "https://api.example") -> _LabPlugin:
    """A lab instance with these values bound, as the core would bind them."""
    plain = {"region": "eu"} | ({"endpoint": endpoint} if endpoint else {})
    secrets = {"api_key": api_key} if api_key else {}
    missing = tuple(key for key, value in (("api_key", api_key), ("endpoint", endpoint)) if not value)
    instance = _LabPlugin()
    instance.bind_settings(BoundSettings(LAB_FIELDS, plain, secrets, missing, fingerprint="f" * 32))
    return instance


class _Spy:
    """``fn`` of a boundary: records whether it was called, then runs ``body``."""

    def __init__(self, body: Callable):
        self.calls = 0
        self.body = body

    def __call__(self):
        self.calls += 1
        return self.body()


async def _returns(value):
    return value


@pytest.mark.asyncio
async def test_call_provider_refuses_an_unconfigured_plugin_before_calling_it():
    """5: ``NOT_CONFIGURED`` with the missing keys in ``details``, and ``fn`` never called: no I/O happened."""
    spy = _Spy(lambda: _returns("reached"))

    with pytest.raises(AssetSourceError) as refused:
        await asset_core.call_provider(_bound_lab(api_key=None, endpoint=None), spy, timeout=5)

    assert refused.value.error_code == "NOT_CONFIGURED" and refused.value.details == {"missing": ["api_key", "endpoint"]}
    assert spy.calls == 0


@pytest.mark.asyncio
async def test_fx_call_refuses_an_unconfigured_plugin_before_calling_it():
    spy = _Spy(lambda: _returns("reached"))

    with pytest.raises(FXNotConfiguredError) as refused:
        await fx_runtime.call_fx_provider(_bound_lab(api_key=None), spy)

    assert isinstance(refused.value, FXServiceError), "the FX legs handle FXServiceError: a refused provider is one of them"
    assert (refused.value.provider_code, refused.value.missing) == ("lab", ["api_key"])
    assert spy.calls == 0


@pytest.mark.asyncio
async def test_an_invalid_variable_refuses_the_call_at_both_boundaries(monkeypatch: pytest.MonkeyPatch):
    """5: an optional field whose variable is invalid: ``NOT_CONFIGURED`` listing it, before ``fn``, asset and FX alike."""
    print_section("5: an invalid variable at the boundaries")
    monkeypatch.setenv("LIBREFOLIO_PLUGIN_ASSET_LAB_VERBOSE", "maybe")
    instance = _LabPlugin()
    instance.bind_settings(build_bound_settings("asset", "lab", LAB_FIELDS, _configured_rows(), None, user_id=None))
    spy = _Spy(lambda: _returns("reached"))

    with pytest.raises(AssetSourceError) as asset_refusal:
        await asset_core.call_provider(instance, spy, timeout=5)
    with pytest.raises(FXNotConfiguredError) as fx_refusal:
        await fx_runtime.call_fx_provider(instance, spy)

    assert (asset_refusal.value.error_code, asset_refusal.value.details) == ("NOT_CONFIGURED", {"missing": ["verbose"]})
    assert fx_refusal.value.missing == ["verbose"]
    assert spy.calls == 0
    print_success("NOT_CONFIGURED [verbose], fn never called")


@pytest.mark.asyncio
async def test_during_an_asset_call_the_secret_is_in_flight_in_the_providers_thread():
    """5: the provider runs in a thread of its own with its own loop; its secrets are in flight there, and only there."""
    secret = _marker()
    seen: dict[str, object] = {}

    async def body():
        seen["in_flight"] = active_secrets()
        seen["masked"] = mask_text(f"GET /q?apikey={secret}")
        return "answer"

    result = await asset_core.call_provider(_bound_lab(api_key=secret), lambda: body(), timeout=5)

    assert result == "answer"
    assert seen == {"in_flight": frozenset({secret}), "masked": f"GET /q?apikey={MASK}"}
    assert active_secrets() == frozenset(), "the secret must be in flight for the call only"


@pytest.mark.asyncio
async def test_an_error_an_asset_plugin_raises_reaches_the_caller_masked():
    """5: message, ``details`` (the URL-encoded form too), ``str()`` and the cause: masked in place; the very error, type and code kept."""
    print_section("5: call_provider masks the plugin's error")
    secret = _marker() + " /+"
    raised_by_the_plugin: list[BaseException] = []

    async def body():
        try:
            raise ConnectionError(f"https://api.example/q?apikey={quote(secret, safe='')} refused")
        except ConnectionError as cause:
            error = AssetSourceError(f"401 for key {secret}", "AUTH_FAILED", {"url": f"https://api.example/q?apikey={quote(secret, safe='')}", "key": secret})
            raised_by_the_plugin.append(error)
            raise error from cause

    with pytest.raises(AssetSourceError) as raised:
        await asset_core.call_provider(_bound_lab(api_key=secret), lambda: body(), timeout=5)

    error = raised.value
    assert error is raised_by_the_plugin[0], "an error masked in place is re-raised as it is, not replaced"
    assert error.error_code == "AUTH_FAILED"
    texts = [str(error), error.message, json.dumps(error.details), str(error.__cause__)]
    assert all(secret not in text and quote(secret, safe="") not in text for text in texts), texts
    assert error.message == f"401 for key {MASK}" and error.details == {"url": f"https://api.example/q?apikey={MASK}", "key": MASK}
    print_success("the caller sees ***, in the message, the details and the cause")


@pytest.mark.asyncio
async def test_an_error_an_fx_plugin_raises_reaches_the_caller_masked():
    secret = _marker()

    async def body():
        raise FXServiceError(f"ECB-like failure with token {secret}")

    with pytest.raises(FXServiceError) as raised:
        await fx_runtime.call_fx_provider(_bound_lab(api_key=secret), body)

    assert str(raised.value) == f"ECB-like failure with token {MASK}"
    assert active_secrets() == frozenset()


@pytest.mark.asyncio
async def test_an_fx_call_has_its_secret_in_flight_and_returns_its_result():
    secret = _marker()

    async def body():
        return active_secrets()

    assert await fx_runtime.call_fx_provider(_bound_lab(api_key=secret), body) == frozenset({secret})


@pytest.mark.asyncio
async def test_an_object_that_is_not_a_plugin_goes_through_unchecked():
    """5: a test double: no settings to check, nothing to mask; ``fn`` is called and its result returned, asset and FX."""
    asset_spy, fx_spy = _Spy(lambda: _returns("asset answer")), _Spy(lambda: _returns("fx answer"))

    assert await asset_core.call_provider(_NotAPlugin(), asset_spy, timeout=5) == "asset answer"
    assert await fx_runtime.call_fx_provider(_NotAPlugin(), fx_spy) == "fx answer"
    assert (asset_spy.calls, fx_spy.calls) == (1, 1)


@pytest.mark.asyncio
async def test_an_unbound_plugin_with_a_required_field_is_refused_too():
    """5: an instance nobody configured has its defaults and no secret: a required secret makes it NOT_CONFIGURED."""
    with pytest.raises(AssetSourceError) as refused:
        await asset_core.call_provider(_LabPlugin(), lambda: _returns("reached"), timeout=5)

    assert refused.value.details["missing"] == ["api_key", "endpoint"]


# -----------------------------------------------------------------------------
# What masking cannot rewrite is replaced; what it can keeps its identity
# -----------------------------------------------------------------------------


def _assert_replaced(error: BaseException, secret: str, original: BaseException) -> None:
    """A boundary's replacement: the masked description of the original, no secret, no link to the original."""
    assert masked_description(original, frozenset({secret})) in str(error), f"the replacement must carry the masked description: {error}"
    assert secret not in str(error) and not exception_renders_secret(error, frozenset({secret}))
    assert error.__cause__ is None and error.__context__ is None, "the replacement keeps no link to the error that still shows the secret"


@pytest.mark.asyncio
async def test_an_asset_error_that_still_shows_a_secret_is_replaced_by_provider_error():
    """5: a ``__str__`` over ``__slots__`` survives masking: the caller gets ``AssetSourceError`` ``PROVIDER_ERROR`` instead."""
    print_section("5: call_provider replaces an error it cannot mask")
    secret = _marker()

    async def body():
        raise _SlotsLeak(secret)

    with pytest.raises(AssetSourceError) as raised:
        await asset_core.call_provider(_bound_lab(api_key=secret), lambda: body(), timeout=5)

    assert type(raised.value) is AssetSourceError and raised.value.error_code == "PROVIDER_ERROR" and raised.value.details == {}
    assert "lab" in raised.value.message, "the replacement names the provider"
    _assert_replaced(raised.value, secret, _SlotsLeak(secret))
    print_success(f"replaced: {raised.value}")


@pytest.mark.asyncio
async def test_an_fx_error_that_still_shows_a_secret_is_replaced_by_an_fx_service_error():
    secret = _marker()

    async def body():
        raise _SlotsLeak(secret)

    with pytest.raises(FXServiceError) as raised:
        await fx_runtime.call_fx_provider(_bound_lab(api_key=secret), body)

    assert type(raised.value) is FXServiceError
    _assert_replaced(raised.value, secret, _SlotsLeak(secret))


@pytest.mark.asyncio
async def test_an_exception_group_whose_own_message_shows_a_secret_is_replaced():
    """5: a group's message is read-only: its members get masked, the group itself is replaced."""
    secret = _marker()

    def group() -> ExceptionGroup:
        return ExceptionGroup(f"calls with key {secret} failed", [ValueError(f"first {secret}")])

    async def body():
        raise group()

    with pytest.raises(AssetSourceError) as raised:
        await asset_core.call_provider(_bound_lab(api_key=secret), lambda: body(), timeout=5)

    assert raised.value.error_code == "PROVIDER_ERROR"
    _assert_replaced(raised.value, secret, group())


@pytest.mark.parametrize("boundary", ["asset", "fx"])
@pytest.mark.asyncio
async def test_an_error_masked_in_place_is_the_very_error_the_plugin_raised(boundary: str):
    """5: a ``__str__`` over a normal attribute comes out masked: same object, same type, nothing replaced."""
    secret = _marker()
    raised_by_the_plugin: list[BaseException] = []

    async def body():
        error = _AttributeLeak(secret)
        raised_by_the_plugin.append(error)
        raise error

    with pytest.raises(_AttributeLeak) as raised:
        if boundary == "asset":
            await asset_core.call_provider(_bound_lab(api_key=secret), lambda: body(), timeout=5)
        else:
            await fx_runtime.call_fx_provider(_bound_lab(api_key=secret), body)

    assert raised.value is raised_by_the_plugin[0]
    assert str(raised.value) == f"failed with {MASK}"


@pytest.mark.asyncio
async def test_a_base_exception_that_is_no_exception_is_never_replaced_at_the_asset_boundary():
    """5: only an ``Exception`` is replaced: a ``BaseException`` (an interruption) keeps its identity and propagates."""
    secret = _marker()
    raised_by_the_plugin: list[BaseException] = []

    async def body():
        error = _SlotsHalt(secret)
        raised_by_the_plugin.append(error)
        raise error

    with pytest.raises(_SlotsHalt) as raised:
        await asset_core.call_provider(_bound_lab(api_key=secret), lambda: body(), timeout=5)

    assert raised.value is raised_by_the_plugin[0]
    assert exception_renders_secret(raised.value, frozenset({secret})), "barrier: it still shows the secret, so only the rule kept it from being replaced"


@pytest.mark.asyncio
async def test_a_cancellation_is_never_replaced_at_the_fx_boundary():
    secret = _marker()
    raised_by_the_plugin: list[BaseException] = []

    async def body():
        error = _SlotsCancelled(secret)
        raised_by_the_plugin.append(error)
        raise error

    with pytest.raises(_SlotsCancelled) as raised:
        await fx_runtime.call_fx_provider(_bound_lab(api_key=secret), body)

    assert raised.value is raised_by_the_plugin[0]
    assert exception_renders_secret(raised.value, frozenset({secret}))
