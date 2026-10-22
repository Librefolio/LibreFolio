"""What a plugin declares to have settings: one ``PluginSettingField`` per value, and the checks that go with it.

A plugin lists its fields in ``settings_fields`` (``contract.py``). The declaration is static and checked once, when the
plugin registers (``validate_declaration``): a plugin with an invalid declaration is not registered, like a plugin that
fails to import. A value is checked with ``validate_value`` when it is written and with ``parse_env_value`` when it
comes from the environment. No error message of this module ever contains the value it judged: a secret must not
travel back in a 422, nor reach a log.

``label`` and ``description`` are English text, the fallback for a plugin mounted without translations; ``label_key``
and ``description_key`` name the i18n keys the interface uses, declared here so that the interface never builds a key.

Scope:

- ``user``: a preference of each user, written by that user only and delivered only to the calls that user makes
  (search, the probe of a provider's configuration);
- ``system``: one value for the whole instance, written by an administrator, or set by the environment
  (``LIBREFOLIO_PLUGIN_<FAMILY>_<CODE>_<FIELD>``, or the ``env`` alias a secret field declares), which then locks it.

Every variable belongs to one field of one plugin: a plugin registers only if none of its variables is already read by
another plugin (``claim_env_variables``). Two plugins never share a value through a variable, so a secret meant for one
can never show as the plain value of another.
"""

from __future__ import annotations

import math
import re
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SettingScope(StrEnum):
    """Who a value belongs to."""

    USER = "user"
    SYSTEM = "system"


