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
   the secrets, the required fields left without a usable value, and that fingerprint. ``missing_field_keys`` is the one
   rule of «not configured», for a call (``build_bound_settings``) and for the catalogue (``configured``): a field is
   missing when it is required without a usable value — a secret resolved for the catalogue carries no value and is
   usable when it is set and readable — or when its variable is invalid, required or not; a default, the one standing
   in for a refused row included, is usable. The same rows give a call and the catalogue the same missing fields, a
   blob the current key cannot decrypt under the current key id aside: the catalogue never decrypts.
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
   ``AssetSourceError`` ``PROVIDER_ERROR`` / ``FXServiceError`` carrying its masked description (the asset error in its
   message and in ``details["detail"]``, decision N6) and no ``__cause__`` or ``__context__``, while a ``BaseException``
   that is no ``Exception`` (a cancellation) is never replaced; an object that is not a plugin goes through unchecked.
   **A secret the caller chose** (N15, security review of CP10–CP11): ``BoundSettings.carries_user_secrets`` is true
   when a non-empty secret of a ``user`` field is bound — never for a system secret, an empty value, a user's plain
   values, or an instance nobody configured. Then the asset boundary hides whole, ``***``, every text of the error that
   shows a secret — arguments, ``message``, details, cause and context — instead of masking it in place; the type,
   ``error_code`` and the very object stay, and a replaced error is described as ``Type: ***``. mockprov, whose error
   echoes a known context and its instance key, called with a personal token made of that context and a guess of the
   key's first character, raises the same error for a wrong guess and for the right one. Without a secret of the
   caller's own the masking in place stays as above.
6. **Search** (``AssetSearchService``): the plain search lists the providers refused with ``NOT_CONFIGURED`` in
   ``providers_not_configured``, in the order of the query, each in ``providers_with_errors`` too, and never calls them;
   a provider failing with another code is an error only, one answering is in neither list. The SSE ``provider_error``
   event of a provider not configured carries ``error_code: NOT_CONFIGURED`` beside its message and nothing else, and
   the refusal is logged at INFO, never as a warning. These providers are lab plugins the asset registry hands out for
   codes of their own, configured for real through the private engine: a required field without a value.
7. **The asset URL** (``public_asset_url``): a URL that shows a bound secret, the instance's or the caller's, as written
   or URL-encoded, is withheld whole — ``None``, never a masked URL — with one warning naming the provider, never the
   URL or the secret; any other URL, and the URL of an object that is not a plugin, comes back as it is, nothing
   logged. The probe (``probe_provider_config``) computes ``provider_url`` through it: mockprov's ``get_asset_url``
   (patched with ``monkeypatch``) putting a secret in the URL gives ``provider_url`` ``None``, the rest of the probe
   answering.

**X-R43** (workstream X): an integer past the double range no longer breaks a resolution: a variable holding one for an
integer field is ``invalid_env`` («too large», logged without the value), a stored row holding one, for an integer or a
number field, ``invalid_stored``. «Red today» is the state before the cure; a guard passes before and after.

Pure: the rows live in a private SQLite file under ``tmp_path`` (``create_all``), reached through a private engine put
in place of ``runtime.get_async_engine``; the instance key is a test key set with ``monkeypatch`` and the data
directory points into ``tmp_path``; every variable a test sets goes through ``monkeypatch``; a search asks a query of
its own, so the process's search caches answer for no other test. Every plugin a test binds is a new instance, and a
method patched on mockprov's class goes through ``monkeypatch``.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import random
import sys
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, quote_plus

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.schemas.provider import FAProviderConfigBase, ProbeOperation
from backend.app.services.asset_source_providers.mockprov.plugin import SETTINGS_ECHO_QUERY, MockProvider
from backend.app.services.assets import core as asset_core
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.provider_management import ProviderManagementOperations
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.assets.search import AssetSearchService
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx.base import FXNotConfiguredError, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.plugin_settings import resolver, runtime
from backend.app.services.plugin_settings.contract import BoundSettings, PluginSettingsMixin
from backend.app.services.plugin_settings.crypto import encrypt_secret, fingerprint_subkey, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, env_name, env_variables
from backend.app.services.plugin_settings.resolver import FieldState, StoredValue, build_bound_settings, missing_field_keys, resolve_plugin_fields, settings_fingerprint
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

#: The lab plugin's fields for the rule of «not configured»: a required field of each kind — a secret, a text, a select
#: with a default, a user's secret — and an optional number. The same keys as LAB_FIELDS, so the same variables.
RULE_FIELDS = (
    PluginSettingField(key="api_key", type=STRING, scope=SYSTEM, label="API key", secret=True, required=True, env="LIBREFOLIO_LAB_API_KEY"),
    PluginSettingField(key="endpoint", type=STRING, scope=SYSTEM, label="Endpoint", required=True),
    PluginSettingField(key="region", type=SELECT, scope=SYSTEM, label="Region", required=True, default="eu", options=tuple(SettingOption(value, value.upper()) for value in REGIONS)),
    PluginSettingField(key="tolerance", type=NUMBER, scope=SYSTEM, label="Tolerance", default=0.5, minimum=0, maximum=10),
    PluginSettingField(key="token", type=STRING, scope=USER, label="Token", secret=True, required=True),
)

#: The searchable lab plugins: two never configured (a required field without a value), one failing on its own.
UNCONFIGURED_FIRST, UNCONFIGURED_SECOND, FAILING = "lab_unconfigured_b", "lab_unconfigured_a", "lab_failing"
SEARCH_LAB_FIELDS = (PluginSettingField(key="endpoint", type=STRING, scope=SYSTEM, label="Endpoint", required=True),)


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


