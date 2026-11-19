"""The instance's call limits as settings of the core (project 76, U4; plan §3.5 «Il limite»).

Five optional system integers, one per window of the call counter (``services/platform/call_counter.py``):
``call_limit_minute`` … ``call_limit_month``. Empty: no limit; 0: the plugin is stopped. The core declares them, not
the plugin, on whoever owns the count:

- a plugin that reaches an external service (``calls_external_service``) and reads no credit-sharing group: at its
  registration (``AbstractPluginRegistry.register``);
- a shared group with ``shares_credits``: at its registration (``groups.register_group``).

They are fields like any other: stored in ``plugin_system_settings``, locked by their variable
(``LIBREFOLIO_PLUGIN_<FAMILY>_<CODE>_CALL_LIMIT_<WINDOW>``), part of the settings fingerprint (so a changed limit lifts
the limit pause, U2b), read by the boundaries through ``call_counter.call_owner``.

This module imports only the fields: the registry base and the groups import it.
"""

from __future__ import annotations

from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType

#: The windows of the call counter, shortest first (``call_counter.WINDOWS``).
_WINDOWS = ("minute", "hour", "day", "week", "month")

#: The keys of the five fields, in window order.
CALL_LIMIT_KEYS: tuple[str, ...] = tuple(f"call_limit_{window}" for window in _WINDOWS)

#: The five fields. Their translated label and description (project 76, S2a) let the search of the Plugins tab find
#: «Limite giornaliero»; the boxes themselves show the window's name.
CALL_LIMIT_FIELDS: tuple[PluginSettingField, ...] = tuple(
    PluginSettingField(
        key=f"call_limit_{window}",
        type=SettingType.INTEGER,
        scope=SettingScope.SYSTEM,
        label=f"Calls per {window}",
        description=f"The most calls this instance makes to the service in one {window} (UTC, calendar). Empty: no limit; 0: stopped.",
        label_key=f"pluginSettings.calls.limitField.{window}.label",
        description_key=f"pluginSettings.calls.limitField.{window}.description",
        required=False,
        default=None,
        minimum=0,
    )
    for window in _WINDOWS
)


def with_call_limits(fields: tuple[PluginSettingField, ...]) -> tuple[PluginSettingField, ...]:
    """``fields``, then the call-limit fields whose key is missing, in window order. A key already declared is kept as
    declared (a test plugin's own limit, with its default). Idempotent."""
    declared = {field.key for field in fields}
    return tuple(fields) + tuple(field for field in CALL_LIMIT_FIELDS if field.key not in declared)
