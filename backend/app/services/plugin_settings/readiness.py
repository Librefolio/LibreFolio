"""Is a plugin configured, and what is missing: ONE check for every plugin (project 76, N1; plan §3.9).

A plugin with a required setting left without a value answers every call with ``NOT_CONFIGURED`` (the family boundaries:
``assets/core.call_provider``, ``fx/runtime.call_fx_provider``). The interface and the writes that would put such a plugin
to use (a search, an assignment, an FX route) ask the same question BEFORE a call, here:

- **The same rule as the boundary.** ``configured`` is true exactly when the values a call would receive leave nothing
  missing (``BoundSettings.missing``): the plugin's own fields (``resolver.missing_field_keys``) and the fields of the
  shared groups it reads, named ``<group>.<field>`` (``contract.qualified_missing``, the one function both use).
- **The database and the environment only.** One short session reads the instance's rows of the plugins asked, the rows
  of their groups and the caller's rows; the environment and the instance key's id come from the resolver. No call to
  the source, no secret decrypted: a stored secret counts as set when the current key can read it.
- **What a caller may be told.** ``missing`` names the fields to set, except, in the managed profile, a field an
  environment variable locks: the hoster sets it and the customer never sees it (decision N2). ``configured`` still
  counts it.

Resolving reads the environment, secret files and the instance key: it runs in a worker thread.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.config.plugins import plugin_setting_env_origin
from backend.app.db.models import PluginSystemSetting, PluginUserSetting
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.services.plugin_settings.contract import qualified_missing
from backend.app.services.plugin_settings.fields import env_variables
from backend.app.services.plugin_settings.groups import GROUP_FAMILY, SettingsGroup, plugin_groups
from backend.app.services.plugin_settings.resolver import FieldState, StoredValue, missing_field_keys, resolve_plugin_fields
from backend.app.services.plugin_settings.runtime import stored_value

logger = get_logger(__name__)


@dataclass(frozen=True)
class PluginReadiness:
    """Whether a plugin is configured, and the settings a caller may be told to set (``<group>.<field>`` for a group's)."""

    configured: bool
    missing: tuple[str, ...] = ()
    #: Why it is not configured (N2b): ``missing_fields`` (a required value to set), or ``invalid_locked_setting`` (a
    #: field an environment variable locks has an invalid value: it is fixed on the server); None when configured.
    reason: str | None = field(default=None, compare=False)
    #: The variables with an invalid value, outside the managed profile (in it the hoster's variables are never named).
    variables: tuple[str, ...] = field(default=(), compare=False)
    #: The plugin's rows could not be read (a database error): the answer comes from the environment and the defaults
    #: only, and a write must not rely on it (N2b: 503). Compared neither: ``configured`` and ``missing`` are the verdict.
    settings_unavailable: bool = field(default=False, compare=False)


#: A plugin that declares nothing, or one its registry does not know: nothing can be missing.
READY = PluginReadiness(True, ())


def _registry(family: str):
    # Imported here: the settings service imports every family's registry, and the registries import the settings.
    from backend.app.services.plugin_settings.service import FAMILY_REGISTRIES  # noqa: PLC0415 — see above

    return FAMILY_REGISTRIES.get(family)


def plugin_may_be_unconfigured(family: str, code: str, plugin_class: type | None) -> bool:
    """Whether ``plugin_class`` (``code`` of ``family``) can be not configured, so that its rows must be read: it reads a
    shared group, declares a required field, or a field whose environment variable is set (an invalid value leaves it
    missing). A plugin whose fields are all optional and unset by the environment (the core's call limits alone, U4) is
    always configured: no database to read."""
    if plugin_class is None:
        return False
    if plugin_groups(plugin_class):
        return True
    fields = getattr(plugin_class, "settings_fields", ())
    if any(field.required for field in fields):
        return True
    return any(plugin_setting_env_origin(variable) is not None for field in fields for variable in env_variables(family, code, field))


@dataclass(frozen=True)
class _Asked:
    code: str
    fields: tuple
    groups: tuple[SettingsGroup, ...]


async def _rows(family: str, asked: list[_Asked], user_id: int | None) -> tuple[dict, dict, bool]:
    """The rows the check needs, in one short session of its own: the instance's of the plugins asked and of their groups,
    and the caller's of the plugins asked. A database error leaves them empty (the environment and the defaults decide),
    and is logged: what the boundary does (``runtime.configure_instance``), so the check and a call still agree."""
    codes = [entry.code for entry in asked]
    group_names = sorted({group.name for entry in asked for group in entry.groups})
    system: dict[tuple[str, str], dict[str, StoredValue]] = {}
    user: dict[str, dict[str, StoredValue]] = {}
    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            condition = (PluginSystemSetting.family == family) & PluginSystemSetting.plugin_code.in_(codes)
            if group_names:
                condition = or_(condition, (PluginSystemSetting.family == GROUP_FAMILY) & PluginSystemSetting.plugin_code.in_(group_names))
            for row in (await session.execute(select(PluginSystemSetting).where(condition))).scalars():
                system.setdefault((row.family, row.plugin_code), {})[row.field_key] = stored_value(row)
            if user_id is not None:
                statement = select(PluginUserSetting).where(PluginUserSetting.user_id == user_id, PluginUserSetting.family == family, PluginUserSetting.plugin_code.in_(codes))
                for row in (await session.execute(statement)).scalars():
                    user.setdefault(row.plugin_code, {})[row.field_key] = stored_value(row)
    except SQLAlchemyError as error:
        logger.warning("Plugin readiness: rows not read, the environment and the defaults only", family=family, error=type(error).__name__)
        return system, user, True
    return system, user, False


def _judge(family: str, asked: list[_Asked], system: dict, user: dict, user_id: int | None, managed: bool, unavailable: bool = False) -> dict[str, PluginReadiness]:  # noqa: PLR0913 — the rows, the caller and the profile
    """The readiness of each plugin asked, from its fields' and its groups' states (no secret decrypted). Synchronous."""
    group_states: dict[str, list[FieldState]] = {}
    answers: dict[str, PluginReadiness] = {}
    for entry in asked:
        own = resolve_plugin_fields(family, entry.code, entry.fields, system.get((family, entry.code), {}), user.get(entry.code, {}) if user_id is not None else None, user_id=user_id, decrypt=False)
        for group in entry.groups:
            if group.name not in group_states:
                group_states[group.name] = resolve_plugin_fields(GROUP_FAMILY, group.name, group.fields, system.get((GROUP_FAMILY, group.name), {}), None, user_id=None, decrypt=False)
        every = qualified_missing(missing_field_keys(own), {group.name: missing_field_keys(group_states[group.name]) for group in entry.groups})
        hidden = set()
        if managed:
            hidden = {state.field.key for state in own if state.locked}
            hidden |= {f"{group.name}.{state.field.key}" for group in entry.groups for state in group_states[group.name] if state.locked}
        # An invalid value in a variable that locks a field is fixed on the server, whatever else is missing (N2b)
        invalid = [state.env_variable for state in own if state.locked and state.problem == "invalid_env"]
        invalid += [state.env_variable for group in entry.groups for state in group_states[group.name] if state.locked and state.problem == "invalid_env"]
        reason = None if not every else ("invalid_locked_setting" if invalid else "missing_fields")
        variables = () if managed or not every else tuple(variable for variable in invalid if variable)
        answers[entry.code] = PluginReadiness(configured=not every, missing=tuple(key for key in every if key not in hidden), reason=reason, variables=variables, settings_unavailable=unavailable)
    return answers


async def plugins_readiness(family: str, codes: Sequence[str], *, user_id: int | None) -> dict[str, PluginReadiness]:
    """The readiness of the plugins ``codes`` of ``family``, for ``user_id`` (None: a call made for nobody). One entry per
    code asked; a code the family's registry does not know, or a plugin that declares no field and no group, is ready."""
    registry = _registry(family)
    answers: dict[str, PluginReadiness] = {}
    asked: list[_Asked] = []
    for code in dict.fromkeys(codes):
        plugin_class = registry.get_plugin(code) if registry is not None else None
        if plugin_may_be_unconfigured(family, code, plugin_class):
            asked.append(_Asked(code, getattr(plugin_class, "settings_fields", ()), plugin_groups(plugin_class)))
        else:
            answers[code] = READY
    if asked:
        system, user, unavailable = await _rows(family, asked, user_id)
        managed = get_settings().LIBREFOLIO_PROFILE == "managed"
        answers.update(await asyncio.to_thread(_judge, family, asked, system, user, user_id, managed, unavailable))
    return {code: answers[code] for code in dict.fromkeys(codes)}


async def plugin_readiness(family: str, code: str, *, user_id: int | None) -> PluginReadiness:
    """The readiness of one plugin: ``plugins_readiness`` for one code."""
    return (await plugins_readiness(family, [code], user_id=user_id))[code]
