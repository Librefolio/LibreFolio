"""Schemas of the plugin settings API: ``GET /api/v1/settings/plugins`` and ``PATCH /api/v1/settings/plugins/bulk``.

The catalogue lists, for each plugin that declares settings, whether it is configured, and its fields with their state
for the caller: the value of a plain field, and for a secret only whether it is set and readable. **A secret never
travels back**: no read schema has a field for its value. It is written in ``secret_value`` (``format: password``,
write-only), which no response and no validation message ever repeats: the route also drops the ``input`` FastAPI would
echo in a 422.

A write is all or nothing (the contract of the settings write path): every item is checked, each refusal gets its
code, and when one item is refused nothing is written — the answer is a 422 whose ``detail.results`` lists every item.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AllowInfNan, Field, SecretStr

from backend.app.schemas.common import StrictModel


class PluginSettingFamily(StrEnum):
    """The plugin families whose plugins may declare settings."""

    ASSET = "asset"
    FX = "fx"


class PluginSettingScope(StrEnum):
    """``system``: one value for the instance, written by an administrator; ``user``: each user's own value."""

    USER = "user"
    SYSTEM = "system"


class PluginSettingType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    SELECT = "select"


class PluginSettingSource(StrEnum):
    """Where a field's value comes from: an environment variable, a saved value, the declared default, or nowhere."""

    ENV = "env"
    DB = "db"
    DEFAULT = "default"
    NONE = "none"


class PluginSettingProblem(StrEnum):
    """Why a field has no usable value although something sets it.

    ``unreadable``: a saved secret the current instance key cannot read (a lost or replaced key, a restore without it):
    enter it again. ``invalid_env``: the variable that sets it holds a value the field refuses, or a ``_FILE`` that
    cannot be read. ``invalid_stored``: a saved value the field refuses now; the default applies.
    """

    UNREADABLE = "unreadable"
    INVALID_ENV = "invalid_env"
    INVALID_STORED = "invalid_stored"


class PluginSettingErrorCode(StrEnum):
    """Why a write item is refused."""

    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    FORBIDDEN_SCOPE = "FORBIDDEN_SCOPE"
    LOCKED_BY_ENV = "LOCKED_BY_ENV"
    INVALID_VALUE = "INVALID_VALUE"


#: A plain value as it travels in JSON. A number is finite: infinity and NaN are refused here, at the edge (H-32), as
#: ``fields.validate_value`` refuses them before a value is saved.
PluginSettingPlainValue = str | int | Annotated[float, AllowInfNan(False)] | bool


class PluginSettingOptionRead(StrictModel):
    """One choice of a ``select`` field."""

    value: str
    label: str = Field(..., description="English label, the fallback when the interface has no translation")
    label_key: str | None = Field(None, description="i18n key of the label, declared by the plugin")


class PluginSettingFieldRead(StrictModel):
    """One field of a plugin, as the caller sees it."""

    key: str
    type: PluginSettingType
    scope: PluginSettingScope
    secret: bool
    required: bool = Field(..., description="Without a value the plugin answers NOT_CONFIGURED")
    label: str = Field(..., description="English label, the fallback when the interface has no translation")
    description: str
    label_key: str | None = None
    description_key: str | None = None
    options: list[PluginSettingOptionRead] = Field(default_factory=list)
    min_length: int | None = None
    max_length: int | None = None
    minimum: float | None = None
    maximum: float | None = None
    default: PluginSettingPlainValue | None = Field(None, description="The declared default; a secret has none")
    value: PluginSettingPlainValue | None = Field(None, description="The current value of a plain field; never set for a secret")
    is_set: bool = Field(..., description="An environment variable or a saved value sets the field (readable or not); a default does not count")
    source: PluginSettingSource
    locked: bool = Field(..., description="An environment variable sets the field: it cannot be written here")
    env_variable: str | None = Field(None, description="The variable that sets a locked field (administrators only)")
    editable: bool = Field(..., description="The caller may write this field now")
    problem: PluginSettingProblem | None = None
    updated_at: datetime | None = Field(None, description="When the saved value last changed")


class PluginSettingsPluginRead(StrictModel):
    """A plugin and its fields."""

    family: PluginSettingFamily
    plugin_code: str
    plugin_name: str
    icon_url: str | None = Field(None, description="The plugin's icon, as its family's provider list publishes it (a remote URL or a path of this instance); null when it has none, and the app shows a neutral icon")
    configured: bool = Field(
        ...,
        description="Every required field has a usable value and no environment variable is invalid: otherwise the plugin answers its calls with NOT_CONFIGURED. Judged on every field, the ones not listed here too",
    )
    fields: list[PluginSettingFieldRead]


class PluginSettingsCatalogResponse(StrictModel):
    """Every plugin that declares settings the caller can see, with their state for the caller."""

    plugins: list[PluginSettingsPluginRead]


class PluginSettingWriteItem(StrictModel):
    """One field to write or to clear.

    A plain value goes in ``value``, a secret in ``secret_value``; ``clear`` deletes the saved value, so the default
    (or nothing) applies again. Exactly one of the three.
    """

    family: PluginSettingFamily
    plugin_code: str = Field(..., min_length=1, max_length=64)
    field_key: str = Field(..., min_length=1, max_length=64)
    scope: PluginSettingScope
    value: PluginSettingPlainValue | None = Field(None, description="The new value of a plain field")
    secret_value: SecretStr | None = Field(None, description="The new value of a secret field: write-only, never returned")
    clear: bool = Field(False, description="Delete the saved value")


class PluginSettingsBulkWrite(StrictModel):
    """The items of one write: all are applied, or none."""

    items: list[PluginSettingWriteItem] = Field(..., min_length=1, max_length=100)


class PluginSettingWriteResult(StrictModel):
    """The outcome of one item. ``message`` says why it was refused, never with the value."""

    family: PluginSettingFamily
    plugin_code: str
    field_key: str
    scope: PluginSettingScope
    success: bool
    error_code: PluginSettingErrorCode | None = None
    message: str | None = None


class PluginSettingsWriteResponse(StrictModel):
    """Every item written. A refused write answers 422 with the same shape in ``detail``, and writes nothing."""

    results: list[PluginSettingWriteResult]
    success_count: int
