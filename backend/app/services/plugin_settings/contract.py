"""The contract between a plugin and its settings: what the family bases inherit, and what the core binds before a call.

Every family base that supports settings (``AssetSourceProvider``, ``FXRateProvider``) inherits
``PluginSettingsMixin``:

- ``settings_fields``: the fields the plugin declares (``fields.py``), empty by default: a plugin that declares none
  is called exactly as before, with no database read and no key;
- ``test_only``: a plugin that exists for the tests, never listed to users (catalogue, provider lists, settings), and
  outside test mode not served at all: the registries do not find it (X-R44);
- ``settings``: the values the core bound to this instance (``runtime.py``), or, on an instance nobody configured,
  the declared defaults and no secret.

The core binds the values on a new instance right before each use, never through the constructor. A plugin reads them
in its operations, never in ``__init__``: ``self.settings.get("key")`` for a plain value, ``self.settings.secret("key")``
for a secret. It never returns a secret in its results and never logs one; the core masks the secrets it delivered in
the errors and the logs of the call (``utils/runtime/secret_masking.py``), as a last line of defence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope


class BoundSettings:
    """The values of one plugin's fields for one use: plain values, secrets, and the required fields left without one.

    ``fingerprint`` identifies the values for the caches that depend on them (``resolver.settings_fingerprint``); it
    is empty for an instance nobody configured. The ``repr`` names the secret fields and never shows their values.
    """

    __slots__ = ("_fields", "_fingerprint", "_missing", "_secrets", "_values")

    def __init__(  # noqa: PLR0913 — the parts of one binding
        self,
        fields: tuple[PluginSettingField, ...],
        values: Mapping[str, Any],
        secrets: Mapping[str, str],
        missing: tuple[str, ...] = (),
        *,
        fingerprint: str = "",
    ):
        self._fields = {declared.key: declared for declared in fields}
        self._values = dict(values)
        self._secrets = dict(secrets)
        self._missing = tuple(missing)
        self._fingerprint = fingerprint

    @classmethod
    def unbound(cls, fields: tuple[PluginSettingField, ...]) -> BoundSettings:
        """What an instance nobody configured sees: each plain field's default, no secret."""
        values = {declared.key: declared.default for declared in fields if not declared.secret and declared.default is not None}
        missing = tuple(declared.key for declared in fields if declared.required and declared.key not in values)
        return cls(fields, values, {}, missing)

    def _declared(self, key: str) -> PluginSettingField:
        declared = self._fields.get(key)
        if declared is None:
            raise KeyError(f"{key!r} is not a declared setting")
        return declared

    def get(self, key: str, default: Any = None) -> Any:
        """The value of the plain field ``key``, or ``default`` when it has none. A secret is read with ``secret()``."""
        if self._declared(key).secret:
            raise KeyError(f"{key!r} is a secret: read it with settings.secret()")
        return self._values.get(key, default)

    def secret(self, key: str) -> str | None:
        """The value of the secret field ``key``, or ``None`` when it has none."""
        if not self._declared(key).secret:
            raise KeyError(f"{key!r} is not a secret: read it with settings.get()")
        return self._secrets.get(key)

    @property
    def missing(self) -> tuple[str, ...]:
        """The fields without a usable value: a required one left without a value, or one whose environment variable is
        set but invalid. The plugin is not configured while one is left."""
        return self._missing

    @property
    def fingerprint(self) -> str:
        """Identifies these values in a cache key; empty when nothing was bound."""
        return self._fingerprint

    def secret_values(self) -> frozenset[str]:
        """The secret values bound here: the core masks them in the errors and the logs of a call."""
        return frozenset(value for value in self._secrets.values() if value)

    @property
    def carries_user_secrets(self) -> bool:
        """Whether a secret of the caller's own (a ``user`` field) is bound here: a value the caller chose.

        The core then hides whole every error text that shows a secret, instead of masking it in place: masking a value
        the caller chose would tell whether it occurs in the text, and so, a character at a time, the instance secret
        beside it (``call_provider``).
        """
        return any(value and self._fields[key].scope is SettingScope.USER for key, value in self._secrets.items() if key in self._fields)

    def plain_values(self) -> dict[str, Any]:
        """A copy of the plain values, by key."""
        return dict(self._values)

    def __repr__(self) -> str:
        return f"BoundSettings(values={self._values!r}, secrets_set={sorted(self._secrets)!r}, missing={list(self._missing)!r})"


class PluginSettingsMixin:
    """The settings part of a plugin family base."""

    settings_fields: ClassVar[tuple[PluginSettingField, ...]] = ()
    test_only: ClassVar[bool] = False
    _lf_bound_settings: BoundSettings | None = None

    @property
    def settings(self) -> BoundSettings:
        """The values bound to this instance, or the declared defaults when the core bound none."""
        bound = self._lf_bound_settings
        return bound if bound is not None else BoundSettings.unbound(type(self).settings_fields)

    def bind_settings(self, bound: BoundSettings) -> None:
        """Called by the core on a new instance, before the call: never by a plugin."""
        self._lf_bound_settings = bound
