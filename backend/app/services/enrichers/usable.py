"""Whether an enricher can be used now (plan 68, B2): served by the registry, and no required setting left empty.

Served: installed, not test-only outside test mode, and listed by ``LIBREFOLIO_ENRICHERS_ENABLED`` when it is set (the
registry's gate, project 76 X1). Configured: the rule of the other families' boundary (``plugin_settings``,
project 76 N1): ``configure_instance`` binds the instance's values, and ``BoundSettings.missing`` names a required field
left without one. An enricher's settings are the instance's only (the family has no personal fields): no user is
involved, so the weekly job and a user's request see the same answer.
"""

from __future__ import annotations

from collections.abc import Iterable

from backend.app.services.enrichers.base import EnricherPlugin
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.readiness import plugins_readiness
from backend.app.services.plugin_settings.runtime import configure_instance

#: The error code of a read refused because a required setting of the enricher is empty.
NOT_CONFIGURED = "NOT_CONFIGURED"


async def bind_settings(plugin: EnricherPlugin) -> tuple[str, ...]:
    """Bind the instance's values to ``plugin``; the required settings it lacks (empty: it can be used).

    A test double that is not a plugin has no settings: it is used as it is, as the other families' boundary does.
    """
    if not isinstance(plugin, PluginSettingsMixin):
        return ()
    await configure_instance(plugin, EnricherRegistry.settings_family(), plugin_code=plugin.code)
    return tuple(plugin.settings.missing)


async def configured_enricher(code: str) -> tuple[EnricherPlugin | None, tuple[str, ...]]:
    """The instance of ``code`` with its settings bound, and the required settings it lacks (empty: it can be used).

    ``(None, ())`` when the registry does not serve it.
    """
    if EnricherRegistry.get_plugin(code) is None:
        return None, ()
    plugin = EnricherRegistry.get_plugin_instance(code)
    if plugin is None:
        return None, ()
    return plugin, await bind_settings(plugin)


async def usable_codes(codes: Iterable[str]) -> set[str]:
    """The codes among ``codes`` that can be used now: served and configured (one short read of the settings)."""
    served = [code for code in dict.fromkeys(codes) if EnricherRegistry.get_plugin(code) is not None]
    if not served:
        return set()
    readiness = await plugins_readiness(EnricherRegistry.settings_family(), served, user_id=None)
    return {code for code in served if readiness[code].configured}