class _UnconfiguredSearch(MockProvider):
    """A searchable asset plugin of the tests — mockprov's search — whose one field is required and never set."""

    settings_fields = SEARCH_LAB_FIELDS
    lab_code = UNCONFIGURED_FIRST

    @property
    def provider_code(self) -> str:
        return self.lab_code


class _UnconfiguredSearchToo(_UnconfiguredSearch):
    lab_code = UNCONFIGURED_SECOND


class _FailingSearch(MockProvider):
    """A searchable asset plugin of the tests, without settings, whose search fails with an error code of its own."""

    settings_fields = ()

    @property
    def provider_code(self) -> str:
        return FAILING

    async def search(self, query: str) -> list[dict]:
        raise AssetSourceError(f"the search backend is down for {query!r} (testing)", "SEARCH_ERROR")


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
    """The test key A as the instance key, a data directory of this test, and no ambient variable of the lab, the searchable labs, mockprov or MOCKFX fields."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(data_dir))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    declared = [("asset", "lab", field) for field in (*LAB_FIELDS, *RULE_FIELDS)] + [("asset", "mockprov", field) for field in MockProvider.settings_fields] + [("fx", "MOCKFX", field) for field in MockFXProvider.settings_fields]
    declared += [("asset", code, field) for code in (UNCONFIGURED_FIRST, UNCONFIGURED_SECOND) for field in SEARCH_LAB_FIELDS]
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
# The rule of «not configured»: missing_field_keys, for a call and for the catalogue
# -----------------------------------------------------------------------------

#: How a row of ``_rule_rows`` changes: dropped, a secret written under another key, a secret moved from another user.
NO_ROW, UNDER_ANOTHER_KEY, FROM_ANOTHER_USER = "no row", "under another key", "from another user"


def _rule_field(key: str) -> PluginSettingField:
    return next(field for field in RULE_FIELDS if field.key == key)


def _rule_rows(system_changes: dict[str, object], user_changes: dict[str, object]) -> tuple[dict[str, StoredValue], dict[str, StoredValue]]:
    """Rows that configure RULE_FIELDS for user 1, then the changes: ``NO_ROW`` drops a row, ``UNDER_ANOTHER_KEY`` and
    ``FROM_ANOTHER_USER`` write the secret so that this key cannot read it, any other value is a plain row."""
    system = {"api_key": _secret_row(_marker(), "api_key"), "endpoint": _plain("https://api.example"), "region": _plain("us")}
    user = {"token": _secret_row(_marker(), "token", "user", 1)}
    for rows, changes, scope in ((system, system_changes, "system"), (user, user_changes, "user")):
        owner = 1 if scope == "user" else None
        for key, change in changes.items():
            if change == NO_ROW:
                rows.pop(key, None)
            elif change == UNDER_ANOTHER_KEY:
                rows[key] = _secret_row(_marker(), key, scope, owner, subkey=FOREIGN_SUBKEY)
            elif change == FROM_ANOTHER_USER:
                rows[key] = _secret_row(_marker(), key, scope, 2)
            else:
                rows[key] = _plain(change)
    return system, user


@pytest.mark.parametrize(
    ("variables", "system_changes", "user_changes", "missing"),
    [
        pytest.param({}, {}, {}, (), id="every-required-field-set-by-a-row"),
        pytest.param({}, dict.fromkeys(("api_key", "endpoint", "region"), NO_ROW), {"token": NO_ROW}, ("api_key", "endpoint", "token"), id="nothing-set-the-select-on-its-default"),
        pytest.param({ALIAS_API_KEY: "lf-a-secret-from-the-alias"}, {"api_key": NO_ROW}, {}, (), id="a-required-secret-set-by-a-variable"),
        pytest.param({}, {"api_key": UNDER_ANOTHER_KEY}, {}, ("api_key",), id="a-required-secret-another-key-wrote"),
        pytest.param({}, {}, {"token": UNDER_ANOTHER_KEY}, ("token",), id="a-required-user-secret-another-key-wrote"),
        pytest.param({}, {"endpoint": NO_ROW}, {}, ("endpoint",), id="a-required-field-with-nothing"),
        pytest.param({}, {"endpoint": ""}, {}, ("endpoint",), id="a-required-field-whose-row-is-refused-without-a-default"),
        pytest.param({}, {"region": NO_ROW}, {}, (), id="a-required-select-on-its-default"),
        pytest.param({}, {"region": "xx"}, {}, (), id="a-required-select-whose-row-is-refused-falls-back-to-its-default"),
        pytest.param({"LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE": "abc"}, {}, {}, ("tolerance",), id="an-optional-field-whose-variable-is-invalid"),
        pytest.param({"LIBREFOLIO_PLUGIN_ASSET_LAB_ENDPOINT": "has\ta tab"}, {}, {}, ("endpoint",), id="a-required-field-whose-variable-is-invalid-beside-a-valid-row"),
        pytest.param({DERIVED_API_KEY: "short"}, {}, {}, ("api_key",), id="a-required-secret-whose-variable-is-invalid-beside-a-readable-row"),
    ],
)
def test_missing_field_keys_gives_a_call_and_the_catalogue_the_same_missing_fields(variables, system_changes, user_changes, missing, monkeypatch: pytest.MonkeyPatch):
    """3: the same rows and variables, resolved for the catalogue (``decrypt=False``: a secret has no value, judged by
    its key id) and bound for a call (``decrypt=True``): the same missing fields, in declaration order."""
    for variable, value in variables.items():
        monkeypatch.setenv(variable, value)
    system, user = _rule_rows(system_changes, user_changes)

    for_the_catalogue = resolve_plugin_fields("asset", "lab", RULE_FIELDS, system, user, user_id=1, decrypt=False)
    for_a_call = build_bound_settings("asset", "lab", RULE_FIELDS, system, user, user_id=1)

    secrets = {state.field.key: state for state in for_the_catalogue if state.field.secret}
    assert all(state.value is None for state in secrets.values()), "barrier: the catalogue resolves no secret's value"
    assert missing_field_keys(for_the_catalogue) == missing
    assert for_a_call.missing == missing


def test_missing_field_keys_reads_a_secret_without_its_value_by_its_state():
    """3, the rule on states made by hand: a secret set and readable is usable without its value, one unreadable or unset
    is missing when required; only a secret is usable without a value; an invalid variable is missing even when the
    field is optional; the missing keys come in the order of the states."""
    api_key, endpoint, region, tolerance = (_rule_field(key) for key in ("api_key", "endpoint", "region", "tolerance"))

    assert missing_field_keys([FieldState(api_key, "db", is_set=True), FieldState(api_key, "env", is_set=True, locked=True, env_variable=ALIAS_API_KEY)]) == ()
    assert missing_field_keys([FieldState(api_key, "db", is_set=True, problem="unreadable")]) == ("api_key",)
    assert missing_field_keys([FieldState(api_key, "none")]) == ("api_key",)
    assert missing_field_keys([FieldState(endpoint, "db", is_set=True)]) == ("endpoint",), "a plain field without a value is missing, set or not"
    assert missing_field_keys([FieldState(region, "default", value="eu", problem="invalid_stored"), FieldState(tolerance, "default", value=0.5)]) == ()
    assert missing_field_keys([FieldState(tolerance, "env", is_set=True, locked=True, env_variable="LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", problem="invalid_env")]) == ("tolerance",)
    assert missing_field_keys([FieldState(tolerance, "env", is_set=True, locked=True, problem="invalid_env"), FieldState(api_key, "none"), FieldState(endpoint, "none")]) == ("tolerance", "api_key", "endpoint")


def test_the_catalogue_cannot_see_a_blob_its_key_id_vouches_for_but_a_call_cannot_decrypt():
    """3, the one divergence, by design: the catalogue never decrypts, so a secret moved from another user — under the
    current key id — counts as usable there, while a call finds it unreadable and the plugin not configured."""
    system, user = _rule_rows({}, {"token": FROM_ANOTHER_USER})

    for_the_catalogue = resolve_plugin_fields("asset", "lab", RULE_FIELDS, system, user, user_id=1, decrypt=False)
    for_a_call = build_bound_settings("asset", "lab", RULE_FIELDS, system, user, user_id=1)

    assert missing_field_keys(for_the_catalogue) == ()
    assert for_a_call.missing == ("token",)


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


# -----------------------------------------------------------------------------
# X-R43: an integer past what a double holds, from a variable or a row
# -----------------------------------------------------------------------------

#: MOCKFX's integer field: ``decimals``, system, default 6, between 0 and 10.
MOCKFX_DECIMALS = next(field for field in MockFXProvider.settings_fields if field.key == "decimals")
#: The warning of a variable that cannot give its field a value (``resolver._warn_invalid_env``).
INVALID_VARIABLE_EVENT = "Plugin setting variable invalid: the plugin is not configured until it is fixed"


def _digits(count: int) -> str:
    """``count`` random decimal digits, the first not 0: a number no message or log line can show by chance."""
    return random.choice("123456789") + "".join(random.choices("0123456789", k=count - 1))


def _shows_a_run_of(digits: str, text: str, width: int = 20) -> bool:
    """Whether ``text`` holds ``width`` consecutive digits of ``digits``: the value whole, or any long piece of it."""
    return any(digits[start : start + width] in text for start in range(len(digits) - width + 1))


@contextmanager
def _no_overflow(story: str) -> Iterator[None]:
    """An ``OverflowError`` inside fails the test, naming it and what the operator then faces."""
    try:
        yield
    except OverflowError as error:
        pytest.fail(f"{story}: the resolution raised OverflowError ({error}) (X-R43): the plugin's catalogue entry and every call of it fail, where the field should be refused «too large» like any value it refuses")


def _mockfx_decimals_variable() -> str:
    (variable,) = env_variables("fx", "MOCKFX", MOCKFX_DECIMALS)
    return variable


def _mockfx_decimals(*, decrypt: bool) -> FieldState:
    """MOCKFX's ``decimals`` as the catalogue (``decrypt=False``) or a call resolves it, without a row."""
    states = resolve_plugin_fields("fx", "MOCKFX", MockFXProvider.settings_fields, {}, None, user_id=None, decrypt=decrypt)
    return next(state for state in states if state.field.key == "decimals")


