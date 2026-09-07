"""
Tests for settings_service user settings behavior.
"""

import uuid

import pytest


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


class TestGetEffectiveBaseCurrency:
    """P0-1 (audit 08): get_effective_base_currency resolution chain.

    per-user UserSettings.base_currency (row exists) → global default_currency
    → "EUR". Replaces the phantom `base_currency` global key, which was never
    registered — every reader silently got EUR regardless of configuration.
    """

    @staticmethod
    async def _stash_global_currency(session):
        """Snapshot the current global default_currency row (or its absence)."""
        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config

        row = await session.get(GlobalSetting, "default_currency")
        return (
            {
                "value": row.value,
                "value_type": row.value_type,
                "description": row.description,
                "updated_at": row.updated_at,
            }
            if row
            else None
        )

    @staticmethod
    async def _restore_global_currency(session, snapshot):
        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.utils.datetime_utils import utcnow  # noqa: PLC0415 — test setup — imports after db config

        current = await session.get(GlobalSetting, "default_currency")
        if snapshot is None:
            if current:
                await session.delete(current)
        elif current:
            current.value = snapshot["value"]
            current.value_type = snapshot["value_type"]
            current.description = snapshot["description"]
            current.updated_at = snapshot["updated_at"]
        else:
            session.add(
                GlobalSetting(
                    key="default_currency",
                    value=snapshot["value"],
                    value_type=snapshot["value_type"],
                    description=snapshot["description"],
                    updated_at=snapshot["updated_at"] or utcnow(),
                )
            )
        await session.commit()

    @pytest.mark.asyncio
    async def test_user_row_wins_over_a_different_global_default(self):
        """(a) User row CHF + global USD → CHF: the per-user value must WIN,
        not merely coincide with the global one."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.schemas.settings import UserSettingsUpdate  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.settings_service import get_effective_base_currency, update_user_settings  # noqa: PLC0415
        from backend.app.utils.datetime_utils import utcnow  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            snapshot = await self._stash_global_currency(session)
            try:
                # Force the global to differ from the user value.
                row = await session.get(GlobalSetting, "default_currency")
                if row:
                    row.value = "USD"
                    row.value_type = "str"
                else:
                    session.add(GlobalSetting(key="default_currency", value="USD", value_type="str", description=f"pytest-{unique_id}", updated_at=utcnow()))
                await session.commit()

                user, error = await user_service.create_user(
                    session=session,
                    username=f"effccy_user_{unique_id}",
                    email=f"effccy_user_{unique_id}@example.com",
                    password="TestPass123!",
                )
                assert error is None
                user_id = user.id  # capture now: the session expires ORM attrs on commit
                await update_user_settings(user_id, UserSettingsUpdate(base_currency="CHF"), session)

                assert await get_effective_base_currency(session, user_id) == "CHF"
            finally:
                await self._restore_global_currency(session, snapshot)

    @pytest.mark.asyncio
    async def test_no_user_row_falls_back_to_global_default(self):
        """(b) No settings row + global default_currency=USD → USD."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.settings_service import get_effective_base_currency  # noqa: PLC0415
        from backend.app.utils.datetime_utils import utcnow  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            snapshot = await self._stash_global_currency(session)
            try:
                row = await session.get(GlobalSetting, "default_currency")
                if row:
                    row.value = "USD"
                    row.value_type = "str"
                else:
                    session.add(GlobalSetting(key="default_currency", value="USD", value_type="str", description=f"pytest-{unique_id}", updated_at=utcnow()))
                await session.commit()

                user, error = await user_service.create_user(
                    session=session,
                    username=f"effccy_glob_{unique_id}",
                    email=f"effccy_glob_{unique_id}@example.com",
                    password="TestPass123!",
                )
                assert error is None
                # No update_user_settings call: the user has NO row.

                assert await get_effective_base_currency(session, user.id) == "USD"
            finally:
                await self._restore_global_currency(session, snapshot)

    @pytest.mark.asyncio
    async def test_no_row_and_no_global_falls_back_to_eur(self):
        """(c) No settings row and NO global default_currency row → EUR."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.settings_service import get_effective_base_currency  # noqa: PLC0415

        unique_id = uuid.uuid4().hex[:8]
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            snapshot = await self._stash_global_currency(session)
            try:
                row = await session.get(GlobalSetting, "default_currency")
                if row:
                    await session.delete(row)
                    await session.commit()

                user, error = await user_service.create_user(
                    session=session,
                    username=f"effccy_none_{unique_id}",
                    email=f"effccy_none_{unique_id}@example.com",
                    password="TestPass123!",
                )
                assert error is None

                assert await get_effective_base_currency(session, user.id) == "EUR"
            finally:
                await self._restore_global_currency(session, snapshot)


class TestEngineBaseCurrencyBranch:
    """P0-1 (audit 08): the `target_currency is None` branch of the engine.

    Before the fix this branch called `get_global_setting` with three
    positional arguments — a guaranteed TypeError — behind a phantom settings
    key. A fresh user with a settings row and ZERO broker accesses takes the
    early return right after the resolution, so the branch is exercised
    end-to-end (real helper, real DB) with no engine fixture to build.
    """

    @pytest.mark.asyncio
    async def test_calculate_without_target_currency_uses_the_user_base_currency(self):
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test setup — imports after db config

        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.schemas.settings import UserSettingsUpdate  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config
        from backend.app.services.portfolio_engine import PortfolioCalculationEngine  # noqa: PLC0415
        from backend.app.services.settings_service import update_user_settings  # noqa: PLC0415

        unique_id = uuid.uuid4().hex[:8]
        engine_session = get_async_engine()
        async with AsyncSession(engine_session) as session:
            user, error = await user_service.create_user(
                session=session,
                username=f"effccy_eng_{unique_id}",
                email=f"effccy_eng_{unique_id}@example.com",
                password="TestPass123!",
            )
            assert error is None
            user_id = user.id  # capture now: the session expires ORM attrs on commit
            await update_user_settings(user_id, UserSettingsUpdate(base_currency="CHF"), session)

            # No broker access rows: calculate() resolves the currency, then
            # returns early with an empty result — the branch is the assertion.
            result = await PortfolioCalculationEngine(session).calculate(user_id=user_id)

            assert result.target_currency == "CHF"
            assert result.daily_states == []
