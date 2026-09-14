"""
Tests for settings_service user settings behavior.
"""

import uuid

import pytest
import pytest_asyncio


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

    @pytest.mark.asyncio
    async def test_explicit_none_clears_avatar_but_omitted_field_preserves_it(self):
        """`avatar_url=None` explicitly set clears it; an update that omits it leaves it untouched.

        `UserSettingsUpdate.avatar_url` defaults to `None`, so a plain `is not None` check
        cannot tell "clear the avatar" from "the caller didn't mention it". The fix reads
        `model_fields_set` instead — this test locks that distinction in for both directions.
        """
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
                username=f"settingsavatar_{unique_id}",
                email=f"settingsavatar_{unique_id}@example.com",
                password="TestPass123!",
            )
            assert error is None
            user_id = user.id

            await update_user_settings(
                user_id,
                UserSettingsUpdate(avatar_url="https://example.com/original-avatar.png"),
                session,
            )

            # An update that omits avatar_url entirely must preserve the existing value.
            preserved = await update_user_settings(
                user_id,
                UserSettingsUpdate(theme="dark"),
                session,
            )
            assert preserved.avatar_url == "https://example.com/original-avatar.png"

            # An update that explicitly sets avatar_url=None must clear it.
            cleared = await update_user_settings(
                user_id,
                UserSettingsUpdate(avatar_url=None),
                session,
            )
            assert cleared.avatar_url is None


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
                assert user is not None and user.id is not None
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


# ============================================================================
# ONBOARDING SERVICE (Workstream J foundation)
# ============================================================================
#
# Tests for backend/app/services/onboarding_service.py: ensure/get/transition.
# Appended here (rather than a new test file) because the backend test runner
# registers test files individually by name — this file is already registered
# as `services settings`, and its domain (per-user settings.py surface) is the
# natural home for the sibling onboarding surface without a runner edit.

_OWNED_ONBOARDING_USER_IDS: set[int] = set()
_ROUND5_ONBOARDING_FLOW_VERSIONS = {
    "welcome": 1,
    "intro_tour": 1,
    "transactions_page_guide": 1,
    "transaction_create_guide": 1,
    "transaction_bulk_guide": 1,
    "import_guide": 1,
    "broker_page_guide": 1,
    "broker_guide": 1,
    "broker_detail_guide": 1,
    "fx_page_guide": 1,
    "fx_guide": 1,
    "fx_detail_guide": 1,
    "asset_page_guide": 1,
    "asset_guide": 1,
    "asset_detail_guide": 1,
}
_REMOVED_ONBOARDING_DRAFT_FLOWS = {
    "transaction_bulk_validation_guide",
    "transaction_bulk_selection_guide",
    "transaction_bulk_save_guide",
}
_ROUND5_ONBOARDING_STEPS = {
    "transaction_bulk_guide": (
        "transaction.bulk.workspace",
        "transaction.bulk.validation",
        "transaction.bulk.selection",
        "transaction.bulk.save",
    ),
    "import_guide": (
        "import.upload",
        "import.select",
        "import.analyze",
        "import.assets",
        "import.fix",
        "import.duplicates",
        "import.review",
        "import.bulk",
    ),
}


@pytest_asyncio.fixture(autouse=True)
async def cleanup_owned_onboarding_service_users():
    """Delete every account created through an onboarding test helper."""
    before = set(_OWNED_ONBOARDING_USER_IDS)
    yield
    owned = _OWNED_ONBOARDING_USER_IDS - before
    if not owned:
        return

    from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

    from backend.app.db.models import User  # noqa: PLC0415
    from backend.app.db.session import get_async_engine  # noqa: PLC0415

    async with AsyncSession(get_async_engine()) as session:
        for user_id in owned:
            user = await session.get(User, user_id)
            if user is not None:
                await session.delete(user)
        await session.commit()
    _OWNED_ONBOARDING_USER_IDS.difference_update(owned)