def _invalid_variable_warnings(logs: list[dict]) -> list[dict]:
    return [entry for entry in logs if entry["event"] == INVALID_VARIABLE_EVENT]


@pytest.mark.parametrize("sign", ["", "-"], ids=["positive", "negative"])
def test_an_integer_variable_past_the_double_range_is_invalid_env_not_an_overflow(sign: str, monkeypatch: pytest.MonkeyPatch):
    """Red today (X-R43): ``OverflowError``. ``int()`` reads the 401 digits, the finiteness check of ``validate_value``
    cannot convert them to a double, and ``_from_environment`` catches ``SettingValueError`` only: an operator who puts
    such a number in MOCKFX's ``decimals`` variable breaks MOCKFX — its catalogue entry and every call of it raise.

    Contract: as any invalid value of a variable: ``invalid_env`` — ``source`` env, locked, no value —, MOCKFX not
    configured (its default never stands in), one warning naming the variable and the reason «too large», never the value."""
    print_section(f"X-R43: MOCKFX decimals set by its variable to {'minus ' if sign else ''}401 digits")
    variable, digits = _mockfx_decimals_variable(), _digits(401)
    monkeypatch.setenv(variable, sign + digits)

    with capture_logs() as logs, _no_overflow(f"{variable} holding {sign}<401 digits>"):
        for_the_catalogue = _mockfx_decimals(decrypt=False)
        for_a_call = build_bound_settings("fx", "MOCKFX", MockFXProvider.settings_fields, {}, None, user_id=None)

    assert _summary(for_the_catalogue) == ("env", None, True, True, variable, "invalid_env"), _summary(for_the_catalogue)
    assert for_a_call.missing == ("decimals",) and "decimals" not in for_a_call.plain_values(), "MOCKFX is not configured until the variable is fixed: its default never stands in"
    warnings = _invalid_variable_warnings(logs)
    assert [(entry["variable"], entry["family"], entry["plugin"], entry["field"]) for entry in warnings] == [(variable, "fx", "MOCKFX", "decimals")], f"one warning, naming the variable: {warnings}"
    assert "too large" in warnings[0]["reason"], f"the warning must say why: {warnings[0]}"
    assert not _shows_a_run_of(digits, repr(logs)), "a log line shows the variable's value"
    print_success(f"invalid_env, MOCKFX not configured, the warning says {warnings[0]['reason']!r}")


