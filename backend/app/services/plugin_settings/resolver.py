"""The value each declared field takes, for the catalogue of the API and for a call.

Precedence, field by field:

1. **environment** (``system`` fields only): ``LIBREFOLIO_PLUGIN_<FAMILY>_<CODE>_<FIELD>``, then the field's ``env``
   alias, each also as ``_FILE`` (``config/plugins.py``, ``plugin_setting_env``). A variable that is set wins and
   locks the field, even when its value is invalid: the field then has the problem ``invalid_env``, the log says why
   (once per process), and the plugin is not configured — its calls are refused with ``NOT_CONFIGURED`` until the
   variable is fixed. Never a silent fallback to the default;
2. **database**: the instance's row for a ``system`` field, the user's row for a ``user`` field;
3. **default**: the declared one (a secret has none).

A secret's row is decrypted only to deliver it to a call (``decrypt=True``). The catalogue judges it by its key id: set,
and readable or not by the current key, never decrypted. A row a field can no longer use (a value the field refuses
now, a secret where a plain value is due, or the reverse) counts as unset, with the problem ``invalid_stored``.

When the instance key cannot be used (a generated key file gone bad: the server starts all the same), every stored
secret is ``unreadable`` and the log says so once; the environment's secrets still reach the calls, and the fingerprint
of their cache keys is computed without the key (``settings_fingerprint``).

``resolve_plugin_fields`` reads the environment, secret files and the instance key: it is synchronous, and the async
callers run it in a worker thread (``runtime.py``, ``service.py``).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from backend.app.config import SecretFileError
from backend.app.config.plugins import plugin_setting_env
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_key import InstanceKeyError
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.crypto import (
    UnreadableSecretError,
    decrypt_secret,
    fingerprint_subkey,
    key_id_of,
    secret_aad,
    settings_subkey,
)
from backend.app.services.plugin_settings.fields import (
    PluginSettingField,
    SettingScope,
    SettingValueError,
    env_variables,
    parse_env_value,
    validate_value,
)

logger = get_logger(__name__)

Source = Literal["env", "db", "default", "none"]
Problem = Literal["unreadable", "invalid_env", "invalid_stored"]

#: (family, plugin, field, key id) of the unreadable secrets already logged: one warning per process, not one per call.
_warned_unreadable: set[tuple[str, str, str, str | None]] = set()
#: The variables already logged as invalid, and whether the unusable instance key was: once per process each.
_warned_invalid_env: set[str] = set()
_warned_key_unavailable: list[bool] = []


def _warn_invalid_env(variable: str, family: str, plugin_code: str, declared: PluginSettingField, reason: str) -> None:
    """Log once that ``variable`` cannot give its field a value: the reason never contains the value."""
    if variable in _warned_invalid_env:
        return
    _warned_invalid_env.add(variable)
    logger.warning("Plugin setting variable invalid: the plugin is not configured until it is fixed", variable=variable, family=family, plugin=plugin_code, field=declared.key, reason=reason)


@dataclass(frozen=True)
class StoredValue:
    """One row's content, copied out of the session so that it can cross into a worker thread."""

    value_json: str | None
    secret_ciphertext: bytes | None
    key_id: str | None
    updated_at: datetime | None


@dataclass(frozen=True)
class FieldState:
    """What one field resolves to.

    ``value`` is the plain value, or a secret's plaintext only when it was resolved for a call. ``is_set`` says that
    the environment or a row gives the field a value, readable or not; a default does not count.
    """

    field: PluginSettingField
    source: Source
    value: Any = None
    is_set: bool = False
    locked: bool = False
    env_variable: str | None = None
    problem: Problem | None = None
    updated_at: datetime | None = None


class _KeyCache:
    """The subkey, derived at most once per resolution and only when a secret row needs it; ``None`` when unusable."""

    def __init__(self) -> None:
        self._subkey: bytes | None = None
        self._unusable = False

    def subkey(self) -> bytes | None:
        if self._subkey is None and not self._unusable:
            try:
                self._subkey = settings_subkey()
            except InstanceKeyError:
                self._unusable = True
                if not _warned_key_unavailable:
                    _warned_key_unavailable.append(True)
                    logger.error("Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)")
        return self._subkey


def _from_environment(family: str, plugin_code: str, declared: PluginSettingField, decrypt: bool) -> FieldState | None:
    for variable in env_variables(family, plugin_code, declared):
        try:
            raw = plugin_setting_env(variable)
        except SecretFileError as error:  # names the variable and the path, never the content
            _warn_invalid_env(variable, family, plugin_code, declared, str(error))
            return FieldState(declared, "env", is_set=True, locked=True, env_variable=variable, problem="invalid_env")
        if raw is None:
            continue
        try:
            value = parse_env_value(declared, raw)
        except SettingValueError as error:  # says why, never the value
            _warn_invalid_env(variable, family, plugin_code, declared, str(error))
            return FieldState(declared, "env", is_set=True, locked=True, env_variable=variable, problem="invalid_env")
        shown = value if (decrypt or not declared.secret) else None
        return FieldState(declared, "env", value=shown, is_set=True, locked=True, env_variable=variable)
    return None


