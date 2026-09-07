"""
Settings schemas for LibreFolio.

Schemas for user settings and global settings management, plus
SETTINGS_REGISTRY: the declarative catalogue of every known setting key.
"""

from dataclasses import dataclass
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import BaseListResponse
from backend.app.utils.datetime_utils import UTCDateTime

# ============================================================================
# USER SETTINGS
# ============================================================================


class UserSettingsRead(BaseModel):
    """User settings response schema."""

    language: str = Field(..., description="Preferred language (en, it, fr, es)")
    base_currency: str = Field(..., description="Base currency for display (ISO 4217)")
    theme: Literal["light", "dark", "auto"] = Field(..., description="UI theme")
    avatar_url: Optional[str] = Field(None, description="URL to user avatar image")


class UserSettingsUpdate(BaseModel):
    """User settings update request. All fields optional."""

    language: Optional[str] = Field(None, min_length=2, max_length=5)
    base_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    theme: Optional[Literal["light", "dark", "auto"]] = None
    avatar_url: Optional[str] = Field(None, max_length=500, description="URL to user avatar image")


# ============================================================================
# GLOBAL SETTINGS
# ============================================================================


class GlobalSettingRead(BaseModel):
    """Global setting response schema."""

    key: str = Field(..., description="Setting key")
    value: str = Field(..., description="Setting value (as string)")
    value_type: str = Field(..., description="Value type: string, int, bool, json")
    description: Optional[str] = Field(None, description="Human-readable description")
    updated_at: Optional[UTCDateTime] = Field(None, description="Last update timestamp")
    updated_by: Optional[int] = Field(None, description="User ID who last updated")

    model_config = {"from_attributes": True}


class GlobalSettingBulkItem(BaseModel):
    """Single global setting update item."""

    key: str
    value: str

    model_config = ConfigDict(extra="forbid")


class GlobalSettingBulkUpdate(BaseModel):
    """Bulk global setting update request."""

    items: list[GlobalSettingBulkItem]

    model_config = ConfigDict(extra="forbid")


class GlobalSettingsListResponse(BaseListResponse[GlobalSettingRead]):
    """Response for listing all global settings."""


class GlobalSettingsInitializeResponse(BaseModel):
    """Response after initializing global settings with default values."""

    message: str = Field(..., description="Human-readable summary of the operation")


# ============================================================================
# SCHEDULER (ADMIN)
# ============================================================================


class SchedulerJobStateInfo(BaseModel):
    """Last-execution info for a single scheduler job."""

    last_run_at: Optional[str] = Field(None, description="ISO-8601 datetime (with timezone) of the last run")
    last_duration_s: Optional[float] = Field(None, description="Duration of the last run, in seconds")
    last_status: Optional[str] = Field(None, description="Outcome of the last run: ok, partial, or error")
    last_items_ok: int = Field(..., description="Items processed successfully in the last run")
    last_items_err: int = Field(..., description="Items that failed in the last run")


class SchedulerStateResponse(BaseModel):
    """Scheduler state: last-run info for each job plus server/scheduler clocks."""

    current_price: SchedulerJobStateInfo
    history_sync: SchedulerJobStateInfo
    server_tz: str = Field(..., description="Server timezone (always UTC)")
    server_now_utc: str = Field(..., description="Current server UTC wall clock, HH:MM")
    scheduler_timezone: str = Field(..., description="IANA timezone used to evaluate scheduler days/times")


class SchedulerLogCurrentPriceItem(BaseModel):
    """Per-asset result inside a current-price refresh log entry."""

    asset_id: int
    name: str
    ok: bool
    icon_url: Optional[str] = None
    error: Optional[str] = None


class SchedulerLogHistoryAssetItem(BaseModel):
    """Per-asset result inside a history-sync log entry."""

    asset_id: int
    name: str
    status: str
    icon_url: Optional[str] = None
    errors: Optional[list[str]] = None
    provider: Optional[str] = None
    prices_changed: Optional[int] = None
    events_changed: Optional[int] = None
    points_changed: Optional[int] = Field(None, description="Legacy field name used by log entries written before prices_changed/events_changed existed")


class SchedulerLogHistoryFxItem(BaseModel):
    """Per-FX-pair result inside a history-sync log entry."""

    pair: str
    status: str
    base: Optional[str] = None
    quote: Optional[str] = None
    errors: Optional[list[str]] = None
    provider: Optional[str] = None
    points_changed: int