class TestOnboardingServiceEnsure:
    """Tests for ensure_onboarding_progress() (also exercised via get_onboarding_progress)."""

    @staticmethod
    async def _make_user(session, marker: str):
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"onb_{marker}_{unique_id}",
            email=f"onb_{marker}_{unique_id}@example.com",
            password="TestPassword123!",
        )
        assert error is None
        user_id = user.id  # capture now: the session expires ORM attrs on commit
        _OWNED_ONBOARDING_USER_IDS.add(user_id)
        return user_id

    def test_round5_registry_is_exactly_fifteen_flows_with_two_step_managed_flows(self):
        """Model, flow registry and step registry share the final Round 5 contract."""
        from backend.app.db.models import OnboardingFlow  # noqa: PLC0415
        from backend.app.services.onboarding_service import ONBOARDING_FLOW_STEPS, ONBOARDING_FLOW_VERSIONS  # noqa: PLC0415

        actual_versions = {flow.value: version for flow, version in ONBOARDING_FLOW_VERSIONS.items()}
        actual_steps = {flow.value: step_ids for flow, step_ids in ONBOARDING_FLOW_STEPS.items()}

        assert len(actual_versions) == 15
        assert actual_versions == _ROUND5_ONBOARDING_FLOW_VERSIONS
        assert {flow.value for flow in OnboardingFlow} == set(_ROUND5_ONBOARDING_FLOW_VERSIONS)
        assert set(actual_versions).isdisjoint(_REMOVED_ONBOARDING_DRAFT_FLOWS)
        assert actual_steps == _ROUND5_ONBOARDING_STEPS
        assert set(actual_versions.values()) == {1}, "Every unreleased Round 5 flow must remain at version 1"

    @pytest.mark.asyncio
    async def test_ensure_creates_all_missing_rows_pending_current_version(self):
        """A brand-new user gets all 15 flows and every registered step pending."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingStatus, User  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            ensure_onboarding_progress,
            get_onboarding_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "ensure_all")

            try:
                rows = await ensure_onboarding_progress(user_id, session)

                assert len(rows) == 15, "A fresh user must receive exactly the Round 5 source-of-truth rows"
                assert set(rows) == set(ONBOARDING_FLOW_VERSIONS), "Every registered flow must get a row"
                for flow, row in rows.items():
                    assert row.user_id == user_id
                    assert row.status == OnboardingStatus.PENDING
                    assert row.version == ONBOARDING_FLOW_VERSIONS[flow]
                    assert row.completed_at is None
                    assert row.skipped_at is None

                response = await get_onboarding_progress(user_id, session)
                items = {item.flow.value: item for item in response.flows}
                assert set(items) == set(_ROUND5_ONBOARDING_FLOW_VERSIONS)
                for flow, expected_step_ids in _ROUND5_ONBOARDING_STEPS.items():
                    steps = items[flow].steps
                    assert steps is not None
                    assert tuple(step.step_id for step in steps) == expected_step_ids
                    assert all(step.status == OnboardingStatus.PENDING for step in steps)
                    assert all(step.version == 1 and step.current_version == 1 for step in steps)
                for flow in set(items) - set(_ROUND5_ONBOARDING_STEPS):
                    assert items[flow].steps is None
            finally:
                await session.rollback()
                user = await session.get(User, user_id)
                if user is not None:
                    await session.delete(user)
                    await session.commit()

    @pytest.mark.asyncio
    async def test_ensure_is_idempotent_on_second_call(self):
        """Calling ensure() again must not insert or touch flow or step rows."""
        from sqlalchemy import select  # noqa: PLC0415
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import User, UserOnboardingStepProgress  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            ensure_onboarding_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "ensure_idem")

            try:
                first = await ensure_onboarding_progress(user_id, session)
                first_snapshot = {flow: (row.id, row.status, row.version, row.updated_at) for flow, row in first.items()}
                first_step_result = await session.execute(select(UserOnboardingStepProgress).where(UserOnboardingStepProgress.user_id == user_id))
                first_step_snapshot = {(row.flow, row.step_id): (row.id, row.status, row.version, row.updated_at) for row in first_step_result.scalars().all()}

                second = await ensure_onboarding_progress(user_id, session)
                second_snapshot = {flow: (row.id, row.status, row.version, row.updated_at) for flow, row in second.items()}
                second_step_result = await session.execute(select(UserOnboardingStepProgress).where(UserOnboardingStepProgress.user_id == user_id))
                second_step_snapshot = {(row.flow, row.step_id): (row.id, row.status, row.version, row.updated_at) for row in second_step_result.scalars().all()}

                assert second_snapshot == first_snapshot, "Second ensure() must leave every flow row byte-identical"
                assert second_step_snapshot == first_step_snapshot, "Second ensure() must leave every step row byte-identical"
                assert len(second) == len(ONBOARDING_FLOW_VERSIONS), "No duplicate flow rows may be created"
                assert len(second_step_snapshot) == sum(len(step_ids) for step_ids in _ROUND5_ONBOARDING_STEPS.values())
            finally:
                await session.rollback()
                user = await session.get(User, user_id)
                if user is not None:
                    await session.delete(user)
                    await session.commit()


class TestOnboardingServiceStepTransition:
    """Tests for step completion/skip and the owning flow aggregate."""

    @staticmethod
    async def _make_user(session, marker: str):
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"onbs_{marker}_{unique_id}",
            email=f"onbs_{marker}_{unique_id}@example.com",
            password=f"Onb9!{unique_id}",
        )
        assert error is None
        assert user is not None and user.id is not None
        user_id = user.id
        _OWNED_ONBOARDING_USER_IDS.add(user_id)
        return user_id

    @pytest.mark.asyncio
    async def test_import_stays_pending_until_all_steps_terminal_then_completes_when_mixed(self):
        """One completed step plus seven skipped steps aggregates to completed,
        but not before the final pending step becomes terminal."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus, User  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_STEPS,
            ONBOARDING_FLOW_VERSIONS,
            transition_onboarding_step_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user_id = await self._make_user(session, "mixed")
            flow = OnboardingFlow.IMPORT_GUIDE
            version = ONBOARDING_FLOW_VERSIONS[flow]
            try:
                first = await transition_onboarding_step_progress(
                    user_id,
                    flow,
                    "import.upload",
                    OnboardingStatus.COMPLETED,
                    version,
                    session,
                )
                repeated = await transition_onboarding_step_progress(
                    user_id,
                    flow,
                    "import.upload",
                    OnboardingStatus.COMPLETED,
                    version,
                    session,
                )

                assert repeated.model_dump() == first.model_dump(), "Repeating a step completion must be idempotent"
                assert first.status == OnboardingStatus.PENDING
                assert first.completed_at is None
                step_items = {step.step_id: step for step in first.steps or []}
                assert tuple(step_items) == ONBOARDING_FLOW_STEPS[flow]
                assert step_items["import.upload"].status == OnboardingStatus.COMPLETED
                assert step_items["import.upload"].completed_at is not None
                assert all(step_items[step_id].status == OnboardingStatus.PENDING for step_id in ONBOARDING_FLOW_STEPS[flow] if step_id != "import.upload")

                remaining = [step_id for step_id in ONBOARDING_FLOW_STEPS[flow] if step_id != "import.upload"]
                result = first
                for step_id in remaining:
                    result = await transition_onboarding_step_progress(
                        user_id,
                        flow,
                        step_id,
                        OnboardingStatus.SKIPPED,
                        version,
                        session,
                    )
                    if step_id != "import.bulk":
                        assert result.status == OnboardingStatus.PENDING

                assert result.status == OnboardingStatus.COMPLETED
                assert result.completed_at is not None
                assert result.skipped_at is None
                terminal_steps = {step.step_id: step for step in result.steps or []}
                assert terminal_steps["import.upload"].status == OnboardingStatus.COMPLETED
                assert all(terminal_steps[step_id].status == OnboardingStatus.SKIPPED for step_id in remaining)
            finally:
                await session.rollback()
                user = await session.get(User, user_id)
                if user is not None:
                    await session.delete(user)
                    await session.commit()

    @pytest.mark.asyncio
    async def test_bulk_aggregate_is_skipped_only_when_every_step_is_skipped(self):
        """Four skipped Bulk steps aggregate to skipped, never completed."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus, User  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_STEPS,
            ONBOARDING_FLOW_VERSIONS,
            transition_onboarding_step_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user_id = await self._make_user(session, "all_skipped")
            flow = OnboardingFlow.TRANSACTION_BULK_GUIDE
            version = ONBOARDING_FLOW_VERSIONS[flow]
            try:
                result = None
                for step_id in ONBOARDING_FLOW_STEPS[flow]:
                    result = await transition_onboarding_step_progress(
                        user_id,
                        flow,
                        step_id,
                        OnboardingStatus.SKIPPED,
                        version,
                        session,
                    )
                    if step_id != "transaction.bulk.save":
                        assert result.status == OnboardingStatus.PENDING

                assert result is not None
                assert result.status == OnboardingStatus.SKIPPED
                assert result.skipped_at is not None
                assert result.completed_at is None
                assert {step.step_id: step.status for step in result.steps or []} == dict.fromkeys(ONBOARDING_FLOW_STEPS[flow], OnboardingStatus.SKIPPED)
            finally:
                await session.rollback()
                user = await session.get(User, user_id)
                if user is not None:
                    await session.delete(user)
                    await session.commit()


class TestOnboardingServiceTransition:
    """Tests for transition_onboarding_progress() (complete/skip)."""

    @staticmethod
    async def _make_user(session, marker: str):
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"onb_{marker}_{unique_id}",
            email=f"onb_{marker}_{unique_id}@example.com",
            password="TestPassword123!",
        )
        assert error is None
        assert user is not None and user.id is not None
        user_id = user.id  # capture now: the session expires ORM attrs on commit
        _OWNED_ONBOARDING_USER_IDS.add(user_id)
        return user_id

    @pytest.mark.asyncio
    async def test_complete_sets_completed_at_and_clears_skipped_at(self):
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            transition_onboarding_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "complete")
            flow = OnboardingFlow.WELCOME

            item = await transition_onboarding_progress(
                user_id=user_id,
                flow=flow,
                target_status=OnboardingStatus.COMPLETED,
                expected_version=ONBOARDING_FLOW_VERSIONS[flow],
                session=session,
            )

            assert item.status == OnboardingStatus.COMPLETED
            assert item.completed_at is not None
            assert item.skipped_at is None
            assert item.update_available is False

    @pytest.mark.asyncio
    async def test_skip_sets_skipped_at_and_clears_completed_at(self):
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            transition_onboarding_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "skip")
            flow = OnboardingFlow.IMPORT_GUIDE

            item = await transition_onboarding_progress(
                user_id=user_id,
                flow=flow,
                target_status=OnboardingStatus.SKIPPED,
                expected_version=ONBOARDING_FLOW_VERSIONS[flow],
                session=session,
            )

            assert item.status == OnboardingStatus.SKIPPED
            assert item.skipped_at is not None
            assert item.completed_at is None

    @pytest.mark.asyncio
    async def test_skipped_to_completed_explicit_transition_swaps_timestamps(self):
        """Replay-like: an explicit complete() call after skip() is allowed and
        must clear skipped_at while setting completed_at (never both set)."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            transition_onboarding_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "replay")
            flow = OnboardingFlow.INTRO_TOUR
            version = ONBOARDING_FLOW_VERSIONS[flow]

            skipped = await transition_onboarding_progress(user_id=user_id, flow=flow, target_status=OnboardingStatus.SKIPPED, expected_version=version, session=session)
            assert skipped.status == OnboardingStatus.SKIPPED
            assert skipped.skipped_at is not None
            assert skipped.completed_at is None

            completed = await transition_onboarding_progress(user_id=user_id, flow=flow, target_status=OnboardingStatus.COMPLETED, expected_version=version, session=session)

            assert completed.status == OnboardingStatus.COMPLETED
            assert completed.completed_at is not None
            assert completed.skipped_at is None, "Completing after a skip must clear skipped_at — never both set"

    @pytest.mark.asyncio
    async def test_repeat_same_transition_is_a_true_noop(self):
        """Idempotent terminal operation: calling complete() again with the same
        version must not change anything, including updated_at."""
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            transition_onboarding_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "repeat")
            flow = OnboardingFlow.WELCOME
            version = ONBOARDING_FLOW_VERSIONS[flow]

            first = await transition_onboarding_progress(user_id=user_id, flow=flow, target_status=OnboardingStatus.COMPLETED, expected_version=version, session=session)
            second = await transition_onboarding_progress(user_id=user_id, flow=flow, target_status=OnboardingStatus.COMPLETED, expected_version=version, session=session)

            assert second.model_dump() == first.model_dump(), "Repeating the same terminal transition must be a byte-identical no-op"

    @pytest.mark.asyncio
    async def test_progress_is_isolated_per_user(self):
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            get_onboarding_progress,
            transition_onboarding_progress,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_a_id = await self._make_user(session, "iso_a")
            user_b_id = await self._make_user(session, "iso_b")
            flow = OnboardingFlow.WELCOME

            await transition_onboarding_progress(
                user_id=user_a_id,
                flow=flow,
                target_status=OnboardingStatus.COMPLETED,
                expected_version=ONBOARDING_FLOW_VERSIONS[flow],
                session=session,
            )

            response_b = await get_onboarding_progress(user_b_id, session)
            item_b = next(i for i in response_b.flows if i.flow == flow)
            assert item_b.status == OnboardingStatus.PENDING, "User B must be unaffected by user A's completion"

            response_a = await get_onboarding_progress(user_a_id, session)
            item_a = next(i for i in response_a.flows if i.flow == flow)
            assert item_a.status == OnboardingStatus.COMPLETED


