"""The plugin settings API: the catalogue a caller sees, and the writes, all or nothing.

The rules (plan 03, §4.4 and the CP10 design):

- **System fields** are written by an administrator only. A user who is not one sees them read-only: the value of a
  plain field, and only whether a secret is set (D-X15).
- **User fields** belong to their user: written and read by that user only. No endpoint shows them to anyone else, an
  administrator included.
- A field an **environment variable** sets is locked: a write is refused with ``LOCKED_BY_ENV``. In the **managed
  profile** (``LIBREFOLIO_PROFILE=managed``) such a field is not shown at all, and a write to it is ``UNKNOWN_FIELD``,
  as if it did not exist: the hoster sets it, the customer never sees it.
- **Test-only plugins** are listed only when named in ``plugin_code``; a write names its plugin, so the tests can set
  their fields.
- **All or nothing**: every item is checked before anything is written. One refused item refuses the write, and the
  refusal lists every item with its outcome. Then one transaction.
- A **secret** is encrypted with the instance's subkey and bound to its row (``crypto.py``). No message, result or log
  line ever contains a value; the log records who wrote which fields.

Reading the environment, secret files and the instance key is synchronous I/O: it runs in a worker thread.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.config.plugins import plugin_setting_env_origin
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.logging_config import get_logger
from backend.app.schemas.plugin_settings import (
    PluginSettingErrorCode,
    PluginSettingFieldRead,
    PluginSettingOptionRead,
    PluginSettingsCatalogResponse,
    PluginSettingsPluginRead,
    PluginSettingsWriteResponse,
    PluginSettingWriteItem,
    PluginSettingWriteResult,
)
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.instance_key import InstanceKeyError
from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType, SettingValueError, env_variables, validate_value
from backend.app.services.plugin_settings.resolver import FieldState, StoredValue, missing_field_keys, resolve_plugin_fields
from backend.app.services.plugin_settings.runtime import stored_value
from backend.app.services.provider_registry import AbstractProviderRegistry
from backend.app.services.tools.registry import ToolPluginRegistry
from backend.app.utils.datetime_utils import utcnow

logger = get_logger(__name__)

#: The families whose plugins may declare settings, with their registries.
FAMILY_REGISTRIES: dict[str, type[AbstractProviderRegistry]] = {"asset": AssetProviderRegistry, "fx": FXProviderRegistry, "brim": BRIMProviderRegistry, "tool": ToolPluginRegistry}

#: The families whose plugins have no icon of their own: a Tool is drawn with the ``icon_key`` of its service by the Tools page, and the
#: settings catalogue lists it with the neutral icon.
FAMILIES_WITHOUT_ICON: frozenset[str] = frozenset({"tool"})

#: The attribute of a plugin instance that holds its icon URL, per family: the one its family's provider list publishes
#: (``GET /assets/provider`` reads ``get_icon``, ``GET /fx/providers`` reads ``icon``, the BRIM plugins publish ``icon_url``). A new family
#: adds one row, or joins ``FAMILIES_WITHOUT_ICON``.
FAMILY_ICON_ATTRIBUTES: dict[str, str] = {"asset": "get_icon", "fx": "icon", "brim": "icon_url"}


class PluginSettingsRefused(Exception):
    """At least one item of a write is refused: nothing was written. ``results`` holds every item's outcome."""

    def __init__(self, results: list[PluginSettingWriteResult]):
        super().__init__(f"{sum(not result.success for result in results)} of {len(results)} plugin setting(s) refused")
        self.results = results


class PluginSettingsKeyUnavailable(Exception):
    """A secret cannot be encrypted: the instance key cannot be used (see the configuration checks)."""


class PluginSettingsConflict(Exception):
    """Another write changed the same fields at the same time: nothing was written; try again."""


@dataclass(frozen=True)
class _Plugin:
    family: str
    code: str
    plugin_class: type
    name: str
    icon_url: str | None