def test_an_integer_variable_longer_than_int_reads_is_already_invalid_env(monkeypatch: pytest.MonkeyPatch):
    """Guard: green today and after (X-R43). Past ``sys.get_int_max_str_digits()`` digits — 4300 by default, so 4301
    here — ``int()`` refuses the text itself: «expected a whole number», ``invalid_env``, the value in no log line."""
    limit = sys.get_int_max_str_digits()
    assert limit > 0, "barrier: this process puts no limit on int(), so no text is too long for it"
    variable, digits = _mockfx_decimals_variable(), _digits(limit + 1)
    monkeypatch.setenv(variable, digits)

    with capture_logs() as logs:
        state = _mockfx_decimals(decrypt=False)

    assert _summary(state) == ("env", None, True, True, variable, "invalid_env"), _summary(state)
    assert [entry["reason"] for entry in _invalid_variable_warnings(logs)] == ["expected a whole number"]
    assert not _shows_a_run_of(digits, repr(logs)), "a log line shows the variable's value"


def test_a_number_variable_of_401_digits_is_already_not_finite(monkeypatch: pytest.MonkeyPatch):
    """Guard: green today and after (X-R43). A number field reads its variable with ``float()``: 401 digits give
    ``inf``, refused «expected a finite number» — ``invalid_env``, the value in no log line. X-R43 changes nothing here."""
    variable, digits = "LIBREFOLIO_PLUGIN_ASSET_LAB_TOLERANCE", _digits(401)
    monkeypatch.setenv(variable, digits)

    with capture_logs() as logs:
        state = _resolve(decrypt=False)["tolerance"]

    assert _summary(state) == ("env", None, True, True, variable, "invalid_env"), _summary(state)
    assert [entry["reason"] for entry in _invalid_variable_warnings(logs)] == ["expected a finite number"]
    assert not _shows_a_run_of(digits, repr(logs)), "a log line shows the variable's value"


@pytest.mark.parametrize(
    ("key", "sign", "default"),
    [
        pytest.param("limit", "", 10, id="a-users-integer"),
        pytest.param("tolerance", "-", 0.5, id="the-instances-number-negative"),
    ],
)
def test_a_row_holding_an_integer_past_the_double_range_counts_as_unset(key: str, sign: str, default: object):
    """Red today (X-R43): ``OverflowError``. ``json.loads`` reads the 401 digits whole, the finiteness check of
    ``validate_value`` cannot convert them to a double, and ``_from_row`` catches ``ValueError`` and ``SettingValueError``
    only: the catalogue and every call of the plugin raise. Only a write behind the API's back stores such a row (an
    edit of the database, a restore); a number field is reached too, since JSON gives it an int.

    Contract: like any row the field refuses now: unset, ``invalid_stored``, the default standing in, the row's date
    kept — for the catalogue and for a call."""
    print_section(f"X-R43: a stored {key} of {'minus ' if sign else ''}401 digits")
    scope = next(field.scope for field in LAB_FIELDS if field.key == key)
    row = _plain(int(sign + _digits(401)))
    system, user = ({key: row}, {}) if scope is SYSTEM else ({}, {key: row})

    with _no_overflow(f"a stored {key} of {sign}<401 digits>"):
        for_the_catalogue = _resolve(system, user, decrypt=False)[key]
        for_a_call = build_bound_settings("asset", "lab", LAB_FIELDS, system, user, user_id=1)

    assert _summary(for_the_catalogue) == ("default", default, False, False, None, "invalid_stored"), _summary(for_the_catalogue)
    assert for_the_catalogue.updated_at == STAMP, "the row's date is kept for the interface"
    assert for_a_call.plain_values()[key] == default, "a call gets the default in place of the row"
    print_success(f"{key}: invalid_stored, the default {default} standing in")


def test_a_row_holding_more_digits_than_json_reads_already_counts_as_unset():
    """Guard: green today and after (X-R43). Past ``sys.get_int_max_str_digits()`` digits ``json.loads`` refuses the
    row with a ``ValueError``, which ``_from_row`` catches: ``invalid_stored``, the default standing in."""
    limit = sys.get_int_max_str_digits()
    assert limit > 0, "barrier: this process puts no limit on int(), so no row is too long for json.loads"
    row = StoredValue(_digits(limit + 1), None, None, STAMP)

    state = _resolve(user={"limit": row})["limit"]

    assert _summary(state) == ("default", 10, False, False, None, "invalid_stored"), _summary(state)


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

    replacement = raised.value
    assert type(replacement) is AssetSourceError and replacement.error_code == "PROVIDER_ERROR"
    assert replacement.message.startswith("Provider lab failed: "), "the replacement names the provider"
    assert replacement.details == {"detail": replacement.message.removeprefix("Provider lab failed: ")}, "N6: the masked description, for the localized message"
    assert replacement.details["detail"] == masked_description(_SlotsLeak(secret), frozenset({secret}))
    assert secret not in json.dumps(replacement.details)
    _assert_replaced(replacement, secret, _SlotsLeak(secret))
    print_success(f"replaced: {replacement}, details {replacement.details}")


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
    assert raised.value.details == {"detail": raised.value.message.removeprefix("Provider lab failed: ")} and secret not in json.dumps(raised.value.details)
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