class SettingType(StrEnum):
    """The kind of value a field holds; only a ``string`` can be secret."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    SELECT = "select"


class SettingsDeclarationError(ValueError):
    """A plugin declares its settings wrongly: the plugin is not registered."""


class SettingValueError(ValueError):
    """A value does not fit its field. The message says why, never what the value was."""


#: A field key: lowercase letters, digits and underscores, a letter first.
FIELD_KEY = re.compile(r"[a-z][a-z0-9_]{0,63}")
#: An explicit environment variable for a field: ``LIBREFOLIO_`` and uppercase letters, digits and underscores.
ENV_ALIAS = re.compile(r"LIBREFOLIO_[A-Z0-9_]{1,100}")
#: The longest text a field holds, secret or not.
STRING_MAX_LENGTH = 4096
#: The shortest secret a field accepts unless it declares otherwise.
SECRET_MIN_LENGTH_DEFAULT = 8
#: No secret field may accept less. A secret is masked wherever its text appears: a short one would hide common words,
#: and a call that echoes what a user sent (the probe of a configuration) would let the user test guesses of it.
SECRET_MIN_LENGTH_FLOOR = 8
#: The prefix of the environment variables derived from a field.
ENV_PREFIX = "LIBREFOLIO_PLUGIN_"

#: The largest integer a setting takes, in absolute value: 2**53 - 1, the last one a JavaScript number (the settings page)
#: and a double hold exactly (X-R43).
MAX_SAFE_INTEGER = 2**53 - 1

_TRUE_WORDS = frozenset({"1", "true", "yes", "on"})
_FALSE_WORDS = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True)
class FamilyRules:
    """What the plugins of one family may declare."""

    #: Whether ``user`` fields reach the plugin: only where calls are made on behalf of a user.
    user_scope: bool
    #: Whether a field may be secret: a Tool calls no external source, so it has nothing to keep secret.
    secrets: bool


#: The families whose plugins may declare settings. Tools join with CP12.
FAMILY_RULES: dict[str, FamilyRules] = {
    "asset": FamilyRules(user_scope=True, secrets=True),
    # The import plugins (W-BS, prepared, no field declared yet): the same rules as the price sources. A parse runs for the user
    # who imports, so a personal value reaches it; an instance value is the administrator's.
    "brim": FamilyRules(user_scope=True, secrets=True),
    # An FX sync serves every user: only the instance's values reach an FX provider.
    "fx": FamilyRules(user_scope=False, secrets=True),
}


@dataclass(frozen=True)
class SettingOption:
    """One choice of a ``select`` field."""

    value: str
    label: str
    label_key: str | None = None


@dataclass(frozen=True)
class PluginSettingField:
    """One value a plugin needs.

    ``default`` is used when nothing else sets the field; a secret has none. ``required`` means the plugin cannot work
    without a value: a call then fails with ``NOT_CONFIGURED`` instead of reaching the plugin. ``min_length`` and
    ``max_length`` bound a text, ``minimum`` and ``maximum`` a number. ``env`` is an explicit variable for a secret
    ``system`` field, read after the derived one: the name a provider read its key from before it declared settings.
    """

    key: str
    type: SettingType
    scope: SettingScope
    label: str
    description: str = ""
    secret: bool = False
    required: bool = False
    default: Any = None
    options: tuple[SettingOption, ...] = ()
    min_length: int | None = None
    max_length: int | None = None
    minimum: float | None = None
    maximum: float | None = None
    label_key: str | None = None
    description_key: str | None = None
    env: str | None = None

    @property
    def effective_min_length(self) -> int:
        """The shortest text accepted: the declared minimum, else 8 for a secret and 1 for any other text."""
        if self.min_length is not None:
            return self.min_length
        return SECRET_MIN_LENGTH_DEFAULT if self.secret else 1

    @property
    def effective_max_length(self) -> int:
        """The longest text accepted: the declared maximum, else 4096."""
        return self.max_length if self.max_length is not None else STRING_MAX_LENGTH

    @property
    def option_values(self) -> tuple[str, ...]:
        """The values a ``select`` field accepts, in their declared order."""
        return tuple(option.value for option in self.options)


def env_name(family: str, plugin_code: str, field_key: str) -> str:
    """The environment variable derived from a field: ``LIBREFOLIO_PLUGIN_<FAMILY>_<CODE>_<FIELD>``, uppercase.

    Every character that is not a letter or a digit becomes ``_``: ``borsa_italiana`` and ``api_key`` give
    ``LIBREFOLIO_PLUGIN_ASSET_BORSA_ITALIANA_API_KEY``.
    """
    parts = (family, plugin_code, field_key)
    return ENV_PREFIX + "_".join(re.sub(r"[^A-Za-z0-9]", "_", part).upper() for part in parts)


def env_variables(family: str, plugin_code: str, declared: PluginSettingField) -> tuple[str, ...]:
    """The variables that can set a ``system`` field, in the order they are read; none for a ``user`` field."""
    if declared.scope is not SettingScope.SYSTEM:
        return ()
    derived = env_name(family, plugin_code, declared.key)
    return (derived,) if declared.env is None or declared.env == derived else (derived, declared.env)


# =============================================================================
# One owner per variable
# =============================================================================

_claims: dict[str, tuple[str, str]] = {}
_claims_lock = threading.Lock()


def claim_env_variables(family: str, plugin_code: str, fields: Iterable[PluginSettingField]) -> None:
    """Reserve the variables of a plugin's fields for it; ``SettingsDeclarationError`` when one is already another's.

    Derived names can meet: ``foo_bar`` with ``baz`` and ``foo`` with ``bar_baz`` both give ``…_FOO_BAR_BAZ``; an alias
    can name any variable. A plugin registering again replaces its own claims. The registries call this right before
    storing a plugin (``provider_registry.py``), so a refused claim leaves the plugin unregistered.
    """
    owner = (family, plugin_code)
    names = [name for declared in fields for name in env_variables(family, plugin_code, declared)]
    if len(set(names)) != len(names):
        raise SettingsDeclarationError("two fields read the same environment variable")
    with _claims_lock:
        for name in names:
            holder = _claims.get(name)
            if holder is not None and holder != owner:
                raise SettingsDeclarationError(f"the environment variable {name} is already read by the {holder[0]} plugin {holder[1]!r}")
        for stale in [name for name, holder in _claims.items() if holder == owner]:
            del _claims[stale]
        _claims.update(dict.fromkeys(names, owner))


def release_env_variables(family: str, plugin_code: str) -> None:
    """Drop the claims of a plugin: for the tests that register a plugin of their own."""
    with _claims_lock:
        for name in [name for name, holder in _claims.items() if holder == (family, plugin_code)]:
            del _claims[name]


def claimed_env_variables() -> dict[str, tuple[str, str]]:
    """Every claimed variable with its plugin, ``(family, plugin_code)``: a copy."""
    with _claims_lock:
        return dict(_claims)


def validate_declaration(fields: object, *, family: str) -> None:
    """Check a plugin's ``settings_fields`` for ``family``; raise ``SettingsDeclarationError`` on the first problem."""
    rules = FAMILY_RULES.get(family)
    if rules is None:
        raise SettingsDeclarationError(f"the plugins of the {family!r} family cannot declare settings")
    if not isinstance(fields, tuple):
        raise SettingsDeclarationError("settings_fields must be a tuple of PluginSettingField")
    seen: set[str] = set()
    for declared in fields:
        if not isinstance(declared, PluginSettingField):
            raise SettingsDeclarationError("settings_fields must be a tuple of PluginSettingField")
        _check_field(declared, rules)
        if declared.key in seen:
            raise SettingsDeclarationError(f"field {declared.key!r} is declared twice")
        seen.add(declared.key)
    aliases = [declared.env for declared in fields if declared.env is not None]
    if len(set(aliases)) != len(aliases):
        raise SettingsDeclarationError("two fields declare the same env alias")


