"""
Settings service layer for LibreFolio.

Handles user settings and global settings operations.
"""

from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import GlobalSetting, UserSettings
from backend.app.schemas.settings import (
    GLOBAL_SETTINGS_DEFAULTS,
    GlobalSettingRead,
    UserSettingsRead,
    UserSettingsUpdate,
)
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)


# ============================================================================
# USER SETTINGS
# ============================================================================


async def get_user_settings(user_id: int, session: AsyncSession) -> Optional[UserSettingsRead]:
    """Get settings for a user. Returns None if not found."""
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    if settings:
        return UserSettingsRead(
            language=settings.language,
            base_currency=settings.base_currency,
            theme=settings.theme,
            avatar_url=settings.avatar_url,
        )
    return None


async def get_or_create_user_settings(user_id: int, session: AsyncSession) -> UserSettingsRead:
    """Get user settings, creating with defaults if not exists."""
    settings = await get_user_settings(user_id, session)
    if settings:
        return settings

    # Create default settings
    new_settings = UserSettings(
        user_id=user_id,
        language="en",
        base_currency="EUR",
        theme="light",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(new_settings)
    await session.commit()
    await session.refresh(new_settings)

    logger.info("Created default user settings", user_id=user_id)

    return UserSettingsRead(
        language=new_settings.language,
        base_currency=new_settings.base_currency,
        theme=new_settings.theme,
        avatar_url=new_settings.avatar_url,
    )


async def update_user_settings(user_id: int, updates: UserSettingsUpdate, session: AsyncSession) -> UserSettingsRead:
    """Update user settings. Creates if not exists."""
    # Get existing settings
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        # Create with updates
        settings = UserSettings(
            user_id=user_id,
            language=updates.language or "en",
            base_currency=updates.base_currency or "EUR",
            theme=updates.theme or "light",
            avatar_url=updates.avatar_url,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(settings)
    else:
        # Update existing
        if updates.language is not None:
            settings.language = updates.language
        if updates.base_currency is not None:
            settings.base_currency = updates.base_currency
        if updates.theme is not None:
            settings.theme = updates.theme
        if updates.avatar_url is not None:
            settings.avatar_url = updates.avatar_url
        settings.updated_at = utcnow()

    await session.commit()
    await session.refresh(settings)

    logger.info("Updated user settings", user_id=user_id)

    return UserSettingsRead(
        language=settings.language,
        base_currency=settings.base_currency,
        theme=settings.theme,
        avatar_url=settings.avatar_url,
    )


# ============================================================================
# GLOBAL SETTINGS
# ============================================================================


async def get_global_setting(key: str, session: AsyncSession) -> Optional[GlobalSettingRead]:
    """Get a single global setting by key."""
    result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        return GlobalSettingRead(
            key=setting.key,
            value=setting.value,
            value_type=setting.value_type,
            description=setting.description,
            updated_at=setting.updated_at,
            updated_by=setting.updated_by_user_id,
        )
    return None


async def get_all_global_settings(session: AsyncSession) -> list[GlobalSettingRead]:
    """Get all global settings."""
    result = await session.execute(select(GlobalSetting))
    settings = result.scalars().all()
    return [
        GlobalSettingRead(
            key=s.key,
            value=s.value,
            value_type=s.value_type,
            description=s.description,
            updated_at=s.updated_at,
            updated_by=s.updated_by_user_id,
        )
        for s in settings
    ]


async def update_global_setting(key: str, value: str, user_id: int, session: AsyncSession) -> Optional[GlobalSettingRead]:
    """Update a global setting. Returns None if key doesn't exist."""
    result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        return None

    setting.value = value
    setting.updated_at = utcnow()
    setting.updated_by_user_id = user_id

    await session.commit()
    await session.refresh(setting)

    logger.info("Updated global setting", key=key, user_id=user_id)

    return GlobalSettingRead(
        key=setting.key,
        value=setting.value,
        value_type=setting.value_type,
        description=setting.description,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by_user_id,
    )


async def initialize_global_settings(session: AsyncSession) -> int:
    """
    Initialize global settings with defaults.
    Only creates settings that don't exist yet.

    Uses INSERT ... ON CONFLICT DO NOTHING to be safe for concurrent
    multi-worker startup (e.g. Uvicorn with multiple workers).

    Returns: Number of settings created.
    """
    created = 0

    for key, config in GLOBAL_SETTINGS_DEFAULTS.items():
        stmt = (
            sqlite_insert(GlobalSetting)
            .values(
                key=key,
                value=config["value"],
                value_type=config["type"],
                description=config["description"],
                updated_at=utcnow(),
            )
            .on_conflict_do_nothing(index_elements=["key"])
        )
        result = await session.execute(stmt)
        if result.rowcount and result.rowcount > 0:
            created += 1

    await session.commit()

    if created > 0:
        logger.info("Initialized global settings", created=created)

    return created


def get_session_ttl_sync() -> int:
    """
    Get session TTL in hours from global settings (synchronous).

    This is a fallback that returns the default value.
    For actual DB lookup, use the async version.
    """
    return int(GLOBAL_SETTINGS_DEFAULTS["session_ttl_hours"]["value"])


async def get_session_ttl(session: AsyncSession) -> int:
    """Get session TTL in hours from global settings."""
    setting = await get_global_setting("session_ttl_hours", session)
    if setting:
        try:
            return int(setting.value)
        except ValueError:
            pass
    return int(GLOBAL_SETTINGS_DEFAULTS["session_ttl_hours"]["value"])
