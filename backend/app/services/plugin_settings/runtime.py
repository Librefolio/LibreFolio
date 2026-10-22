"""A configured instance: a new plugin instance with the values of its fields bound, ready for one use.

The family runtimes call ``configure_instance`` on every instance they are about to call (``services/assets/core.py``,
``services/fx/runtime.py``), right after creating it. A plugin that declares no field is returned as it is: no database
read, no key. Otherwise the rows are read in a short session of its own — never the caller's, which concurrent calls
(a search runs every provider at once) cannot share — and the values are resolved in a worker thread, because that
reads the environment, secret files and the instance key (``resolver.py``).

What reaches the plugin (D-X13): the instance's values always; the user's values only when the call is made for a user
(``user_id``: search, the probe of a configuration). Prices, history, metadata and every scheduled job are shared by all
users, so they receive the instance's values only. The values are resolved again for every use, never kept in memory
between calls; each instance is new, so one user's values never reach another's call.

A database error does not stop the call: the plugin then gets the environment and the defaults, and the error is
logged. A required field left without a value makes the family boundary refuse the call with ``NOT_CONFIGURED``.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PluginSystemSetting, PluginUserSetting
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.services.plugin_settings.contract import BoundSettings, PluginSettingsMixin
from backend.app.services.plugin_settings.fields import SettingScope
from backend.app.services.plugin_settings.resolver import StoredValue, build_bound_settings

if TYPE_CHECKING:
    from backend.app.services.provider_registry import AbstractProviderRegistry

logger = get_logger(__name__)


def stored_value(row: PluginSystemSetting | PluginUserSetting) -> StoredValue:
    """A row's content, out of the session."""
    return StoredValue(row.value_json, row.secret_ciphertext, row.key_id, row.updated_at)


async def read_plugin_rows(session: AsyncSession, family: str, plugin_code: str, user_id: int | None) -> tuple[dict[str, StoredValue], dict[str, StoredValue] | None]:
    """The instance's rows of one plugin and, when ``user_id`` is given, that user's rows: by field key."""
    system = await session.execute(select(PluginSystemSetting).where(PluginSystemSetting.family == family, PluginSystemSetting.plugin_code == plugin_code))
    system_rows = {row.field_key: stored_value(row) for row in system.scalars()}
    if user_id is None:
        return system_rows, None
    user = await session.execute(select(PluginUserSetting).where(PluginUserSetting.user_id == user_id, PluginUserSetting.family == family, PluginUserSetting.plugin_code == plugin_code))
    return system_rows, {row.field_key: stored_value(row) for row in user.scalars()}


async def bound_settings_for(registry: type[AbstractProviderRegistry], plugin_code: str, *, user_id: int | None = None) -> BoundSettings | None:
    """The values of the plugin ``plugin_code`` of ``registry``'s family for one use, or ``None`` when it declares no field.

    For a caller that cannot bind them itself: the BRIM parse runs in a worker process that re-creates the plugin by its code
    (W-BS), so the parent resolves the values here — the instance's, and the user's when ``user_id`` is given — and hands the
    ``BoundSettings`` over, which pickles. A plugin without fields, or one the registry does not know, gives ``None``: no
    database read, no key.
    """
    family = registry.settings_family()
    plugin_class = registry.get_plugin(plugin_code)
    if family is None or plugin_class is None or not getattr(plugin_class, "settings_fields", ()):
        return None
    instance = plugin_class()
    await configure_instance(instance, family, user_id=user_id)
    return instance.settings


async def configure_instance[PluginT: PluginSettingsMixin](instance: PluginT, family: str, *, user_id: int | None = None) -> PluginT:
    """Bind to ``instance`` the values of its fields: the instance's, and the user's when ``user_id`` is given.

    An object that declares no field — a plugin without settings, or a test double that is not a plugin — is returned
    as it is, as the family boundaries let it through.
    """
    fields = getattr(type(instance), "settings_fields", ())
    if not fields:
        return instance
    plugin_code = instance.provider_code  # type: ignore[attr-defined] — asset and FX providers both have it
    wants_system = any(declared.scope is SettingScope.SYSTEM for declared in fields)
    wants_user = user_id is not None and any(declared.scope is SettingScope.USER for declared in fields)
    system_rows: dict[str, StoredValue] = {}
    user_rows: dict[str, StoredValue] | None = {} if user_id is not None else None
    if wants_system or wants_user:
        try:
            async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
                system_rows, user_rows = await read_plugin_rows(session, family, plugin_code, user_id if wants_user else None)
            if user_id is not None and user_rows is None:
                user_rows = {}
        except SQLAlchemyError as error:
            logger.warning("Plugin settings not read: database error, the environment and the defaults only", family=family, plugin=plugin_code, error=type(error).__name__)
    bound = await asyncio.to_thread(build_bound_settings, family, plugin_code, fields, system_rows, user_rows, user_id=user_id)
    instance.bind_settings(bound)
    return instance
