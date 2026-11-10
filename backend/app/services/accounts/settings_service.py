"""
Settings service layer for LibreFolio.

Dual responsibility (P2-9 — user columns vs global key-value, the two services
stay separate by design):

- USER settings: CRUD over the per-user `UserSettings` row: the typed columns
  (`language`, `base_currency`, `avatar_url`) and the JSON `ui_preferences`
  (`theme`, `chart_line_shape`), whose absent keys follow their global defaults.
- GLOBAL settings: CRUD over the admin-managed `GlobalSetting` key-value rows
  (registration, uploads, scheduler configuration, new-user defaults).

`global_settings_service` complements this file with typed read helpers for
global keys. Every known key — storage location, type, description — is
declared once in `SETTINGS_REGISTRY` (backend.app.schemas.settings); reference
registry constants (e.g. `SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key`)
instead of raw string literals.
"""

import json
from collections.abc import Callable, Sequence
from typing import Any, Optional, get_args

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.config.accounts import registration_mode_pinned
from backend.app.config.backup import STORAGE_LIMIT_VARIABLE, storage_limit_pinned
from backend.app.db.models import GlobalSetting, UserSettings
from backend.app.schemas.settings import (
    GLOBAL_SETTINGS_DEFAULTS,
    SETTINGS_REGISTRY,
    UI_PREFERENCES_MAX_BYTES,
    GlobalSettingRead,
    UIPreferenceDefaults,
    UIPreferences,
    UserSettingsRead,
    UserSettingsUpdate,
    validate_global_setting_value,
)
from backend.app.services.accounts.global_settings_service import effective_stored_value, get_setting_value
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)


# ============================================================================
# USER SETTINGS
# ============================================================================

#: The value each interface preference takes when neither the user nor a readable global setting gives one.
FALLBACK_UI_PREFERENCES: dict[str, str] = {"theme": "auto", "chart_line_shape": "segments"}
#: The global setting that gives each interface preference its default.
_UI_PREFERENCE_GLOBALS: dict[str, str] = {
    "theme": SETTINGS_REGISTRY.global_.DEFAULT_THEME.key,
    "chart_line_shape": SETTINGS_REGISTRY.global_.DEFAULT_CHART_LINE_SHAPE.key,
}


class UIPreferencesTooLargeError(ValueError):
    """A write would leave ``user_settings.ui_preferences`` longer than ``UI_PREFERENCES_MAX_BYTES``."""


def _known_values(key: str) -> frozenset[str]:
    """The values ``UIPreferences.<key>`` accepts, read from the schema."""
    annotation = UIPreferences.model_fields[key].annotation
    return frozenset(value for arg in get_args(annotation) for value in get_args(arg))


def _stored_ui_preferences(user_id: int, raw: Optional[str]) -> dict[str, Any]:
    """What ``user_settings.ui_preferences`` holds, as a dict: ``{}`` for NULL, for text that is not JSON or not an object."""
    if not raw:
        return {}
    try:
        stored = json.loads(raw)
    except ValueError:
        logger.warning("The stored interface preferences are not JSON: none is used", user_id=user_id)
        return {}
    if not isinstance(stored, dict):
        logger.warning("The stored interface preferences are not an object: none is used", user_id=user_id)
        return {}
    return stored


def _readable_ui_preferences(user_id: int, raw: Optional[str]) -> UIPreferences:
    """The user's own preferences this version can show (A-11, per key).

    A key it does not know, or a value it does not know — written by hand, or by a later version before a downgrade — is
    left out, with a warning: that preference follows its global default. Reading writes nothing, so the row keeps the
    value, and a version that knows it shows it again.
    """
    stored = _stored_ui_preferences(user_id, raw)
    readable: dict[str, str] = {}
    for key in UIPreferences.model_fields:
        value = stored.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value in _known_values(key):
            readable[key] = value
        else:
            logger.warning("A stored interface preference is unknown: its global default is shown", user_id=user_id, key=key, stored=str(value)[:20])
    return UIPreferences(**readable)


async def ui_preference_defaults(session: AsyncSession) -> UIPreferenceDefaults:
    """The global default of every interface preference; one the app does not know falls back to ``FALLBACK_UI_PREFERENCES``."""
    defaults: dict[str, str] = {}
    for key, global_key in _UI_PREFERENCE_GLOBALS.items():
        value = await get_setting_value(session, global_key, FALLBACK_UI_PREFERENCES[key])
        if value not in _known_values(key):
            logger.warning("A global interface default is unknown: the built-in one is used", key=global_key, stored=str(value)[:20])
            value = FALLBACK_UI_PREFERENCES[key]
        defaults[key] = value
    return UIPreferenceDefaults(**defaults)