# -----------------------------------------------------------------------------
# A secret the caller chose: every text that shows a secret hidden whole (N15)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("secrets", "carried"),
    [
        pytest.param({"personal_token": "a-token-the-user-chose"}, True, id="a-user-secret"),
        pytest.param({"api_key": "the-instance-key-0001", "personal_token": "a-token-the-user-chose"}, True, id="a-user-secret-beside-a-system-one"),
        pytest.param({"api_key": "the-instance-key-0001"}, False, id="a-system-secret-only"),
        pytest.param({"api_key": "the-instance-key-0001", "personal_token": ""}, False, id="an-empty-user-secret"),
        pytest.param({}, False, id="no-secret"),
        pytest.param({"not_declared": "a-value-no-field-declares"}, False, id="a-key-no-field-declares"),
    ],
)
def test_carries_user_secrets_is_a_non_empty_secret_of_a_user_field(secrets: dict[str, str], carried: bool):
    """5, N15: mockprov's declaration — a system secret ``api_key``, a user secret ``personal_token`` — with the user's
    plain values set in every case: only a non-empty secret of a ``user`` field is a secret the caller chose; a system
    secret, an empty value, a user's plain values and a key no field declares are not."""
    bound = BoundSettings(MockProvider.settings_fields, {"results_limit": 5, "preferred_language": "it"}, secrets)

    assert bound.carries_user_secrets is carried


def test_an_unbound_instance_carries_no_user_secret():
    """5, N15: mockprov as the registry hands it out, before ``configure_instance``, and ``BoundSettings.unbound``."""
    assert MockProvider().settings.carries_user_secrets is False
    assert BoundSettings.unbound(MockProvider.settings_fields).carries_user_secrets is False


def test_the_binding_of_a_call_carries_a_user_secret_only_with_the_users_own_readable_token():
    """5, N15: ``build_bound_settings`` as ``configure_instance`` calls it for mockprov, the instance key bound every
    time: the user's own token, read from their row, is carried; the same user without a token, a token row moved from
    another user (unreadable: no value) and a call for nobody (``user_rows=None``, a scheduled sync) carry none."""
    system = {"api_key": _secret_row(_marker(), "api_key", code="mockprov")}
    limit = {"results_limit": _plain(5)}
    token = _marker()

    def bind(user_rows: dict[str, StoredValue] | None, user_id: int | None) -> BoundSettings:
        return build_bound_settings("asset", "mockprov", MockProvider.settings_fields, system, user_rows, user_id=user_id)

    own_token = bind({**limit, "personal_token": _secret_row(token, "personal_token", "user", 1, code="mockprov")}, 1)
    no_token = bind(limit, 1)
    moved_token = bind({**limit, "personal_token": _secret_row(_marker(), "personal_token", "user", 2, code="mockprov")}, 1)
    for_nobody = bind(None, None)

    bindings = (own_token, no_token, moved_token, for_nobody)
    assert (own_token.secret("personal_token"), moved_token.secret("personal_token")) == (token, None), "barrier: the token as each binding resolved it"
    assert all(binding.secret_values() for binding in bindings), "barrier: the instance key is bound every time"
    assert [binding.carries_user_secrets for binding in bindings] == [True, False, False, False]


#: What mockprov's error shows right before its instance key: a refused request, as an HTTP library writes it. Anybody
#: can read it in the plugin's code. Longer than a key: a personal token chosen as this context and one character is the
#: longer of the two, the order in which replacing the longest form first left the rest of the key in clear.
ECHO_CONTEXT = "Client error '401 Unauthorized' for url 'https://api.mock.example/v1/quote?symbol=MOCK&apikey="
ECHO_TAIL = "'"
#: The identifiers ``_EchoingMock`` fails for: with an error the boundary masks in place, with one it has to replace.
ECHO, ECHO_SLOTS = "LF_ECHO", "LF_ECHO_SLOTS"


class _EchoingMock(MockProvider):
    """mockprov, whose current value fails for ``ECHO`` and ``ECHO_SLOTS`` with the text of the refused request —
    ``ECHO_CONTEXT``, the instance key, ``ECHO_TAIL`` —: for ``ECHO`` an ``AssetSourceError`` raised from the library's
    ``ConnectionError`` (kept in ``raised``), which the boundary masks in place; for ``ECHO_SLOTS`` a ``_SlotsLeak``,
    which it has to replace. Any other identifier gets mockprov's own answer."""

    raised: AssetSourceError | None = None

    async def get_current_value(self, identifier, identifier_type, provider_params=None):
        if identifier not in (ECHO, ECHO_SLOTS):
            return await super().get_current_value(identifier, identifier_type, provider_params)
        echoed = f"{ECHO_CONTEXT}{self.settings.secret('api_key')}{ECHO_TAIL}"
        if identifier == ECHO_SLOTS:
            raise _SlotsLeak(echoed)
        try:
            raise ConnectionError(echoed)
        except ConnectionError as cause:
            self.raised = AssetSourceError(f"{echoed} refused", "AUTH_FAILED", {"url": echoed, "status": 401})
            raise self.raised from cause