class SchedulerLogCurrentPriceSummary(BaseModel):
    """Aggregate counts for a current-price refresh run."""

    ok: int
    err: int


class SchedulerLogHistorySyncSummary(BaseModel):
    """Aggregate counts for a history-sync run."""

    assets_ok: int
    assets_err: int
    fx_ok: int
    fx_err: int


class SchedulerLogCurrentPriceEntry(BaseModel):
    """JSONL log entry for a current-price refresh run."""

    ts: str = Field(..., description="ISO-8601 timestamp (with timezone)")
    job: Literal["current_price"] = Field(json_schema_extra={"enum": ["current_price"]})
    duration_s: float
    status: str
    summary: SchedulerLogCurrentPriceSummary
    items: list[SchedulerLogCurrentPriceItem]


class SchedulerLogHistorySyncEntry(BaseModel):
    """JSONL log entry for a history-sync run."""

    ts: str = Field(..., description="ISO-8601 timestamp (with timezone)")
    job: Literal["history_sync"] = Field(json_schema_extra={"enum": ["history_sync"]})
    duration_s: float
    status: str
    summary: SchedulerLogHistorySyncSummary
    assets: list[SchedulerLogHistoryAssetItem]
    fx: list[SchedulerLogHistoryFxItem]


SchedulerLogEntry = Annotated[
    SchedulerLogCurrentPriceEntry | SchedulerLogHistorySyncEntry,
    Field(discriminator="job"),
]
"""Scheduler log entry, discriminated by the ``job`` field."""


class SchedulerLogResponse(BaseModel):
    """Scheduler job log entries, newest first."""

    entries: list[SchedulerLogEntry]


# ============================================================================
# PREDEFINED GLOBAL SETTINGS
# ============================================================================

GLOBAL_SETTINGS_DEFAULTS = {
    # Authentication & Security
    "session_ttl_hours": {
        "value": "24",
        "type": "int",
        "description": "Session cookie TTL in hours (default: 24)",
    },
    "enable_registration": {
        "value": "true",
        "type": "bool",
        "description": "Allow new user registration",
    },
    # placeholder — email verification not implemented (see TODO_FUTURI email server)
    "require_email_verification": {
        "value": "false",
        "type": "bool",
        "description": "Require email verification for new users",
    },
    # File Upload
    "max_file_upload_mb": {
        "value": "10",
        "type": "int",
        "description": "Max file upload size in MB",
    },
    # Market Data Scheduler
    "scheduler_enabled": {
        "value": "true",
        "type": "bool",
        "description": "Enable automatic market data sync (scheduler daemon)",
    },
    "scheduler_current_price_frequency_minutes": {
        "value": "10",
        "type": "int",
        "description": "Minutes between current-price refresh cycles (1-1440)",
    },
    "scheduler_history_sync_times": {
        "value": "06:00,23:00",
        "type": "str",
        "description": "Comma-separated HH:MM local times for history sync in scheduler_timezone",
    },
    "scheduler_history_sync_days": {
        "value": "mon,tue,wed,thu,fri,sat",
        "type": "str",
        "description": "Comma-separated days of week for history sync (mon,tue,wed,thu,fri,sat,sun)",
    },
    "scheduler_history_sync_horizon_days": {
        "value": "14",
        "type": "int",
        "description": "Rolling horizon in days for history sync (1-365)",
    },
    "scheduler_timezone": {
        "value": "UTC",
        "type": "str",
        "description": "IANA timezone used to store and evaluate scheduler history-sync days and times",
    },
    # Display
    "default_currency": {
        "value": "EUR",
        "type": "str",
        "description": "Default display currency for new users",
    },
    "default_language": {
        "value": "en",
        "type": "str",
        "description": "Default language for new users (en, it, fr, es)",
    },
    "default_theme": {
        "value": "auto",
        "type": "str",
        "description": "Default theme for new users (light, dark, auto)",
    },
}


# ============================================================================
# SETTINGS REGISTRY
# ============================================================================


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """
    Declarative metadata for one known setting.

    Attributes:
        key: Storage key — the `GlobalSetting` row key for global settings,
            the `UserSettings` column name for per-user settings.
        location: Where the setting lives: "user" (typed column on the
            per-user UserSettings row) or "global" (key-value row in the
            admin-managed GlobalSetting table).
        value_type: Stored value type ("str", "int", "bool", "json").
        description: One-line human-readable summary.
    """

    key: str
    location: Literal["user", "global"]
    value_type: str
    description: str


