"""
Settings service layer for LibreFolio.

Dual responsibility (P2-9 — user columns vs global key-value, the two services
stay separate by design):

- USER settings: CRUD over the typed columns of the per-user `UserSettings`
  row (`language`, `base_currency`, `theme`, `avatar_url`).
- GLOBAL settings: CRUD over the admin-managed `GlobalSetting` key-value rows
  (registration, uploads, scheduler configuration, new-user defaults).

`global_settings_service` complements this file with typed read helpers for
global keys. Every known key — storage location, type, description — is
declared once in `SETTINGS_REGISTRY` (backend.app.schemas.settings); reference
registry constants (e.g. `SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key`)
instead of raw string literals.
"""

from collections.abc import Callable, Sequence
from typing import Optional, get_args

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.accounts import registration_mode_pinned
from backend.app.db.models import GlobalSetting, UserSettings
from backend.app.schemas.settings import (
    GLOBAL_SETTINGS_DEFAULTS,
    SETTINGS_REGISTRY,
    GlobalSettingRead,
    UserSettingsRead,
    UserSettingsUpdate,
    validate_global_setting_value,
)
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)


# ============================================================================
# USER SETTINGS
# ============================================================================

#: The themes the web app knows: the values ``UserSettingsRead.theme`` accepts, read from it.
KNOWN_THEMES: frozenset[str] = frozenset(get_args(UserSettingsRead.model_fields["theme"].annotation))
#: The theme shown when neither the stored one nor the instance's ``default_theme`` is known.
FALLBACK_THEME = "auto"


async def _shown_theme(session: AsyncSession, user_id: int, stored: str) -> str:
    """The theme to show for the stored ``stored``: itself when the app knows it (A-11).

    Otherwise — a row or a ``default_theme`` written by hand, or a later version's theme after a downgrade — the instance's
    ``default_theme`` when that is known, else ``auto``, with a warning. The row keeps its value: reading writes nothing,
    and a version that knows the theme shows it again.
    """
    if stored in KNOWN_THEMES:
        return stored
    default = await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_THEME.key, FALLBACK_THEME)
    shown = default if default in KNOWN_THEMES else FALLBACK_THEME
    logger.warning("The stored theme is unknown: another one is shown", user_id=user_id, stored=str(stored)[:20], shown=shown)
    return shown


async def _settings_read(session: AsyncSession, settings: UserSettings) -> UserSettingsRead:
    """``settings`` as the API answers them; a stored theme the app does not know is shown as another (A-11)."""
    return UserSettingsRead(
        language=settings.language,
        base_currency=settings.base_currency,
        theme=await _shown_theme(session, settings.user_id, settings.theme),
        avatar_url=settings.avatar_url,
    )


async def get_user_settings(user_id: int, session: AsyncSession) -> Optional[UserSettingsRead]:
    """Get settings for a user. Returns None if not found."""
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    if settings:
        return await _settings_read(session, settings)
    return None


async def get_or_create_user_settings(user_id: int, session: AsyncSession) -> UserSettingsRead:
    """Get user settings, creating with defaults if not exists.

    Uses INSERT OR IGNORE (on_conflict_do_nothing) to be safe against concurrent
    requests for the same user (e.g. multiple Playwright workers calling /api/v1/settings/user
    simultaneously right after login).
    """
    now = utcnow()
    default_language = await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key, "en")
    default_currency = await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key, "EUR")
    default_theme = await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_THEME.key, "auto")
    stmt = (
        sqlite_insert(UserSettings)
        .values(
            user_id=user_id,
            language=default_language,
            base_currency=default_currency,
            theme=default_theme,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await session.execute(stmt)
    await session.commit()

    settings = await get_user_settings(user_id, session)
    if settings:
        return settings

    # Should never happen — but guard against unexpected state
    raise RuntimeError(f"user_settings for user_id={user_id} not found after upsert")


async def get_effective_base_currency(session: AsyncSession, user_id: int) -> str:
    """Effective base currency for a user.

    Semantics (audit 08 P0-1, decision 2026-09-02 — per-user with global
    fallback): the per-user `UserSettings.base_currency` wins whenever a
    settings row exists. New rows are seeded FROM the admin-level global
    `default_currency` at creation (see `get_or_create_user_settings`), so the
    global default reaches users who never chose. No row at all → global
    `default_currency` → "EUR".

    Replaces the phantom `base_currency` global key, which was never
    registered: every reader silently fell back to EUR regardless of the
    configured default.
    """
    result = await session.execute(select(UserSettings.base_currency).where(UserSettings.user_id == user_id))
    user_value = result.scalar_one_or_none()
    if user_value:
        return user_value
    return await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key, "EUR")


async def update_user_settings(user_id: int, updates: UserSettingsUpdate, session: AsyncSession) -> UserSettingsRead:
    """Update user settings. Creates if not exists."""
    # Get existing settings
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        # Create with updates
        settings = UserSettings(
            user_id=user_id,
            language=updates.language or await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key, "en"),
            base_currency=updates.base_currency or await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key, "EUR"),
            theme=updates.theme or await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_THEME.key, "auto"),
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
        if "avatar_url" in updates.model_fields_set:
            settings.avatar_url = updates.avatar_url
        settings.updated_at = utcnow()

    await session.commit()
    await session.refresh(settings)

    logger.info("Updated user settings", user_id=user_id)

    return await _settings_read(session, settings)


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