def _from_row(  # noqa: PLR0913 — the row, its owner and the key travel together
    family: str,
    plugin_code: str,
    declared: PluginSettingField,
    stored: StoredValue,
    user_id: int | None,
    decrypt: bool,
    keys: _KeyCache,
) -> FieldState | None:
    if declared.secret:
        if stored.secret_ciphertext is None:
            return None
        subkey = keys.subkey()
        if subkey is None:
            return FieldState(declared, "db", is_set=True, problem="unreadable", updated_at=stored.updated_at)
        if not decrypt:
            readable = stored.key_id == key_id_of(subkey)
            return FieldState(declared, "db", is_set=True, problem=None if readable else "unreadable", updated_at=stored.updated_at)
        aad = secret_aad(family, plugin_code, declared.key, declared.scope.value, user_id if declared.scope is SettingScope.USER else None)
        try:
            plaintext = decrypt_secret(subkey, aad, stored.secret_ciphertext)
        except UnreadableSecretError:
            marker = (family, plugin_code, declared.key, stored.key_id)
            if marker not in _warned_unreadable:
                _warned_unreadable.add(marker)
                logger.warning("Plugin setting unreadable: it must be entered again", family=family, plugin=plugin_code, field=declared.key, scope=declared.scope.value)
            return FieldState(declared, "db", is_set=True, problem="unreadable", updated_at=stored.updated_at)
        return FieldState(declared, "db", value=plaintext, is_set=True, updated_at=stored.updated_at)
    if stored.value_json is None:
        return None
    try:
        value = validate_value(declared, json.loads(stored.value_json))
    except (ValueError, SettingValueError):
        return None
    return FieldState(declared, "db", value=value, is_set=True, updated_at=stored.updated_at)


def resolve_plugin_fields(  # noqa: PLR0913 — one plugin's fields, its rows and the caller
    family: str,
    plugin_code: str,
    fields: tuple[PluginSettingField, ...],
    system_rows: Mapping[str, StoredValue],
    user_rows: Mapping[str, StoredValue] | None,
    *,
    user_id: int | None,
    decrypt: bool,
) -> list[FieldState]:
    """The state of each field of one plugin, in declaration order. Synchronous: run it in a worker thread.

    ``user_rows`` are the caller's rows, or ``None`` when the values are not for a user (a scheduled sync): the
    ``user`` fields then take their defaults. ``decrypt`` delivers the secrets' plaintext, for a call only.
    """
    keys = _KeyCache()
    states = []
    for declared in fields:
        from_env = _from_environment(family, plugin_code, declared, decrypt)
        if from_env is not None:
            states.append(from_env)
            continue
        rows = system_rows if declared.scope is SettingScope.SYSTEM else (user_rows or {})
        stored = rows.get(declared.key)
        state = _from_row(family, plugin_code, declared, stored, user_id, decrypt, keys) if stored is not None else None
        if state is not None:
            states.append(state)
            continue
        problem: Problem | None = "invalid_stored" if stored is not None else None
        updated_at = stored.updated_at if stored is not None else None
        if declared.default is not None:
            states.append(FieldState(declared, "default", value=declared.default, problem=problem, updated_at=updated_at))
        else:
            states.append(FieldState(declared, "none", problem=problem, updated_at=updated_at))
    return states


def missing_field_keys(states: list[FieldState]) -> tuple[str, ...]:
    """The fields that leave a plugin not configured: required without a usable value, or set by an invalid variable.

    One rule for a call (``build_bound_settings``, ``NOT_CONFIGURED``) and for the catalogue (``configured``). A secret
    resolved without decrypting it (the catalogue) has no value: it is usable when it is set and readable.
    """
    missing = []
    for state in states:
        usable = state.problem not in ("unreadable", "invalid_env") and (state.value is not None or (state.field.secret and state.is_set))
        if (state.field.required and not usable) or state.problem == "invalid_env":
            missing.append(state.field.key)
    return tuple(missing)


def settings_fingerprint(plain: Mapping[str, Any], secrets: Mapping[str, str]) -> str:
    """A short fingerprint of the values a call received, for the keys of the caches that depend on them.

    Plain values only: a SHA-256. With secrets: an HMAC under a subkey of the instance, so the fingerprint of a cache
    key never lets anyone test a guess of a secret. When the instance key cannot be used, the stored secrets are
    unreadable and only the environment's reach a call, the same for the whole process: the fingerprint then takes
    the names of the secrets, never their values.
    """
    canonical = json.dumps({"plain": plain, "secret": secrets}, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    if not secrets:
        return hashlib.sha256(canonical).hexdigest()[:32]
    try:
        subkey = fingerprint_subkey()
    except InstanceKeyError:
        names = json.dumps({"plain": plain, "secret_names": sorted(secrets), "key": "unusable"}, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(names).hexdigest()[:32]
    return hmac.new(subkey, canonical, hashlib.sha256).hexdigest()[:32]


def build_bound_settings(  # noqa: PLR0913 — the arguments of resolve_plugin_fields
    family: str,
    plugin_code: str,
    fields: tuple[PluginSettingField, ...],
    system_rows: Mapping[str, StoredValue],
    user_rows: Mapping[str, StoredValue] | None,
    *,
    user_id: int | None,
) -> BoundSettings:
    """The values a call receives: plain values, secrets, the fields left without a usable value, the fingerprint.

    A field is left without a usable value when it is required and has none, or when its environment variable is set
    but invalid (never replaced by the default): either way the plugin is not configured. Synchronous like
    ``resolve_plugin_fields``: run it in a worker thread.
    """
    states = resolve_plugin_fields(family, plugin_code, fields, system_rows, user_rows, user_id=user_id, decrypt=True)
    plain = {state.field.key: state.value for state in states if not state.field.secret and state.value is not None}
    secrets = {state.field.key: state.value for state in states if state.field.secret and state.value is not None}
    return BoundSettings(fields, plain, secrets, missing_field_keys(states), fingerprint=settings_fingerprint(plain, secrets))