def _check_field(declared: PluginSettingField, rules: FamilyRules) -> None:  # noqa: C901 — one flat list of rules
    name = f"field {declared.key!r}"
    if not isinstance(declared.key, str) or not FIELD_KEY.fullmatch(declared.key):
        raise SettingsDeclarationError(f"{name}: a key is lowercase letters, digits and _, a letter first, at most 64 characters")
    if declared.key.endswith("_file"):
        raise SettingsDeclarationError(f"{name}: a key does not end in _file, the suffix of the variables that name a secret file")
    if not isinstance(declared.type, SettingType) or not isinstance(declared.scope, SettingScope):
        raise SettingsDeclarationError(f"{name}: type and scope must be SettingType and SettingScope values")
    if not isinstance(declared.label, str) or not declared.label.strip():
        raise SettingsDeclarationError(f"{name}: an English label is required")
    if declared.scope is SettingScope.USER and not rules.user_scope:
        raise SettingsDeclarationError(f"{name}: this family delivers only the instance's values, so a field cannot be a user's")
    if declared.scope is SettingScope.USER and declared.required:
        # Prices, history and scheduled jobs are made for nobody: a required personal field would leave them NOT_CONFIGURED
        # for ever, while every user's catalogue says «configured».
        raise SettingsDeclarationError(f"{name}: a personal field cannot be required: the calls made for nobody (prices, scheduled jobs) never receive it")
    if declared.secret:
        if not rules.secrets:
            raise SettingsDeclarationError(f"{name}: this family calls no external source, so a field cannot be secret")
        if declared.type is not SettingType.STRING:
            raise SettingsDeclarationError(f"{name}: only a string can be secret")
        if declared.default is not None:
            raise SettingsDeclarationError(f"{name}: a secret has no default")
        if declared.effective_min_length < SECRET_MIN_LENGTH_FLOOR:
            raise SettingsDeclarationError(f"{name}: a secret accepts at least {SECRET_MIN_LENGTH_FLOOR} characters")
    if declared.env is not None:
        if declared.scope is not SettingScope.SYSTEM or not declared.secret:
            # A plain field shows its value to every user: through an alias it could show a variable that is not its own.
            raise SettingsDeclarationError(f"{name}: only a secret system field has an env alias")
        if not isinstance(declared.env, str) or not ENV_ALIAS.fullmatch(declared.env) or declared.env.endswith("_FILE"):
            raise SettingsDeclarationError(f"{name}: env is LIBREFOLIO_ and uppercase letters, digits and _, not ending in _FILE")
        if declared.env.startswith(ENV_PREFIX):
            raise SettingsDeclarationError(f"{name}: the {ENV_PREFIX} names are the derived ones, not an alias")
    _check_bounds(declared, name)
    if declared.type is SettingType.SELECT:
        values = [option.value for option in declared.options if isinstance(option, SettingOption)]
        if len(values) != len(declared.options) or not values:
            raise SettingsDeclarationError(f"{name}: a select needs a tuple of SettingOption")
        if any(not isinstance(value, str) or not value for value in values) or len(set(values)) != len(values):
            raise SettingsDeclarationError(f"{name}: option values are distinct, non-empty strings")
        if any(not isinstance(option.label, str) or not option.label.strip() for option in declared.options):
            raise SettingsDeclarationError(f"{name}: every option needs an English label")
    elif declared.options:
        raise SettingsDeclarationError(f"{name}: only a select has options")
    if declared.default is not None:
        try:
            validate_value(declared, declared.default)
        except SettingValueError as error:
            raise SettingsDeclarationError(f"{name}: invalid default ({error})") from None


