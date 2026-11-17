"""Shared settings groups: values that several plugins read, declared once by the core (project 76, G1).

The need: one CoinGecko key, read by the price plugin and by the profile enricher; tomorrow the same for other pairs of
plugins of one source. Without a group each plugin declares its own ``api_key``: two values, two variables, and the
credits of one account seen as two. A plugin may not read another plugin's settings either (no dependency between
plugins). So a GROUP is declared here, by the core, once:

- a group has a name (``coingecko``) and its own fields, ``system`` ones only in this first version: one value for the
  whole instance, written by an administrator, or set by the environment;
- its rows live in ``plugin_system_settings`` with ``family="group"`` and ``plugin_code=<name>``; no migration, the
  encryption binds a secret to that row as for any plugin (``crypto.secret_aad``);
- its variables are ``LIBREFOLIO_PLUGIN_GROUP_<NAME>_<FIELD>``, owned by the group in the variable registry
  (``claim_env_variables``), so no plugin can read one too;
- a plugin declares ``settings_groups = ("coingecko",)`` and reads ``self.settings.group("coingecko").secret("api_key")``;
  the core binds the group's values beside the plugin's own (``runtime.configure_instance``), masks its secrets, puts
  it in the fingerprint of the cache keys, and leaves the plugin «not configured» while a required group field has no
  value (``coingecko.api_key`` in ``missing``).

This package imports only ``fields``: never a registry or a plugin, which import it. A group registers itself when its
module is imported (one module per group, beside this one), before the plugins that use it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace

from backend.app.config import is_test_mode
from backend.app.services.plugin_settings.call_limits import with_call_limits
from backend.app.services.plugin_settings.fields import (
    FAMILY_RULES,
    FIELD_KEY,
    PluginSettingField,
    SettingsDeclarationError,
    claim_env_variables,
    release_env_variables,
    validate_declaration,
)

#: The family name of a group's rows and variables.
GROUP_FAMILY = "group"


@dataclass(frozen=True)
class SettingsGroup:
    """One group: its name, its English texts (the fallback of ``label_key`` / ``description_key``), its fields."""

    name: str
    label: str
    description: str = ""
    fields: tuple[PluginSettingField, ...] = ()
    label_key: str | None = None
    description_key: str | None = None
    #: A group for the tests only: never listed to users, and not required to have a plugin that uses it
    test_only: bool = False
    #: The plugins that read it spend the credits of one account (CoinGecko's key): they are counted, and limited, on
    #: the group (``family="group"``), not each on its own row (project 76, U2). A plugin reads at most one such group.
    shares_credits: bool = False

    @property
    def has_secrets(self) -> bool:
        """Whether a field of the group is secret: only a family that may hold secrets can use it."""
        return any(declared.secret for declared in self.fields)


_groups: dict[str, SettingsGroup] = {}
_groups_lock = threading.Lock()


def register_group(group: SettingsGroup) -> None:
    """Declare ``group``; ``SettingsDeclarationError`` when its name or a field is invalid, or a variable is another's.

    The fields follow the ``group`` family's rules (``FAMILY_RULES``): system fields only, secrets allowed. The group's
    variables are claimed for it. Registering the same name again replaces the group.
    """
    if not isinstance(group, SettingsGroup):
        raise SettingsDeclarationError("a group is a SettingsGroup")
    if not isinstance(group.name, str) or not FIELD_KEY.fullmatch(group.name):
        raise SettingsDeclarationError(f"group {group.name!r}: a name is lowercase letters, digits and _, a letter first")
    if not isinstance(group.label, str) or not group.label.strip():
        raise SettingsDeclarationError(f"group {group.name!r}: an English label is required")
    if group.shares_credits and isinstance(group.fields, tuple):
        # Its readers spend one account's credits: the core's call limits are the group's (project 76, U4)
        group = replace(group, fields=with_call_limits(group.fields))
    try:
        validate_declaration(group.fields, family=GROUP_FAMILY)
        claim_env_variables(GROUP_FAMILY, group.name, group.fields)
    except SettingsDeclarationError as error:
        raise SettingsDeclarationError(f"group {group.name!r}: {error}") from None
    with _groups_lock:
        _groups[group.name] = group


def release_group(name: str) -> None:
    """Forget a group and its variable claims: for the tests that register a group of their own."""
    with _groups_lock:
        _groups.pop(name, None)
    release_env_variables(GROUP_FAMILY, name)


def is_withheld(group: SettingsGroup | None) -> bool:
    """X-R44 for groups: a test-only group is not served outside test mode, like a test-only plugin. Registered in every
    process (the plugin that reads it is registered everywhere too, withheld by its registry), but never listed nor
    written on a production instance. ``is_test_mode()`` is read at each call."""
    return group is not None and group.test_only and not is_test_mode()


def served_group(name: str) -> SettingsGroup | None:
    """The group ``name`` as the catalogue and the writes see it: None when none is registered, or when it is withheld."""
    group = get_group(name)
    return None if is_withheld(group) else group


def get_group(name: str) -> SettingsGroup | None:
    """The group ``name``, or None when none is registered."""
    with _groups_lock:
        return _groups.get(name)


def all_groups() -> dict[str, SettingsGroup]:
    """Every registered group, by name: a copy."""
    with _groups_lock:
        return dict(_groups)


def plugin_groups(plugin_class: type) -> tuple[SettingsGroup, ...]:
    """The registered groups a plugin class declares, in its order; a name no group answers is left out (the
    registration refused such a plugin already)."""
    groups = []
    for name in getattr(plugin_class, "settings_groups", ()) or ():
        group = get_group(name) if isinstance(name, str) else None
        if group is not None:
            groups.append(group)
    return tuple(groups)


def validate_plugin_groups(plugin_class: type, *, family: str) -> None:
    """Check a plugin's ``settings_groups`` for ``family``; ``SettingsDeclarationError`` on the first problem.

    A tuple of names of registered groups, each once; no group field with the key of one of the plugin's own fields
    (``self.settings.get(key)`` and ``self.settings.group(name).get(key)`` would read two different values under one
    name); a group with a secret only in a family whose plugins may hold secrets.
    """
    names = getattr(plugin_class, "settings_groups", ())
    if not isinstance(names, tuple):
        raise SettingsDeclarationError(f"settings_groups must be a tuple of group names, not a {type(names).__name__}")
    for name in names:
        if not isinstance(name, str):
            raise SettingsDeclarationError(f"settings_groups holds a {type(name).__name__}: a group name is a str")
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise SettingsDeclarationError(f"group {repeated[0]!r} is named twice in settings_groups")
    rules = FAMILY_RULES.get(family)
    own_keys = {declared.key for declared in getattr(plugin_class, "settings_fields", ())}
    sharing = [name for name in names if (group := get_group(name)) is not None and group.shares_credits]
    if len(sharing) > 1:
        raise SettingsDeclarationError(f"settings_groups names two groups that share credits, {sharing[0]!r} and {sharing[1]!r}: a call is counted on one")
    for name in names:
        group = get_group(name)
        if group is None:
            raise SettingsDeclarationError(f"settings_groups names {name!r}, which is no registered group")
        shared = own_keys & {declared.key for declared in group.fields}
        if shared:
            raise SettingsDeclarationError(f"field {sorted(shared)[0]!r} is declared by the plugin and by its group {name!r}")
        if group.has_secrets and (rules is None or not rules.secrets):
            raise SettingsDeclarationError(f"group {name!r} holds a secret, and the plugins of the {family!r} family cannot")


# The groups that ship, one module each, registered on import: here, so that every process that imports the settings
# (the server, a spawned worker) has them before the plugins that read them. At the end: they import this module.
from backend.app.services.plugin_settings.groups import mock as _mock_group  # noqa: E402, F401 — registered on import