def _plugin_identity(family: str, plugin_class: type, code: str) -> tuple[str, str | None]:
    """The plugin's name and icon URL, read from one instance as its family's provider list reads them.

    A plugin that cannot be instantiated shows its code and no icon. The name is ``provider_name``, else ``name``, else
    the code; one that raises (other than ``AttributeError``, which moves on to the next) is the code. An icon that
    cannot be read, or is not a non-empty string, is no icon: the catalogue never fails because of either.

    A Tool is listed by its tool code (``code``): its name is the ``ToolService.name`` of that code, and it has no icon.
    """
    if family == "tool":
        service = next((candidate for candidate in getattr(plugin_class, "services", ()) if candidate.tool_code == code), None)
        return (service.name if service is not None else code), None
    try:
        instance = plugin_class()
    except Exception:  # noqa: BLE001 — a plugin that cannot be instantiated still has a code to show
        return code, None
    try:
        name = getattr(instance, "provider_name", None) or getattr(instance, "name", None) or code
    except Exception:  # noqa: BLE001 — a name that cannot be read: the code stands for it
        name = code
    attribute = FAMILY_ICON_ATTRIBUTES.get(family)
    try:
        icon = getattr(instance, attribute, None) if attribute else None
    except Exception:  # noqa: BLE001 — an icon is decoration: one that cannot be read is none
        icon = None
    return name, icon.strip() if isinstance(icon, str) and icon.strip() else None


def _plugins(family: str | None, plugin_code: str | None) -> Iterator[_Plugin]:
    """The registered plugins that declare settings, filtered; a test-only one only when ``plugin_code`` names it."""
    for name, registry in FAMILY_REGISTRIES.items():
        if family is not None and name != family:
            continue
        for code in registry.list_plugin_codes():
            plugin_class = registry.get_plugin(code)
            if plugin_class is None or not getattr(plugin_class, "settings_fields", ()):
                continue
            if plugin_code is not None and code != plugin_code:
                continue
            if getattr(plugin_class, "test_only", False) and plugin_code is None:
                continue
            yield _Plugin(name, code, plugin_class, *_plugin_identity(name, plugin_class, code))


def _find_plugin(family: str, plugin_code: str) -> _Plugin | None:
    return next(iter(_plugins(family, plugin_code)), None)


def _is_managed() -> bool:
    return get_settings().LIBREFOLIO_PROFILE == "managed"


# =============================================================================
# Catalogue
# =============================================================================


async def _rows_by_plugin(session: AsyncSession, user_id: int) -> tuple[dict[tuple[str, str], dict[str, StoredValue]], dict[tuple[str, str], dict[str, StoredValue]]]:
    system: dict[tuple[str, str], dict[str, StoredValue]] = defaultdict(dict)
    for row in (await session.execute(select(PluginSystemSetting))).scalars():
        system[(row.family, row.plugin_code)][row.field_key] = stored_value(row)
    user: dict[tuple[str, str], dict[str, StoredValue]] = defaultdict(dict)
    for row in (await session.execute(select(PluginUserSetting).where(PluginUserSetting.user_id == user_id))).scalars():
        user[(row.family, row.plugin_code)][row.field_key] = stored_value(row)
    return system, user


def _field_read(state: FieldState, *, is_admin: bool) -> PluginSettingFieldRead:
    declared = state.field
    textual = declared.type is SettingType.STRING
    return PluginSettingFieldRead(
        key=declared.key,
        type=declared.type.value,
        scope=declared.scope.value,
        secret=declared.secret,
        required=declared.required,
        label=declared.label,
        description=declared.description,
        label_key=declared.label_key,
        description_key=declared.description_key,
        options=[PluginSettingOptionRead(value=option.value, label=option.label, label_key=option.label_key) for option in declared.options],
        min_length=declared.effective_min_length if textual else None,
        max_length=declared.effective_max_length if textual else None,
        minimum=declared.minimum,
        maximum=declared.maximum,
        default=None if declared.secret else declared.default,
        value=None if declared.secret else state.value,
        is_set=state.is_set,
        source=state.source,
        locked=state.locked,
        env_variable=state.env_variable if is_admin and state.locked else None,
        editable=not state.locked and (declared.scope is SettingScope.USER or is_admin),
        problem=state.problem,
        updated_at=state.updated_at,
    )


