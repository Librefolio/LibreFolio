"""
Global Settings Service - Utility functions for reading global settings.

This module provides simple getter functions for global settings values.
All functions read directly from DB (no cache) to ensure consistency
across multiple workers.

Pass keys from SETTINGS_REGISTRY (backend.app.schemas.settings) rather than
raw string literals; defaults stay in GLOBAL_SETTINGS_DEFAULTS.

Usage:
    from backend.app.services.accounts.global_settings_service import (
        get_session_ttl_hours,
        get_max_upload_mb,
    )

    ttl = await get_session_ttl_hours(session)
    max_mb = await get_max_upload_mb(session)

Who may register is decided by services/accounts/registration_service.py.
"""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.accounts import default_language
from backend.app.db.models import GlobalSetting
from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS, SETTINGS_REGISTRY

DEFAULT_LANGUAGE_KEY = SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key


def effective_stored_value(key: str, setting: GlobalSetting | None) -> str | None:
    """The value a global setting has now, when an environment variable stands behind it: ``None`` when none does.

    ``LIBREFOLIO_DEFAULT_LANGUAGE`` (CL-10) is the ``default_language`` until an administrator saves that setting: its row
    is missing, or was never written by a user (``updated_by_user_id`` is empty, as the row the startup seeds with the default).
    From the administrator's first save on, the row wins, even when it says the default again. An unusable variable is the audit's
    to stop at the start; here it stands for nothing.
    """
    if key != DEFAULT_LANGUAGE_KEY or (setting is not None and setting.updated_by_user_id is not None):
        return None
    try:
        return default_language()
    except ValueError:
        return None


async def get_setting_value(session: AsyncSession, key: str, default: Any = None) -> Any:
    """
    Get a global setting value by key, with automatic type conversion.

    Reads directly from DB (no cache) for consistency across workers.

    Args:
        session: Database session
        key: Setting key — pass a registry constant, e.g. SETTINGS_REGISTRY.global_.SESSION_TTL_HOURS.key
        default: Default value if setting not found

    Returns:
        Setting value converted to appropriate type, or default
    """
    result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
    setting = result.scalar_one_or_none()

    pinned = effective_stored_value(key, setting)
    if pinned is not None:
        return pinned

    if not setting:
        # Try to get default from GLOBAL_SETTINGS_DEFAULTS
        if key in GLOBAL_SETTINGS_DEFAULTS:
            return _convert_value(GLOBAL_SETTINGS_DEFAULTS[key]["value"], GLOBAL_SETTINGS_DEFAULTS[key]["type"])
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
    value = await get_setting_value(session, SETTINGS_REGISTRY.global_.SESSION_TTL_HOURS.key, 24)
    return int(value) if value else 24


async def get_max_upload_mb(session: AsyncSession) -> int:
    """
    Get maximum file upload size in MB.

    Default: 10 MB
    """
    value = await get_setting_value(session, SETTINGS_REGISTRY.global_.MAX_FILE_UPLOAD_MB.key, 10)
    return int(value) if value else 10