def merged_ui_preferences(user_id: int, raw: Optional[str], changes: UIPreferences) -> Optional[str]:
    """``raw`` with the keys ``changes`` names applied: a value sets its key, ``null`` removes it; NULL when nothing is left.

    Only the named keys change, so two tabs that each write their own key never undo each other. A key this version does
    not know is kept as it is: a later version wrote it.
    """
    merged = _stored_ui_preferences(user_id, raw)
    for key in changes.model_fields_set:
        value = getattr(changes, key)
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    if not merged:
        return None
    text = json.dumps(merged, separators=(",", ":"), sort_keys=True)
    if len(text.encode("utf-8")) > UI_PREFERENCES_MAX_BYTES:
        raise UIPreferencesTooLargeError(f"The interface preferences would take more than {UI_PREFERENCES_MAX_BYTES} bytes")
    return text


async def _settings_read(session: AsyncSession, settings: UserSettings) -> UserSettingsRead:
    """``settings`` as the API answers them: the user's own interface preferences that this version knows, and their defaults."""
    return UserSettingsRead(
        language=settings.language,
        base_currency=settings.base_currency,
        avatar_url=settings.avatar_url,
        ui_preferences=_readable_ui_preferences(settings.user_id, settings.ui_preferences),
        ui_preference_defaults=await ui_preference_defaults(session),
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

    A new row holds no interface preference: each follows its global default until the user chooses it.

    Uses INSERT OR IGNORE (on_conflict_do_nothing) to be safe against concurrent
    requests for the same user (e.g. multiple Playwright workers calling /api/v1/settings/user
    simultaneously right after login).
    """
    now = utcnow()
    default_language = await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key, "en")
    default_currency = await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key, "EUR")
    stmt = (
        sqlite_insert(UserSettings)
        .values(
            user_id=user_id,
            language=default_language,
            base_currency=default_currency,
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
    """Update user settings. Creates if not exists.

    ``updates.ui_preferences`` merges key by key (``merged_ui_preferences``); a write that would leave the column over
    ``UI_PREFERENCES_MAX_BYTES`` raises ``UIPreferencesTooLargeError`` and saves nothing.
    """
    # Get existing settings
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        # Create with updates
        settings = UserSettings(
            user_id=user_id,
            language=updates.language or await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key, "en"),
            base_currency=updates.base_currency or await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key, "EUR"),
            avatar_url=updates.avatar_url,
            ui_preferences=merged_ui_preferences(user_id, None, updates.ui_preferences) if updates.ui_preferences is not None else None,
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
        if "avatar_url" in updates.model_fields_set:
            settings.avatar_url = updates.avatar_url
        if updates.ui_preferences is not None:
            settings.ui_preferences = merged_ui_preferences(user_id, settings.ui_preferences, updates.ui_preferences)
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
            value=effective_stored_value(setting.key, setting) or setting.value,
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
            value=effective_stored_value(s.key, s) or s.value,
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
    "storage_limit_mb": (STORAGE_LIMIT_VARIABLE, storage_limit_pinned),
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


def _refused_by_profile(key: str, stored: str) -> str | None:
    """Why the active profile refuses a valid value, or ``None``: a managed instance cannot switch off the space limit of
    its kept backups (FB-24), since its volume is fixed. The age may be switched off."""
    if key == SETTINGS_REGISTRY.global_.BACKUP_CLEANUP_MAX_MB.key and stored == "0" and get_settings().LIBREFOLIO_PROFILE == "managed":
        return "must be at least 1 on a managed instance"
    return None


def _validated(items: Sequence[tuple[str, str]], rows: dict[str, GlobalSetting]) -> tuple[list[str], list[tuple[str, str]]]:
    """The value to store for each item, and every (key, reason) a setting or the active profile refuses."""
    stored_values: list[str] = []
    errors: list[tuple[str, str]] = []
    for key, value in items:
        try:
            stored = validate_global_setting_value(key, value, rows[key].value_type)
            refusal = _refused_by_profile(key, stored)
            if refusal is not None:
                raise ValueError(refusal)
            stored_values.append(stored)
        except ValueError as exc:
            errors.append((key, str(exc)))
    return stored_values, errors


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

    stored_values, errors = _validated(items, rows)
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