def _bound_mockprov(*, api_key: str, personal_token: str | None = None, plugin_class: type[MockProvider] = MockProvider) -> MockProvider:
    """A new ``plugin_class`` instance bound as ``configure_instance`` binds mockprov for a call made for user 1: the
    instance key and, when given, that user's personal token, both read from their stored rows under the test key."""
    system = {"api_key": _secret_row(api_key, "api_key", code="mockprov")}
    user = {} if personal_token is None else {"personal_token": _secret_row(personal_token, "personal_token", "user", 1, code="mockprov")}
    instance = plugin_class()
    instance.bind_settings(build_bound_settings("asset", "mockprov", MockProvider.settings_fields, system, user, user_id=1))
    assert (instance.settings.secret("api_key"), instance.settings.secret("personal_token"), instance.settings.missing) == (api_key, personal_token, ()), "setup: bound as stored"
    return instance


def _guesses(key: str) -> dict[str, str]:
    """The personal tokens a caller chooses to guess ``key``'s first character: ``ECHO_CONTEXT``, then a wrong
    character, or the right one."""
    wrong = "0" if key[0] != "0" else "1"
    return {"wrong": ECHO_CONTEXT + wrong, "right": ECHO_CONTEXT + key[0]}


async def _raised_by(provider: MockProvider, identifier: str) -> AssetSourceError:
    """What ``call_provider`` raises to its caller when ``provider``'s current value for ``identifier`` fails."""
    with pytest.raises(AssetSourceError) as raised:
        await asset_core.call_provider(provider, lambda: provider.get_current_value(identifier, None), timeout=5)
    return raised.value


def _link(error: BaseException | None) -> tuple | None:
    return None if error is None else (type(error), error.args, str(error))


def _what_the_caller_reads(error: AssetSourceError) -> tuple:
    """All a caller can read of an error: type, code, arguments, message, details, text and representation, and the
    type, arguments and text of its cause and of its context."""
    return (type(error), error.error_code, error.args, error.message, error.details, str(error), repr(error), _link(error.__cause__), _link(error.__context__))


@pytest.mark.asyncio
async def test_with_a_personal_secret_two_guesses_of_the_instance_key_raise_the_same_error():
    """5, N15, the overlap attack through ``call_provider``: mockprov's error echoes ``ECHO_CONTEXT`` and its instance
    key; the caller's personal token is that context and a guess of the key's first character. Wrong or right, the
    caller gets the same error: the very one the plugin raised, type and ``error_code`` kept, every text that showed a
    secret — arguments, message, details, cause and context — ``***`` entirely. A detail that shows none stays, and an
    error that shows no secret is left as it is."""
    print_section("5: N15, two guesses of the instance key, one error")
    key = _marker()
    tokens = _guesses(key)
    echoed = f"{ECHO_CONTEXT}{key}{ECHO_TAIL}"
    assert len(tokens["right"]) > len(key), "setup: the chosen token is the longer one"
    assert mask_text(echoed, frozenset({key, tokens["wrong"]})) != mask_text(echoed, frozenset({key, tokens["right"]})), "barrier: masked in place, the two guesses would read differently"

    seen = {}
    for guess, token in tokens.items():
        provider = _bound_mockprov(api_key=key, personal_token=token, plugin_class=_EchoingMock)
        assert provider.settings.carries_user_secrets, "barrier: the call carries a secret of the caller's own"
        error = await _raised_by(provider, ECHO)
        assert error is provider.raised, "masked in place: the very error the plugin raised, not a replacement"
        seen[guess] = _what_the_caller_reads(error)

    hidden = (ConnectionError, (MASK,), MASK)
    assert seen["wrong"] == seen["right"], f"the two guesses must read the same: {seen}"
    assert seen["right"] == (AssetSourceError, "AUTH_FAILED", (MASK,), MASK, {"url": MASK, "status": 401}, MASK, f"AssetSourceError({MASK!r})", hidden, hidden)
    untouched = await _raised_by(_bound_mockprov(api_key=key, personal_token=tokens["right"], plugin_class=_EchoingMock), "INVALID_TICKER_12345")
    assert (untouched.error_code, untouched.message, untouched.details) == ("NOT_FOUND", "Invalid identifier for mock provider.", {}), "an error that shows no secret is left as it is"
    print_success("wrong or right guess: AUTH_FAILED, every text ***")


@pytest.mark.asyncio
async def test_without_a_personal_secret_the_errors_are_masked_in_place_as_before():
    """5, the other side of N15: the instance key only, for a user without a token: the error reaches the caller masked
    in place, the known context kept (the CP10 contract), and an error the boundary replaces is described by its text
    masked in place."""
    key = _marker()
    provider = _bound_mockprov(api_key=key, plugin_class=_EchoingMock)
    assert not provider.settings.carries_user_secrets, "barrier: no secret of the caller's own"

    in_place = await _raised_by(provider, ECHO)
    replaced = await _raised_by(_bound_mockprov(api_key=key, plugin_class=_EchoingMock), ECHO_SLOTS)

    echoed = f"{ECHO_CONTEXT}{MASK}{ECHO_TAIL}"
    message, link = f"{echoed} refused", (ConnectionError, (echoed,), echoed)
    assert in_place is provider.raised
    assert _what_the_caller_reads(in_place) == (AssetSourceError, "AUTH_FAILED", (message,), message, {"url": echoed, "status": 401}, message, f"AssetSourceError({message!r})", link, link)
    description = f"_SlotsLeak: failed with {echoed}"
    replacement = f"Provider mockprov failed: {description}"
    assert _what_the_caller_reads(replaced) == (AssetSourceError, "PROVIDER_ERROR", (replacement,), replacement, {"detail": description}, replacement, f"AssetSourceError({replacement!r})", None, None)