def _resolve_catalogue(plugins: list[_Plugin], system: dict, user: dict, user_id: int) -> list[list[FieldState]]:
    return [resolve_plugin_fields(plugin.family, plugin.code, plugin.plugin_class.settings_fields, system.get((plugin.family, plugin.code), {}), user.get((plugin.family, plugin.code), {}), user_id=user_id, decrypt=False) for plugin in plugins]


async def read_catalogue(session: AsyncSession, user: User, *, family: str | None = None, plugin_code: str | None = None) -> PluginSettingsCatalogResponse:
    """The plugins that declare settings, and the state of each field for ``user``."""
    plugins = list(_plugins(family, plugin_code))
    if not plugins:
        return PluginSettingsCatalogResponse(plugins=[])
    system, own = await _rows_by_plugin(session, user.id)
    all_states = await asyncio.to_thread(_resolve_catalogue, plugins, system, own, user.id)
    managed = _is_managed()
    entries = []
    for plugin, states in zip(plugins, all_states, strict=True):
        fields = [_field_read(state, is_admin=user.is_superuser) for state in states if not (managed and state.locked)]
        if fields:
            # Judged on every field, the hidden ones too: a yes or no, which names none of them (decision N2).
            configured = not missing_field_keys(states)
            entries.append(PluginSettingsPluginRead(family=plugin.family, plugin_code=plugin.code, plugin_name=plugin.name, icon_url=plugin.icon_url, configured=configured, fields=fields))
    return PluginSettingsCatalogResponse(plugins=entries)


# =============================================================================
# Writes
# =============================================================================


@dataclass(frozen=True)
class _Accepted:
    item: PluginSettingWriteItem
    field: PluginSettingField
    value: Any  # the validated value; None for a clear


def _locking_variable(family: str, plugin_code: str, declared: PluginSettingField) -> str | None:
    return next((variable for variable in env_variables(family, plugin_code, declared) if plugin_setting_env_origin(variable) is not None), None)


def _check_item(item: PluginSettingWriteItem, user: User, managed: bool, seen: set[tuple]) -> tuple[_Accepted | None, PluginSettingErrorCode | None, str | None]:  # noqa: C901, PLR0911 — one flat list of refusals
    plugin = _find_plugin(item.family.value, item.plugin_code)
    declared = None
    if plugin is not None:
        declared = next((field for field in plugin.plugin_class.settings_fields if field.key == item.field_key and field.scope.value == item.scope.value), None)
    if plugin is None or declared is None:
        return None, PluginSettingErrorCode.UNKNOWN_FIELD, "no such plugin setting in this scope"
    if declared.scope is SettingScope.SYSTEM:
        locked_by = _locking_variable(plugin.family, plugin.code, declared)
        if locked_by is not None and managed:
            return None, PluginSettingErrorCode.UNKNOWN_FIELD, "no such plugin setting in this scope"
        if not user.is_superuser:
            return None, PluginSettingErrorCode.FORBIDDEN_SCOPE, "only an administrator writes the instance's settings"
        if locked_by is not None:
            return None, PluginSettingErrorCode.LOCKED_BY_ENV, f"set by the environment variable {locked_by}"
    identity = (plugin.family, plugin.code, declared.key, declared.scope.value)
    if identity in seen:
        return None, PluginSettingErrorCode.INVALID_VALUE, "the field appears twice in this write"
    seen.add(identity)
    given = [item.value is not None, item.secret_value is not None, item.clear]
    if sum(given) != 1:
        return None, PluginSettingErrorCode.INVALID_VALUE, "give exactly one of value, secret_value and clear"
    if item.clear:
        return _Accepted(item, declared, None), None, None
    if declared.secret and item.value is not None:
        return None, PluginSettingErrorCode.INVALID_VALUE, "a secret is written in secret_value"
    if not declared.secret and item.secret_value is not None:
        return None, PluginSettingErrorCode.INVALID_VALUE, "this field is not secret: write it in value"
    raw = item.secret_value.get_secret_value() if declared.secret else item.value
    try:
        return _Accepted(item, declared, validate_value(declared, raw)), None, None
    except SettingValueError as error:
        return None, PluginSettingErrorCode.INVALID_VALUE, str(error)