def _global_spec(key: str) -> SettingSpec:
    """Build a global SettingSpec, deriving type/description from GLOBAL_SETTINGS_DEFAULTS (single source)."""
    config = GLOBAL_SETTINGS_DEFAULTS[key]
    return SettingSpec(key=key, location="global", value_type=config["type"], description=config["description"])


class SETTINGS_REGISTRY:
    """
    Central registry of every known setting key.

    Two storage models, one lookup point:

    - `SETTINGS_REGISTRY.user` — per-user preferences held as typed columns on
      the UserSettings row (one row per user);
    - `SETTINGS_REGISTRY.global_` — instance-wide settings held as key-value
      rows in the GlobalSetting table (admin-managed; defaults seeded from
      GLOBAL_SETTINGS_DEFAULTS, which stays the single source of defaults).

    Call sites reference registry constants instead of re-declaring raw string
    literals:

        await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key, "EUR")

    Alembic migrations and tests that deliberately exercise raw keys are the
    legitimate exceptions.
    """

    class user:
        """Per-user settings — typed columns on the UserSettings row."""

        BASE_CURRENCY = SettingSpec(key="base_currency", location="user", value_type="str", description="Base currency for display (ISO 4217)")
        LANGUAGE = SettingSpec(key="language", location="user", value_type="str", description="Preferred language (en, it, fr, es)")
        THEME = SettingSpec(key="theme", location="user", value_type="str", description="UI theme (light, dark, auto)")
        AVATAR_URL = SettingSpec(key="avatar_url", location="user", value_type="str", description="URL to user avatar image")

        @classmethod
        def all(cls) -> tuple[SettingSpec, ...]:
            """All registered per-user setting specs."""
            return tuple(v for v in vars(cls).values() if isinstance(v, SettingSpec))

    class global_:
        """Global settings — key-value rows in the GlobalSetting table."""

        # Authentication & Security
        SESSION_TTL_HOURS = _global_spec("session_ttl_hours")
        ENABLE_REGISTRATION = _global_spec("enable_registration")
        REQUIRE_EMAIL_VERIFICATION = _global_spec("require_email_verification")
        # File Upload
        MAX_FILE_UPLOAD_MB = _global_spec("max_file_upload_mb")
        # Market Data Scheduler
        SCHEDULER_ENABLED = _global_spec("scheduler_enabled")
        SCHEDULER_CURRENT_PRICE_FREQUENCY_MINUTES = _global_spec("scheduler_current_price_frequency_minutes")
        SCHEDULER_HISTORY_SYNC_TIMES = _global_spec("scheduler_history_sync_times")
        SCHEDULER_HISTORY_SYNC_DAYS = _global_spec("scheduler_history_sync_days")
        SCHEDULER_HISTORY_SYNC_HORIZON_DAYS = _global_spec("scheduler_history_sync_horizon_days")
        SCHEDULER_TIMEZONE = _global_spec("scheduler_timezone")
        # Display
        DEFAULT_CURRENCY = _global_spec("default_currency")
        DEFAULT_LANGUAGE = _global_spec("default_language")
        DEFAULT_THEME = _global_spec("default_theme")

        @classmethod
        def all(cls) -> tuple[SettingSpec, ...]:
            """All registered global setting specs (one per GLOBAL_SETTINGS_DEFAULTS entry)."""
            return tuple(v for v in vars(cls).values() if isinstance(v, SettingSpec))


# ============================================================================
# CACHE ADMIN
# ============================================================================


class CacheStatusEntry(BaseModel):
    """Status of a single named cache."""

    name: str = Field(..., description="Unique cache name")
    current_size: int = Field(..., description="Current number of entries")
    maxsize: int = Field(..., description="Maximum number of entries before W-TinyLFU eviction")
    ttl_seconds: float = Field(..., description="Default time-to-live for entries, in seconds")


class CacheStatusResponse(BaseListResponse[CacheStatusEntry]):
    """Response for listing all registered caches with their stats."""


class CacheClearResponse(BaseModel):
    """Response after clearing one or all caches."""

    cleared_count: int = Field(..., description="Number of caches cleared (1 for a single-cache clear)")
    name: Optional[str] = Field(None, description="Name of the cleared cache (null when clearing all)")
    message: str = Field(..., description="Human-readable summary of the operation")