@pytest.mark.asyncio
async def test_with_a_personal_secret_a_replaced_error_is_described_as_its_type_and_a_mask():
    """5, N15: an error masking cannot rewrite — a ``__str__`` over ``__slots__``, the ``_SlotsLeak`` of the CP10 tests —
    is replaced by ``PROVIDER_ERROR``; with a personal secret its description, in the message and in
    ``details["detail"]``, is ``Type: ***``, the same for either guess, and the replacement keeps no link to the
    original."""
    key = _marker()

    seen = {}
    for guess, token in _guesses(key).items():
        seen[guess] = _what_the_caller_reads(await _raised_by(_bound_mockprov(api_key=key, personal_token=token, plugin_class=_EchoingMock), ECHO_SLOTS))

    replacement = f"Provider mockprov failed: _SlotsLeak: {MASK}"
    assert seen["wrong"] == seen["right"] == (AssetSourceError, "PROVIDER_ERROR", (replacement,), replacement, {"detail": f"_SlotsLeak: {MASK}"}, replacement, f"AssetSourceError({replacement!r})", None, None)


# =============================================================================
# 6. SEARCH: THE PROVIDERS NOT CONFIGURED
# =============================================================================


def _hand_out_new(monkeypatch: pytest.MonkeyPatch, registry: type, classes: dict[str, type]) -> None:
    """``registry`` hands out a new instance of ``classes[code]`` for those codes, and its own plugins otherwise."""
    original = registry.get_provider_instance

    def get_provider_instance(_cls, code, **kwargs):
        plugin_class = classes.get(code)
        return plugin_class() if plugin_class is not None else original(code, **kwargs)

    monkeypatch.setattr(registry, "get_provider_instance", classmethod(get_provider_instance))


def _searches_of(monkeypatch: pytest.MonkeyPatch, plugin_class: type) -> list[str]:
    """The queries ``plugin_class.search`` (and its subclasses') is asked, still answering them."""
    asked: list[str] = []
    original = plugin_class.search

    async def counted(self, query: str) -> list[dict]:
        asked.append(query)
        return await original(self, query)

    monkeypatch.setattr(plugin_class, "search", counted)
    return asked


async def _sse(stream) -> list[dict]:
    """The events of an SSE stream, decoded."""
    events = []
    async for chunk in stream:
        assert chunk.startswith("data: ") and chunk.endswith("\n\n"), chunk
        events.append(json.loads(chunk[len("data: ") :]))
    return events