def _result(item: PluginSettingWriteItem, success: bool, error_code: PluginSettingErrorCode | None = None, message: str | None = None) -> PluginSettingWriteResult:
    return PluginSettingWriteResult(family=item.family, plugin_code=item.plugin_code, field_key=item.field_key, scope=item.scope, success=success, error_code=error_code, message=message)


async def _apply(session: AsyncSession, accepted: _Accepted, user: User, subkey: bytes | None) -> None:
    item, declared = accepted.item, accepted.field
    family, code, key = item.family.value, item.plugin_code, declared.key
    is_user = declared.scope is SettingScope.USER
    model = PluginUserSetting if is_user else PluginSystemSetting
    conditions = [model.family == family, model.plugin_code == code, model.field_key == key]
    if is_user:
        conditions.append(PluginUserSetting.user_id == user.id)
    if item.clear:
        await session.execute(delete(model).where(*conditions))
        return
    row = (await session.execute(select(model).where(*conditions))).scalar_one_or_none()
    if row is None:
        row = PluginUserSetting(user_id=user.id, family=family, plugin_code=code, field_key=key) if is_user else PluginSystemSetting(family=family, plugin_code=code, field_key=key)
        session.add(row)
    if declared.secret:
        if subkey is None:  # write_settings derives it before the first secret write
            raise PluginSettingsKeyUnavailable("no key to encrypt the secret with")
        aad = secret_aad(family, code, key, declared.scope.value, user.id if is_user else None)
        row.value_json, row.secret_ciphertext, row.key_id = None, encrypt_secret(subkey, aad, accepted.value), key_id_of(subkey)
    else:
        row.value_json, row.secret_ciphertext, row.key_id = json.dumps(accepted.value), None, None
    row.updated_at = utcnow()
    if not is_user:
        row.updated_by_user_id = user.id


async def write_settings(session: AsyncSession, user: User, items: list[PluginSettingWriteItem]) -> PluginSettingsWriteResponse:
    """Check every item, then write them all in one transaction, or none.

    Raises ``PluginSettingsRefused`` (with every outcome) when an item is refused, ``PluginSettingsKeyUnavailable``
    when a secret cannot be encrypted, ``PluginSettingsConflict`` when a concurrent write collides.
    """
    managed = _is_managed()
    seen: set[tuple] = set()
    checked = [(item, *_check_item(item, user, managed, seen)) for item in items]
    if any(accepted is None for _item, accepted, _code, _message in checked):
        raise PluginSettingsRefused([_result(item, accepted is not None, code, message) for item, accepted, code, message in checked])
    accepted_items = [accepted for _item, accepted, _code, _message in checked]
    subkey = None
    if any(accepted.field.secret and not accepted.item.clear for accepted in accepted_items):
        try:
            subkey = await asyncio.to_thread(settings_subkey)
        except InstanceKeyError as error:
            raise PluginSettingsKeyUnavailable("the instance key cannot be used: see the configuration checks") from error
    try:
        for accepted in accepted_items:
            await _apply(session, accepted, user, subkey)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise PluginSettingsConflict("another write changed the same plugin settings: try again") from error
    logger.info(
        "Plugin settings written",
        user_id=user.id,
        fields=[f"{accepted.item.family.value}/{accepted.item.plugin_code}/{accepted.field.key}:{accepted.field.scope.value}:{'clear' if accepted.item.clear else 'set'}" for accepted in accepted_items],
    )
    return PluginSettingsWriteResponse(results=[_result(accepted.item, True) for accepted in accepted_items], success_count=len(accepted_items))