class TestOnboardingServiceCompleteWelcome:
    """Tests for complete_welcome_onboarding() — the atomic preferences+progress commit."""

    @staticmethod
    async def _make_user(session, marker: str):
        from backend.app.services import user_service  # noqa: PLC0415 — test setup — imports after db config

        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"onbw_{marker}_{unique_id}",
            email=f"onbw_{marker}_{unique_id}@example.com",
            password="TestPass123!",
        )
        assert error is None
        assert user is not None and user.id is not None
        user_id = user.id  # capture now: the session expires ORM attrs on commit
        _OWNED_ONBOARDING_USER_IDS.add(user_id)
        return user_id

    @pytest.mark.asyncio
    async def test_atomic_welcome_updates_language_currency_avatar_and_completes_progress(self):
        """A first-time welcome completion must create the settings row with the
        submitted preferences AND mark the welcome flow completed, in one call."""
        from sqlalchemy import select  # noqa: PLC0415
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus, UserSettings  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.schemas.settings import OnboardingWelcomeSettings  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            complete_welcome_onboarding,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "create")
            version = ONBOARDING_FLOW_VERSIONS[OnboardingFlow.WELCOME]

            item = await complete_welcome_onboarding(
                user_id=user_id,
                expected_version=version,
                welcome_settings=OnboardingWelcomeSettings(language="fr", base_currency="CHF", avatar_url="https://example.com/atomic-avatar.png"),
                session=session,
            )

            assert item.flow == OnboardingFlow.WELCOME
            assert item.status == OnboardingStatus.COMPLETED
            assert item.completed_at is not None
            assert item.skipped_at is None
            assert item.update_available is False

        # Verify from a fresh session: the settings row must reflect the submitted values.
        async with AsyncSession(engine) as verify_session:
            result = await verify_session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            settings = result.scalar_one()
            assert settings.language == "fr"
            assert settings.base_currency == "CHF"
            assert settings.avatar_url == "https://example.com/atomic-avatar.png"

    @pytest.mark.asyncio
    async def test_atomic_welcome_updates_existing_settings_without_touching_theme(self):
        """When a settings row already exists (e.g. via PUT /settings/user before welcome
        finishes), the atomic path must update language/currency/avatar and must not
        clobber a field it does not own (theme)."""
        from sqlalchemy import select  # noqa: PLC0415
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, UserSettings  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.schemas.settings import OnboardingWelcomeSettings, UserSettingsUpdate  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            complete_welcome_onboarding,
        )
        from backend.app.services.settings_service import update_user_settings  # noqa: PLC0415

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "existing")
            await update_user_settings(
                user_id,
                UserSettingsUpdate(language="en", base_currency="EUR", theme="dark", avatar_url=None),
                session,
            )
            version = ONBOARDING_FLOW_VERSIONS[OnboardingFlow.WELCOME]

            await complete_welcome_onboarding(
                user_id=user_id,
                expected_version=version,
                welcome_settings=OnboardingWelcomeSettings(language="it", base_currency="USD", avatar_url="https://example.com/existing-avatar.png"),
                session=session,
            )

        async with AsyncSession(engine) as verify_session:
            result = await verify_session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            settings = result.scalar_one()
            assert settings.language == "it"
            assert settings.base_currency == "USD"
            assert settings.avatar_url == "https://example.com/existing-avatar.png"
            assert settings.theme == "dark", "theme is not part of welcome_settings and must survive untouched"

    @pytest.mark.asyncio
    async def test_terminal_replay_remains_explicit_settings_reapplied_progress_untouched(self):
        """Calling complete_welcome_onboarding again at the same version is allowed
        (unlike a silently-ignored no-op): the settings write is re-applied explicitly
        with whatever the caller sends this time, while the already-terminal progress
        row is left exactly as it was (no wasted rewrite of an unchanged status)."""
        from sqlalchemy import select  # noqa: PLC0415
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, OnboardingStatus, UserSettings  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.schemas.settings import OnboardingWelcomeSettings  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            complete_welcome_onboarding,
        )

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            user_id = await self._make_user(session, "replay")
            version = ONBOARDING_FLOW_VERSIONS[OnboardingFlow.WELCOME]

            first = await complete_welcome_onboarding(
                user_id=user_id,
                expected_version=version,
                welcome_settings=OnboardingWelcomeSettings(language="en", base_currency="EUR", avatar_url=None),
                session=session,
            )
            assert first.status == OnboardingStatus.COMPLETED

            second = await complete_welcome_onboarding(
                user_id=user_id,
                expected_version=version,
                welcome_settings=OnboardingWelcomeSettings(language="es", base_currency="GBP", avatar_url="https://example.com/replay-avatar.png"),
                session=session,
            )

            assert second.status == OnboardingStatus.COMPLETED
            assert second.updated_at == first.updated_at, "an already-terminal row at the current version must not be rewritten"
            assert second.completed_at == first.completed_at

        async with AsyncSession(engine) as verify_session:
            result = await verify_session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            settings = result.scalar_one()
            assert settings.language == "es", "the replay's settings must be applied explicitly, not silently skipped"
            assert settings.base_currency == "GBP"
            assert settings.avatar_url == "https://example.com/replay-avatar.png"

    @pytest.mark.asyncio
    async def test_commit_failure_rolls_back_both_preferences_and_progress(self, monkeypatch):
        """A failure at the final commit must not leave a half-applied welcome: neither
        the settings row nor the progress row may reach disk. Verified from a fresh,
        unpatched session, per the asset-delete-bulk commit-failure pattern."""
        from sqlalchemy import select  # noqa: PLC0415
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import OnboardingFlow, UserOnboardingProgress, UserSettings  # noqa: PLC0415
        from backend.app.db.session import get_async_engine  # noqa: PLC0415
        from backend.app.schemas.settings import OnboardingWelcomeSettings  # noqa: PLC0415
        from backend.app.services.onboarding_service import (  # noqa: PLC0415
            ONBOARDING_FLOW_VERSIONS,
            complete_welcome_onboarding,
        )

        engine = get_async_engine()
        async with AsyncSession(engine, expire_on_commit=False) as setup_session:
            user_id = await self._make_user(setup_session, "commitfail")
        version = ONBOARDING_FLOW_VERSIONS[OnboardingFlow.WELCOME]

        async def failing_commit():
            raise RuntimeError("simulated commit failure")

        async with AsyncSession(engine, expire_on_commit=False) as session:
            monkeypatch.setattr(session, "commit", failing_commit)

            with pytest.raises(RuntimeError, match="simulated commit failure"):
                await complete_welcome_onboarding(
                    user_id=user_id,
                    expected_version=version,
                    welcome_settings=OnboardingWelcomeSettings(language="it", base_currency="CHF", avatar_url="https://example.com/rollback-avatar.png"),
                    session=session,
                )

        async with AsyncSession(engine, expire_on_commit=False) as verify_session:
            settings_result = await verify_session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            assert settings_result.scalar_one_or_none() is None, "a commit failure must roll back the tentative settings write"

            progress_result = await verify_session.execute(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user_id))
            assert progress_result.scalars().all() == [], "a commit failure must roll back the tentative progress insert too — not even a pending row survives"