def _check_bounds(declared: PluginSettingField, name: str) -> None:
    textual = declared.type is SettingType.STRING
    numeric = declared.type in (SettingType.NUMBER, SettingType.INTEGER)
    if (declared.min_length is not None or declared.max_length is not None) and not textual:
        raise SettingsDeclarationError(f"{name}: only a string has a length")
    if (declared.minimum is not None or declared.maximum is not None) and not numeric:
        raise SettingsDeclarationError(f"{name}: only a number has bounds")
    if textual:
        low, high = declared.effective_min_length, declared.effective_max_length
        if not (isinstance(low, int) and isinstance(high, int)) or low < 1 or high > STRING_MAX_LENGTH or low > high:
            raise SettingsDeclarationError(f"{name}: lengths must satisfy 1 <= min_length <= max_length <= {STRING_MAX_LENGTH}")
    if numeric:
        for bound in (declared.minimum, declared.maximum):
            if bound is not None and (isinstance(bound, bool) or not isinstance(bound, (int, float)) or not _holdable_number(bound)):
                raise SettingsDeclarationError(f"{name}: bounds are finite numbers, an integer within {MAX_SAFE_INTEGER}")
        if declared.minimum is not None and declared.maximum is not None and declared.minimum > declared.maximum:
            raise SettingsDeclarationError(f"{name}: minimum is above maximum")


def _holdable_number(value: int | float) -> bool:
    """A number a setting can hold (X-R43): an integer within ``MAX_SAFE_INTEGER``, or a finite float. Never raises:
    ``math.isfinite`` raised ``OverflowError`` on an integer past a double."""
    if isinstance(value, int):
        return abs(value) <= MAX_SAFE_INTEGER
    return math.isfinite(value)


def validate_value(declared: PluginSettingField, value: object) -> Any:  # noqa: C901 — one branch per type
    """``value`` as the field stores it; ``SettingValueError`` when it does not fit, with a reason and never the value."""
    if declared.type in (SettingType.STRING, SettingType.SELECT):
        if not isinstance(value, str):
            raise SettingValueError("expected text")
        if declared.type is SettingType.SELECT:
            if value not in declared.option_values:
                raise SettingValueError("not one of the options")
            return value
        if len(value) < declared.effective_min_length:
            raise SettingValueError(f"too short: at least {declared.effective_min_length} characters")
        if len(value) > declared.effective_max_length:
            raise SettingValueError(f"too long: at most {declared.effective_max_length} characters")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise SettingValueError("control characters are not allowed")
        return value
    if declared.type is SettingType.BOOLEAN:
        if not isinstance(value, bool):
            raise SettingValueError("expected true or false")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SettingValueError("expected a number")
    if declared.type is SettingType.INTEGER and not isinstance(value, int):
        raise SettingValueError("expected a whole number")
    if isinstance(value, int) and not _holdable_number(value):
        # X-R43: ``math.isfinite`` raised OverflowError here on an integer past a double, and the request answered 500
        raise SettingValueError(f"too large: at most {MAX_SAFE_INTEGER} in absolute value")
    if not _holdable_number(value):
        raise SettingValueError("expected a finite number")
    if declared.minimum is not None and value < declared.minimum:
        raise SettingValueError(f"below the minimum of {declared.minimum:g}")
    if declared.maximum is not None and value > declared.maximum:
        raise SettingValueError(f"above the maximum of {declared.maximum:g}")
    return value


def parse_env_value(declared: PluginSettingField, text: str) -> Any:
    """The value an environment variable gives a field, checked like a written one.

    A secret is taken as written, as ``env_secret`` gives it; any other text is stripped. A boolean is ``1``, ``true``,
    ``yes``, ``on`` or ``0``, ``false``, ``no``, ``off``, in any case.
    """
    if declared.type is SettingType.STRING:
        return validate_value(declared, text if declared.secret else text.strip())
    stripped = text.strip()
    if declared.type is SettingType.SELECT:
        return validate_value(declared, stripped)
    if declared.type is SettingType.BOOLEAN:
        word = stripped.lower()
        if word in _TRUE_WORDS:
            return True
        if word in _FALSE_WORDS:
            return False
        raise SettingValueError("expected 1, true, yes, on or 0, false, no, off")
    try:
        number: int | float = int(stripped) if declared.type is SettingType.INTEGER else float(stripped)
    except ValueError:
        raise SettingValueError("expected a whole number" if declared.type is SettingType.INTEGER else "expected a number") from None
    return validate_value(declared, number)