class GlobalSettingNotFoundError(LookupError):
    """A bulk update names a key that has no global setting."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


class GlobalSettingLockedError(PermissionError):
    """A bulk update writes a setting an environment variable pins (``variable``)."""

    def __init__(self, key: str, variable: str) -> None:
        super().__init__(f"Setting '{key}' is set by {variable} and cannot be changed here")
        self.key = key
        self.variable = variable


# The global settings an environment variable pins when it is set: the row then stays as it is.
_PINNED_BY_ENV: dict[str, tuple[str, Callable[[], bool]]] = {
    "registration_mode": ("LIBREFOLIO_REGISTRATION", registration_mode_pinned),
}


class GlobalSettingUnavailableError(RuntimeError):
    """A bulk update turns on a setting the instance cannot honour now; ``code`` says why (workstream E: email
    verification needs an email with a link able to go out, ``EMAIL_VERIFICATION_UNAVAILABLE``)."""

    def __init__(self, key: str, code: str) -> None:
        super().__init__(f"Setting '{key}' cannot be turned on now: {code}")
        self.key = key
        self.code = code


class GlobalSettingValueError(ValueError):
    """A bulk update carries values their settings refuse; ``errors`` holds every (key, reason)."""

    def __init__(self, errors: list[tuple[str, str]]) -> None:
        self.errors = errors
        super().__init__("Invalid global settings: " + "; ".join(f"{key}: {reason}" for key, reason in errors))


async def _refuse_what_cannot_turn_on(rows: dict[str, GlobalSetting], keys: list[str], stored_values: list[str]) -> None:
    """``GlobalSettingUnavailableError`` for a setting turned on that the instance cannot honour now: email verification
    without an email with a link able to go out (workstream E). Only off to on: a bulk save that sends it on again, while
    email has stopped working, still saves the rest."""
    verification_key = SETTINGS_REGISTRY.global_.REQUIRE_EMAIL_VERIFICATION.key
    for key, stored in zip(keys, stored_values, strict=True):
        if key == verification_key and stored == "true" and rows[key].value != "true":
            # Email imports the accounts services, so the import waits for the call.
            from backend.app.services.email.verification import EmailVerificationUnavailableError, ensure_verification_can_be_enabled  # noqa: PLC0415

            try:
                await ensure_verification_can_be_enabled()
            except EmailVerificationUnavailableError as exc:
                raise GlobalSettingUnavailableError(key, exc.code) from None


async def update_global_settings(items: Sequence[tuple[str, str]], user_id: int, session: AsyncSession) -> list[GlobalSettingRead]:
    """Update several global settings at once, all or nothing.

    Unknown keys are checked first (GlobalSettingNotFoundError), then every value against its type and
    constraint (GlobalSettingValueError, listing every refusal), then whether a setting turned on can be honoured now
    (GlobalSettingUnavailableError: email verification, off to on, needs an email with a link able to go out). Only
    then are the values written, in one commit. Returns one entry per item, in request order.
    """
    keys = [key for key, _value in items]
    result = await session.execute(select(GlobalSetting).where(GlobalSetting.key.in_(keys)))  # type: ignore[attr-defined]
    rows = {row.key: row for row in result.scalars()}
    for key in keys:
        if key not in rows:
            raise GlobalSettingNotFoundError(key)
    for key in keys:
        if key in _PINNED_BY_ENV and _PINNED_BY_ENV[key][1]():
            raise GlobalSettingLockedError(key, _PINNED_BY_ENV[key][0])

    stored_values: list[str] = []
    errors: list[tuple[str, str]] = []
    for key, value in items:
        try:
            stored_values.append(validate_global_setting_value(key, value, rows[key].value_type))
        except ValueError as exc:
            errors.append((key, str(exc)))
    if errors:
        raise GlobalSettingValueError(errors)
    await _refuse_what_cannot_turn_on(rows, keys, stored_values)

    now = utcnow()
    for key, stored in zip(keys, stored_values, strict=True):
        row = rows[key]
        row.value = stored
        row.updated_at = now
        row.updated_by_user_id = user_id
    await session.commit()
    for row in rows.values():
        await session.refresh(row)

    logger.info("Updated global settings", keys=keys, user_id=user_id)

    return [
        GlobalSettingRead(
            key=rows[key].key,
            value=rows[key].value,
            value_type=rows[key].value_type,
            description=rows[key].description,
            updated_at=rows[key].updated_at,
            updated_by=rows[key].updated_by_user_id,
        )
        for key in keys
    ]


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