def _query(prefix: str) -> str:
    """A query of this test alone: no search cache of the process answers it."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@pytest.mark.asyncio
async def test_the_search_lists_the_providers_not_configured_in_the_order_asked(monkeypatch: pytest.MonkeyPatch, through_private_engine: list[int]):
    """6: two providers not configured, one failing with ``SEARCH_ERROR``, mockprov answering: the two in
    ``providers_not_configured`` in the order asked, and never called; the failing one an error only; mockprov in neither."""
    print_section("6: providers_not_configured")
    _hand_out_new(monkeypatch, AssetProviderRegistry, {UNCONFIGURED_FIRST: _UnconfiguredSearch, UNCONFIGURED_SECOND: _UnconfiguredSearchToo, FAILING: _FailingSearch})
    asked = _searches_of(monkeypatch, _UnconfiguredSearch)
    order = [UNCONFIGURED_FIRST, FAILING, "mockprov", UNCONFIGURED_SECOND]

    response = await AssetSearchService.search(_query("lab-search"), provider_codes=order)

    assert response.providers_queried == order
    assert response.providers_with_errors == [UNCONFIGURED_FIRST, FAILING, UNCONFIGURED_SECOND]
    assert response.providers_not_configured == [UNCONFIGURED_FIRST, UNCONFIGURED_SECOND]
    assert {item.provider_code for item in response.results} == {"mockprov"}, "barrier: the configured provider answered"
    assert asked == [], "a provider not configured is never called"
    assert len(through_private_engine) == 3, "barrier: the two labs and mockprov were configured for real, through the private engine"
    print_success(f"not configured {response.providers_not_configured}, with errors {response.providers_with_errors}")


@pytest.mark.asyncio
async def test_the_search_stream_reports_a_provider_not_configured_with_its_code_at_info(monkeypatch: pytest.MonkeyPatch, through_private_engine: list[int]):
    """6: the ``provider_error`` event carries ``error_code: NOT_CONFIGURED`` beside the message, and nothing else; the
    refusal is one INFO line naming the missing field: no warning, no error, no traceback; the provider is never called."""
    print_section("6: the SSE provider_error of a provider not configured")
    _hand_out_new(monkeypatch, AssetProviderRegistry, {UNCONFIGURED_SECOND: _UnconfiguredSearchToo})
    asked = _searches_of(monkeypatch, _UnconfiguredSearch)

    with capture_logs() as logs:
        events = await _sse(AssetSearchService.search_stream(_query("lab-stream"), provider_codes=[UNCONFIGURED_SECOND]))

    (error,) = [event for event in events if event["event"] == "provider_error"]
    (done,) = [event for event in events if event["event"] == "done"]
    assert error.keys() == {"event", "provider_code", "error", "error_code"}
    assert (error["provider_code"], error["error_code"]) == (UNCONFIGURED_SECOND, "NOT_CONFIGURED")
    assert error["error"], "the raw message stays"
    assert (done["providers_queried"], done["providers_with_errors"], done["total_results"]) == ([UNCONFIGURED_SECOND], [UNCONFIGURED_SECOND], 0)
    stream_lines = [(entry["event"], entry["log_level"], entry.get("provider"), entry.get("missing")) for entry in logs if str(entry["event"]).startswith("Search stream")]
    assert stream_lines == [("Search stream: provider not configured", "info", UNCONFIGURED_SECOND, ["endpoint"])]
    assert [entry for entry in logs if entry["log_level"] in ("warning", "error", "critical") or entry.get("exc_info")] == []
    assert asked == []
    print_success(f"provider_error {error['error_code']}, logged at INFO")


# =============================================================================
# 7. THE ASSET URL: public_asset_url, and the probe's provider_url
# =============================================================================

#: The warning of a withheld URL: it names the provider, never the URL or a secret.
URL_WITHHELD = "Provider asset URL withheld: it shows a secret"


@pytest.mark.parametrize("form", ["as-written", "quote", "quote_plus"])
@pytest.mark.parametrize("field_key", ["api_key", "personal_token"])
def test_public_asset_url_withholds_a_url_that_shows_a_secret(field_key: str, form: str):
    """7: a URL that shows a bound secret — the instance key or the caller's token, as written or URL-encoded — is
    withheld whole: ``None``, never a masked URL, and one warning naming the provider, without the URL or a secret."""
    bound_secrets = {key: _marker() + " /+&" for key in ("api_key", "personal_token")}
    provider = _bound_mockprov(api_key=bound_secrets["api_key"], personal_token=bound_secrets["personal_token"])
    secret = bound_secrets[field_key]
    forms = {"as-written": secret, "quote": quote(secret, safe=""), "quote_plus": quote_plus(secret)}
    assert len(set(forms.values())) == 3, "setup: the three forms must differ, or the test proves one of them only"
    url = f"https://mock.example/assets/MOCK?region=eu&{field_key}={forms[form]}"

    with capture_logs() as logs:
        withheld = asset_core.public_asset_url(provider, url)

    assert withheld is None
    assert logs == [{"event": URL_WITHHELD, "log_level": "warning", "provider": "mockprov"}]
    assert all(text not in repr(logs) for text in (*bound_secrets.values(), forms[form])), logs


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("https://mock.example/assets/MOCK?region=eu", id="a-url-without-a-secret"),
        pytest.param(None, id="no-url"),
        pytest.param("", id="an-empty-url"),
    ],
)
def test_public_asset_url_hands_back_a_url_that_shows_no_secret(url: str | None):
    """7: the URL as the plugin built it — the very object —, nothing logged: with both secrets bound, and on an instance
    nobody configured."""
    configured = _bound_mockprov(api_key=_marker(), personal_token=_marker())

    with capture_logs() as logs:
        handed_back = (asset_core.public_asset_url(configured, url), asset_core.public_asset_url(MockProvider(), url))

    assert all(result is url for result in handed_back), handed_back
    assert logs == []


def test_public_asset_url_hands_a_test_doubles_url_back_as_it_is():
    """7: an object that is not a plugin has no settings: its URL comes back as it is, nothing logged — even from a
    double without a ``provider_code``."""
    url = "https://double.example/assets/X?apikey=whatever-the-double-says"

    with capture_logs() as logs:
        handed_back = (asset_core.public_asset_url(_NotAPlugin(), url), asset_core.public_asset_url(_SuiteDouble(), url))

    assert all(result is url for result in handed_back), handed_back
    assert logs == []


@pytest.mark.parametrize(
    ("shown", "withheld"),
    [
        pytest.param("api_key", True, id="the-instance-key-in-the-url"),
        pytest.param("personal_token", True, id="the-users-token-in-the-url"),
        pytest.param(None, False, id="no-secret-in-the-url"),
    ],
)
@pytest.mark.asyncio
async def test_the_probe_withholds_a_provider_url_that_shows_a_secret(shown: str | None, withheld: bool, users: dict[str, int], private_engine: AsyncEngine, through_private_engine: list[int], monkeypatch: pytest.MonkeyPatch):
    """7: the probe computes ``provider_url`` outside the call boundary, through ``public_asset_url``. mockprov's
    ``get_asset_url``, patched to put a secret in the URL — the instance key, or alice's token, URL-encoded —: alice's
    probe answers ``provider_url`` ``None`` with one warning, and its current price as before. The control, a URL
    without a secret, comes back as the plugin built it."""
    print_section(f"7: the probe's provider_url, {shown or 'no secret'} in the URL")
    alice = users["alice"]
    bound_secrets = {key: _marker() + " /+" for key in ("api_key", "personal_token")}
    await _store(private_engine, _system("mockprov", "api_key", secret=bound_secrets["api_key"]), _user(alice, "mockprov", "personal_token", secret=bound_secrets["personal_token"]))
    built: list[str] = []

    def asset_url(self: MockProvider, identifier: str, identifier_type: object, provider_params: dict | None = None) -> str:
        query = "region=eu" if shown is None else f"region=eu&{shown}={quote(self.settings.secret(shown), safe='')}"
        built.append(f"https://mock.example/assets/{identifier}?{query}")
        return built[-1]

    monkeypatch.setattr(MockProvider, "get_asset_url", asset_url)
    config = FAProviderConfigBase(provider_code="mockprov", identifier="MOCK", identifier_type="TICKER", provider_params={})

    with capture_logs() as logs:
        response = await ProviderManagementOperations.probe_provider_config(config, [ProbeOperation.CURRENT_PRICE], user_id=alice)

    assert len(built) == 1, "barrier: the probe asked the plugin for its URL"
    assert shown is None or quote(bound_secrets[shown], safe="") in built[0], f"barrier: the plugin put the secret in its URL: {built}"
    assert response.provider_url == (None if withheld else built[0])
    assert [entry for entry in logs if entry["event"] == URL_WITHHELD] == ([{"event": URL_WITHHELD, "log_level": "warning", "provider": "mockprov"}] if withheld else [])
    assert response.current_price is not None and response.current_price.success, f"the rest of the probe answers: {response.current_price}"
    answer = response.model_dump_json()
    assert not [form for secret in bound_secrets.values() for form in (secret, quote(secret, safe=""), quote_plus(secret)) if form in answer], "no form of a secret in the probe's answer"
    print_success(f"provider_url {response.provider_url!r}")
