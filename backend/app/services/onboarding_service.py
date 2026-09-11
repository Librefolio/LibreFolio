"""Versioned per-user onboarding progress."""

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    OnboardingFlow,
    OnboardingStatus,
    UserOnboardingProgress,
    UserSettings,
)
from backend.app.schemas.settings import (
    SETTINGS_REGISTRY,
    OnboardingProgressItem,
    OnboardingProgressResponse,
    OnboardingWelcomeSettings,
)
from backend.app.services.global_settings_service import get_setting_value
from backend.app.utils.datetime_utils import utcnow

ONBOARDING_FLOW_VERSIONS: Mapping[OnboardingFlow, int] = {
    OnboardingFlow.WELCOME: 1,
    OnboardingFlow.INTRO_TOUR: 1,
    OnboardingFlow.BROKER_GUIDE: 1,
    OnboardingFlow.FX_GUIDE: 1,
    OnboardingFlow.ASSET_GUIDE: 1,
    OnboardingFlow.IMPORT_GUIDE: 1,
}


class OnboardingVersionMismatchError(ValueError):
    """Raised when a client completes content older or newer than the server."""

    def __init__(self, flow: OnboardingFlow, expected_version: int, current_version: int) -> None:
        self.flow = flow
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(f"Onboarding flow '{flow.value}' version mismatch: " f"client={expected_version}, server={current_version}")


def _to_progress_item(row: UserOnboardingProgress) -> OnboardingProgressItem:
    current_version = ONBOARDING_FLOW_VERSIONS[row.flow]
    return OnboardingProgressItem(
        flow=row.flow,
        status=row.status,
        version=row.version,
        current_version=current_version,
        update_available=row.version < current_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
        skipped_at=row.skipped_at,
    )


async def _get_progress_rows(
    user_id: int,
    session: AsyncSession,
) -> dict[OnboardingFlow, UserOnboardingProgress]:
    result = await session.execute(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user_id))
    return {OnboardingFlow(row.flow): row for row in result.scalars().all()}


async def _ensure_onboarding_progress_uncommitted(
    user_id: int,
    session: AsyncSession,
) -> dict[OnboardingFlow, UserOnboardingProgress]:
    """Insert only missing flow rows without committing the caller's transaction."""
    now = utcnow()
    statement = (
        sqlite_insert(UserOnboardingProgress)
        .values(
            [
                {
                    "user_id": user_id,
                    "flow": flow.value,
                    "status": OnboardingStatus.PENDING.value,
                    "version": version,
                    "created_at": now,
                    "updated_at": now,
                }
                for flow, version in ONBOARDING_FLOW_VERSIONS.items()
            ]
        )
        .on_conflict_do_nothing(index_elements=["user_id", "flow"])
    )
    await session.execute(statement)

    rows = await _get_progress_rows(user_id, session)
    missing = set(ONBOARDING_FLOW_VERSIONS) - set(rows)
    if missing:
        missing_values = ", ".join(sorted(flow.value for flow in missing))
        raise RuntimeError(f"onboarding progress missing after upsert for user_id={user_id}: " f"{missing_values}")
    return rows


async def ensure_onboarding_progress(
    user_id: int,
    session: AsyncSession,
) -> dict[OnboardingFlow, UserOnboardingProgress]:
    """Insert only missing flow rows; never rewrite persisted progress."""
    await _ensure_onboarding_progress_uncommitted(user_id, session)
    await session.commit()
    return await _get_progress_rows(user_id, session)


async def get_onboarding_progress(
    user_id: int,
    session: AsyncSession,
) -> OnboardingProgressResponse:
    """Get every registered flow, creating only missing rows as pending."""
    rows = await ensure_onboarding_progress(user_id, session)
    return OnboardingProgressResponse(flows=[_to_progress_item(rows[flow]) for flow in ONBOARDING_FLOW_VERSIONS])


async def transition_onboarding_progress(
    user_id: int,
    flow: OnboardingFlow,
    target_status: OnboardingStatus,
    expected_version: int,
    session: AsyncSession,
) -> OnboardingProgressItem:
    """Apply an explicit terminal transition for the current content version."""
    if target_status not in {
        OnboardingStatus.COMPLETED,
        OnboardingStatus.SKIPPED,
    }:
        raise ValueError(f"Unsupported onboarding terminal status: {target_status.value}")

    current_version = ONBOARDING_FLOW_VERSIONS[flow]
    if expected_version != current_version:
        raise OnboardingVersionMismatchError(
            flow=flow,
            expected_version=expected_version,
            current_version=current_version,
        )

    rows = await _ensure_onboarding_progress_uncommitted(user_id, session)
    row = rows[flow]
    if row.status == target_status and row.version == current_version:
        return _to_progress_item(row)

    now = utcnow()
    row.status = target_status
    row.version = current_version
    row.updated_at = now
    if target_status == OnboardingStatus.COMPLETED:
        row.completed_at = now
        row.skipped_at = None
    else:
        row.skipped_at = now
        row.completed_at = None

    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_progress_item(row)


async def complete_welcome_onboarding(
    user_id: int,
    expected_version: int,
    welcome_settings: OnboardingWelcomeSettings,
    session: AsyncSession,
) -> OnboardingProgressItem:
    """Commit welcome preferences and terminal progress in one transaction."""
    current_version = ONBOARDING_FLOW_VERSIONS[OnboardingFlow.WELCOME]
    if expected_version != current_version:
        raise OnboardingVersionMismatchError(
            flow=OnboardingFlow.WELCOME,
            expected_version=expected_version,
            current_version=current_version,
        )

    try:
        rows = await _ensure_onboarding_progress_uncommitted(user_id, session)
        row = rows[OnboardingFlow.WELCOME]

        result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        settings = result.scalar_one_or_none()
        now = utcnow()
        if settings is None:
            settings = UserSettings(
                user_id=user_id,
                language=welcome_settings.language,
                base_currency=welcome_settings.base_currency,
                theme=await get_setting_value(
                    session,
                    SETTINGS_REGISTRY.global_.DEFAULT_THEME.key,
                    "auto",
                ),
                avatar_url=welcome_settings.avatar_url,
                created_at=now,
                updated_at=now,
            )
        else:
            settings.language = welcome_settings.language
            settings.base_currency = welcome_settings.base_currency
            settings.avatar_url = welcome_settings.avatar_url
            settings.updated_at = now
        session.add(settings)

        if row.status != OnboardingStatus.COMPLETED or row.version != current_version:
            row.status = OnboardingStatus.COMPLETED
            row.version = current_version
            row.updated_at = now
            row.completed_at = now
            row.skipped_at = None
            session.add(row)

        await session.commit()
        await session.refresh(row)
        return _to_progress_item(row)
    except Exception:
        await session.rollback()
        raise
