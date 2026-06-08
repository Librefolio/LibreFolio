"""
Settings schemas for LibreFolio.

Schemas for user settings and global settings management.
"""

from typing import Literal, Optional

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

    pass


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
        "description": "Comma-separated HH:MM times for daily history sync (server local time)",
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
}
