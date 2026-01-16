"""
Global Settings Service - Utility functions for reading global settings.

This module provides simple getter functions for global settings values.
All functions read directly from DB (no cache) to ensure consistency
across multiple workers.

Usage:
    from backend.app.services.global_settings_service import (
        get_session_ttl_hours,
        get_max_upload_mb,
        is_registration_enabled,
    )

    ttl = await get_session_ttl_hours(session)
    max_mb = await get_max_upload_mb(session)
    can_register = await is_registration_enabled(session)
"""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import GlobalSetting
from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS


async def get_setting_value(session: AsyncSession, key: str, default: Any = None) -> Any:
    """
    Get a global setting value by key, with automatic type conversion.

    Reads directly from DB (no cache) for consistency across workers.

    Args:
        session: Database session
        key: Setting key (e.g., "session_ttl_hours")
        default: Default value if setting not found

    Returns:
        Setting value converted to appropriate type, or default
    """
    result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        # Try to get default from GLOBAL_SETTINGS_DEFAULTS
        if key in GLOBAL_SETTINGS_DEFAULTS:
            return _convert_value(
                GLOBAL_SETTINGS_DEFAULTS[key]["value"], GLOBAL_SETTINGS_DEFAULTS[key]["type"]
            )
        return default

    return _convert_value(setting.value, setting.value_type)


def _convert_value(value: str, value_type: str) -> Any:
    """Convert string value to appropriate Python type."""
    if value_type == "int":
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    elif value_type == "bool":
        return value.lower() in ("true", "1", "yes", "on")
    elif value_type == "json":
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    else:
        # string or unknown type
        return value


async def get_session_ttl_hours(session: AsyncSession) -> int:
    """
    Get session TTL in hours.

    Default: 24 hours
    """
    value = await get_setting_value(session, "session_ttl_hours", 24)
    return int(value) if value else 24


async def get_max_upload_mb(session: AsyncSession) -> int:
    """
    Get maximum file upload size in MB.

    Default: 10 MB
    """
    value = await get_setting_value(session, "max_file_upload_mb", 10)
    return int(value) if value else 10


async def is_registration_enabled(session: AsyncSession) -> bool:
    """
    Check if new user registration is enabled.

    Default: True
    """
    value = await get_setting_value(session, "enable_registration", True)
    return bool(value)


async def get_default_language(session: AsyncSession) -> str:
    """
    Get default language for new users.

    Default: "en"
    """
    value = await get_setting_value(session, "default_language", "en")
    return str(value) if value else "en"


async def get_default_currency(session: AsyncSession) -> str:
    """
    Get default base currency for new users.

    Default: "EUR"
    """
    value = await get_setting_value(session, "default_currency", "EUR")
    return str(value) if value else "EUR"


# Synchronous fallback functions (use defaults, no DB access)
# These are useful for initialization or when async is not available


def get_session_ttl_hours_sync() -> int:
    """Get session TTL from defaults (no DB access)."""
    return int(GLOBAL_SETTINGS_DEFAULTS.get("session_ttl_hours", {}).get("value", 24))


def get_max_upload_mb_sync() -> int:
    """Get max upload MB from defaults (no DB access)."""
    return int(GLOBAL_SETTINGS_DEFAULTS.get("max_file_upload_mb", {}).get("value", 10))


def is_registration_enabled_sync() -> bool:
    """Check registration enabled from defaults (no DB access)."""
    value = GLOBAL_SETTINGS_DEFAULTS.get("enable_registration", {}).get("value", "true")
    return value.lower() in ("true", "1", "yes", "on")
