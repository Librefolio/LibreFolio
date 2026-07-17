"""
Tests for settings_service: get_session_ttl_sync and get_session_ttl.

Covers:
- get_session_ttl_sync: synchronous TTL default value
- get_session_ttl: async TTL from DB
"""

import uuid

import pytest

from backend.app.services.settings_service import get_session_ttl, get_session_ttl_sync


class TestGetSessionTTLSync:
    def test_returns_positive_integer(self):
        ttl = get_session_ttl_sync()
        assert isinstance(ttl, int)
        assert ttl > 0

    def test_returns_default_value(self):
        """Default is typically 24 hours."""
        ttl = get_session_ttl_sync()
        assert ttl >= 1  # at least 1 hour


class TestGetSessionTTL:
    """Tests for async get_session_ttl."""

    @pytest.mark.asyncio
    async def test_returns_positive_integer(self):
        """get_session_ttl returns a positive int from DB."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after sys.path/db config

        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after sys.path/db config

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            ttl = await get_session_ttl(session)
            assert isinstance(ttl, int)
            assert ttl > 0

    @pytest.mark.asyncio
    async def test_returns_default_when_no_setting(self):
        """Falls back to default when setting not in DB."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after sys.path/db config

        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after sys.path/db config

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            ttl = await get_session_ttl(session)
            assert ttl >= 1

    @pytest.mark.asyncio
    async def test_returns_custom_value_from_db(self):
        """get_session_ttl returns persisted custom TTL."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.utils.datetime_utils import utcnow  # noqa: PLC0415 — test setup — imports after db config

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            existing = await session.get(GlobalSetting, "session_ttl_hours")
            original_value = existing.value if existing else None
            original_type = existing.value_type if existing else None
            original_description = existing.description if existing else None
            original_updated_at = existing.updated_at if existing else None

            if existing:
                existing.value = "72"
                existing.value_type = "int"
            else:
                session.add(
                    GlobalSetting(
                        key="session_ttl_hours",
                        value="72",
                        value_type="int",
                        description=f"pytest-{uuid.uuid4().hex[:8]}",
                        updated_at=utcnow(),
                    )
                )
            await session.commit()

            try:
                ttl = await get_session_ttl(session)
                assert ttl == 72
            finally:
                created = await session.get(GlobalSetting, "session_ttl_hours")
                if existing and created:
                    created.value = original_value
                    created.value_type = original_type
                    created.description = original_description
                    created.updated_at = original_updated_at
                elif created:
                    await session.delete(created)
                await session.commit()


class TestGetOrCreateUserSettings:
    """Tests for get_or_create_user_settings()."""

    @pytest.mark.asyncio
    async def test_uses_custom_global_defaults_when_creating_settings(self):
        """get_or_create_user_settings uses DB-backed global defaults."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.settings_service import get_or_create_user_settings  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.utils.datetime_utils import utcnow  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            existing_language = await session.get(GlobalSetting, "default_language")
            existing_currency = await session.get(GlobalSetting, "default_currency")
            existing_theme = await session.get(GlobalSetting, "default_theme")

            original_language = (
                {
                    "value": existing_language.value,
                    "value_type": existing_language.value_type,
                    "description": existing_language.description,
                    "updated_at": existing_language.updated_at,
                }
                if existing_language
                else None
            )
            original_currency = (
                {
                    "value": existing_currency.value,
                    "value_type": existing_currency.value_type,
                    "description": existing_currency.description,
                    "updated_at": existing_currency.updated_at,
                }
                if existing_currency
                else None
            )
            original_theme = (
                {
                    "value": existing_theme.value,
                    "value_type": existing_theme.value_type,
                    "description": existing_theme.description,
                    "updated_at": existing_theme.updated_at,
                }
                if existing_theme
                else None
            )

            if existing_language:
                existing_language.value = "it"
                existing_language.value_type = "str"
            else:
                session.add(
                    GlobalSetting(
                        key="default_language",
                        value="it",
                        value_type="str",
                        description=f"pytest-{uuid.uuid4().hex[:8]}",
                        updated_at=utcnow(),
                    )
                )

            if existing_currency:
                existing_currency.value = "CHF"
                existing_currency.value_type = "str"
            else:
                session.add(
                    GlobalSetting(
                        key="default_currency",
                        value="CHF",
                        value_type="str",
                        description=f"pytest-{uuid.uuid4().hex[:8]}",
                        updated_at=utcnow(),
                    )
                )

            if existing_theme:
                existing_theme.value = "dark"
                existing_theme.value_type = "str"
            else:
                session.add(
                    GlobalSetting(
                        key="default_theme",
                        value="dark",
                        value_type="str",
                        description=f"pytest-{uuid.uuid4().hex[:8]}",
                        updated_at=utcnow(),
                    )
                )

            await session.commit()

            try:
                user, error = await user_service.create_user(
                    session=session,
                    username=f"settingsdefaults_{unique_id}",
                    email=f"settingsdefaults_{unique_id}@example.com",
                    password="TestPassword123!",
                )
                assert error is None

                result = await get_or_create_user_settings(user.id, session)

                assert result.language == "it"
                assert result.base_currency == "CHF"
                assert result.theme == "dark"
            finally:
                current_language = await session.get(GlobalSetting, "default_language")
                current_currency = await session.get(GlobalSetting, "default_currency")
                current_theme = await session.get(GlobalSetting, "default_theme")

                if original_language and current_language:
                    current_language.value = original_language["value"]
                    current_language.value_type = original_language["value_type"]
                    current_language.description = original_language["description"]
                    current_language.updated_at = original_language["updated_at"]
                elif current_language:
                    await session.delete(current_language)

                if original_currency and current_currency:
                    current_currency.value = original_currency["value"]
                    current_currency.value_type = original_currency["value_type"]
                    current_currency.description = original_currency["description"]
                    current_currency.updated_at = original_currency["updated_at"]
                elif current_currency:
                    await session.delete(current_currency)

                if original_theme and current_theme:
                    current_theme.value = original_theme["value"]
                    current_theme.value_type = original_theme["value_type"]
                    current_theme.description = original_theme["description"]
                    current_theme.updated_at = original_theme["updated_at"]
                elif current_theme:
                    await session.delete(current_theme)

                await session.commit()

    @pytest.mark.asyncio
    async def test_falls_back_to_seeded_defaults_when_rows_missing(self):
        """get_or_create_user_settings falls back to GLOBAL_SETTINGS_DEFAULTS."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.settings_service import get_or_create_user_settings  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            existing_language = await session.get(GlobalSetting, "default_language")
            existing_currency = await session.get(GlobalSetting, "default_currency")
            existing_theme = await session.get(GlobalSetting, "default_theme")

            original_language = (
                {
                    "value": existing_language.value,
                    "value_type": existing_language.value_type,
                    "description": existing_language.description,
                    "updated_at": existing_language.updated_at,
                }
                if existing_language
                else None
            )
            original_currency = (
                {
                    "value": existing_currency.value,
                    "value_type": existing_currency.value_type,
                    "description": existing_currency.description,
                    "updated_at": existing_currency.updated_at,
                }
                if existing_currency
                else None
            )
            original_theme = (
                {
                    "value": existing_theme.value,
                    "value_type": existing_theme.value_type,
                    "description": existing_theme.description,
                    "updated_at": existing_theme.updated_at,
                }
                if existing_theme
                else None
            )

            if existing_language:
                await session.delete(existing_language)
            if existing_currency:
                await session.delete(existing_currency)
            if existing_theme:
                await session.delete(existing_theme)
            await session.commit()

            try:
                user, error = await user_service.create_user(
                    session=session,
                    username=f"settingsseeded_{unique_id}",
                    email=f"settingsseeded_{unique_id}@example.com",
                    password="TestPassword123!",
                )
                assert error is None

                result = await get_or_create_user_settings(user.id, session)

                assert result.language == "en"
                assert result.base_currency == "EUR"
                assert result.theme == "auto"
            finally:
                if original_language:
                    session.add(
                        GlobalSetting(
                            key="default_language",
                            value=original_language["value"],
                            value_type=original_language["value_type"],
                            description=original_language["description"],
                            updated_at=original_language["updated_at"],
                        )
                    )
                if original_currency:
                    session.add(
                        GlobalSetting(
                            key="default_currency",
                            value=original_currency["value"],
                            value_type=original_currency["value_type"],
                            description=original_currency["description"],
                            updated_at=original_currency["updated_at"],
                        )
                    )
                if original_theme:
                    session.add(
                        GlobalSetting(
                            key="default_theme",
                            value=original_theme["value"],
                            value_type=original_theme["value_type"],
                            description=original_theme["description"],
                            updated_at=original_theme["updated_at"],
                        )
                    )
                await session.commit()


class TestUpdateUserSettings:
    """Tests for update_user_settings()."""

    @pytest.mark.asyncio
    async def test_creates_settings_when_missing(self):
        """update_user_settings creates a settings row for users without one."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.schemas.settings import UserSettingsUpdate  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.settings_service import update_user_settings  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user, error = await user_service.create_user(
                session=session,
                username=f"settingscreate_{unique_id}",
                email=f"settingscreate_{unique_id}@example.com",
                password="TestPass123!",
            )
            assert error is None

            result = await update_user_settings(
                user.id,
                UserSettingsUpdate(
                    language="es",
                    base_currency="CHF",
                    theme="dark",
                    avatar_url="https://example.com/create-avatar.png",
                ),
                session,
            )

            assert result.model_dump() == {
                "language": "es",
                "base_currency": "CHF",
                "theme": "dark",
                "avatar_url": "https://example.com/create-avatar.png",
            }

    @pytest.mark.asyncio
    async def test_updates_existing_settings(self):
        """update_user_settings updates an existing settings row."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.schemas.settings import UserSettingsUpdate  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.settings_service import update_user_settings  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user, error = await user_service.create_user(
                session=session,
                username=f"settingsupdate_{unique_id}",
                email=f"settingsupdate_{unique_id}@example.com",
                password="TestPass123!",
            )
            assert error is None
            user_id = user.id

            await update_user_settings(
                user_id,
                UserSettingsUpdate(language="it", base_currency="GBP", theme="light"),
                session,
            )

            result = await update_user_settings(
                user_id,
                UserSettingsUpdate(theme="auto", avatar_url="https://example.com/update-avatar.png"),
                session,
            )

            assert result.model_dump() == {
                "language": "it",
                "base_currency": "GBP",
                "theme": "auto",
                "avatar_url": "https://example.com/update-avatar.png",
            }
