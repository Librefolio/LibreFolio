"""Versioned per-user onboarding progress."""

from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    OnboardingFlow,
    OnboardingStatus,
    UserOnboardingProgress,
    UserOnboardingStepProgress,
    UserSettings,
)
from backend.app.schemas.settings import (
    SETTINGS_REGISTRY,
    OnboardingProgressItem,
    OnboardingProgressResponse,
    OnboardingStepProgressItem,
    OnboardingWelcomeSettings,
)
from backend.app.services.global_settings_service import get_setting_value
from backend.app.utils.datetime_utils import utcnow

ONBOARDING_FLOW_VERSIONS: Mapping[OnboardingFlow, int] = {
    OnboardingFlow.WELCOME: 1,
    OnboardingFlow.INTRO_TOUR: 1,
    OnboardingFlow.TRANSACTIONS_PAGE_GUIDE: 1,
    OnboardingFlow.TRANSACTION_CREATE_GUIDE: 1,
    OnboardingFlow.TRANSACTION_BULK_GUIDE: 1,
    OnboardingFlow.IMPORT_GUIDE: 1,
    OnboardingFlow.BROKER_PAGE_GUIDE: 1,
    OnboardingFlow.BROKER_GUIDE: 1,
    OnboardingFlow.BROKER_DETAIL_GUIDE: 1,
    OnboardingFlow.FX_PAGE_GUIDE: 1,
    OnboardingFlow.FX_GUIDE: 1,
    OnboardingFlow.FX_DETAIL_GUIDE: 1,
    OnboardingFlow.ASSET_PAGE_GUIDE: 1,
    OnboardingFlow.ASSET_GUIDE: 1,
    OnboardingFlow.ASSET_DETAIL_GUIDE: 1,
}

ONBOARDING_FLOW_STEPS: Mapping[OnboardingFlow, tuple[str, ...]] = {
    OnboardingFlow.TRANSACTION_BULK_GUIDE: (
        "transaction.bulk.workspace",
        "transaction.bulk.validation",
        "transaction.bulk.selection",
        "transaction.bulk.save",
    ),
    OnboardingFlow.IMPORT_GUIDE: (
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


class OnboardingVersionMismatchError(ValueError):
    """Raised when a client completes content older or newer than the server."""

    def __init__(self, flow: OnboardingFlow, expected_version: int, current_version: int) -> None:
        self.flow = flow
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(f"Onboarding flow '{flow.value}' version mismatch: " f"client={expected_version}, server={current_version}")


def _to_step_progress_item(row: UserOnboardingStepProgress, current_version: int) -> OnboardingStepProgressItem:
    return OnboardingStepProgressItem(
        step_id=row.step_id,
        status=row.status,
        version=row.version,
        current_version=current_version,
        update_available=row.version < current_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
        skipped_at=row.skipped_at,
    )


def _to_progress_item(
    row: UserOnboardingProgress,
    step_rows: Mapping[tuple[OnboardingFlow, str], UserOnboardingStepProgress] | None = None,
    *,
    include_steps: bool = True,
) -> OnboardingProgressItem:
    current_version = ONBOARDING_FLOW_VERSIONS[row.flow]
    registered_steps = ONBOARDING_FLOW_STEPS.get(row.flow, ())
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
        steps=([_to_step_progress_item(step_rows[(row.flow, step_id)], current_version) for step_id in registered_steps] if include_steps and step_rows is not None and registered_steps else None),
    )


async def _get_progress_rows(
    user_id: int,
    session: AsyncSession,
) -> dict[OnboardingFlow, UserOnboardingProgress]:
    result = await session.execute(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user_id))
    rows: dict[OnboardingFlow, UserOnboardingProgress] = {}
    for row in result.scalars().all():
        try:
            rows[OnboardingFlow(row.flow)] = row
        except ValueError:
            continue
    return rows


async def _get_step_progress_rows(
    user_id: int,
    session: AsyncSession,
) -> dict[tuple[OnboardingFlow, str], UserOnboardingStepProgress]:
    result = await session.execute(select(UserOnboardingStepProgress).where(UserOnboardingStepProgress.user_id == user_id))
    rows: dict[tuple[OnboardingFlow, str], UserOnboardingStepProgress] = {}
    for row in result.scalars().all():
        try:
            rows[(OnboardingFlow(row.flow), row.step_id)] = row
        except ValueError:
            continue
    return rows


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
    step_values = [
        {
            "user_id": user_id,
            "flow": flow.value,
            "step_id": step_id,
            "status": OnboardingStatus.PENDING.value,
            "version": ONBOARDING_FLOW_VERSIONS[flow],
            "created_at": now,
            "updated_at": now,
        }
        for flow, step_ids in ONBOARDING_FLOW_STEPS.items()
        for step_id in step_ids
    ]
    if step_values:
        await session.execute(sqlite_insert(UserOnboardingStepProgress).values(step_values).on_conflict_do_nothing(index_elements=["user_id", "flow", "step_id"]))

    rows = await _get_progress_rows(user_id, session)
    missing = set(ONBOARDING_FLOW_VERSIONS) - set(rows)
    if missing:
        missing_values = ", ".join(sorted(flow.value for flow in missing))
        raise RuntimeError(f"onboarding progress missing after upsert for user_id={user_id}: " f"{missing_values}")
    step_rows = await _get_step_progress_rows(user_id, session)
    missing_steps = {(flow, step_id) for flow, step_ids in ONBOARDING_FLOW_STEPS.items() for step_id in step_ids if (flow, step_id) not in step_rows}
    if missing_steps:
        missing_values = ", ".join(sorted(f"{flow.value}:{step_id}" for flow, step_id in missing_steps))
        raise RuntimeError(f"onboarding step progress missing after upsert for user_id={user_id}: {missing_values}")
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
    step_rows = await _get_step_progress_rows(user_id, session)
    return OnboardingProgressResponse(
        flows=[_to_progress_item(rows[flow], step_rows) for flow in ONBOARDING_FLOW_VERSIONS],
    )


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
    if flow in ONBOARDING_FLOW_STEPS:
        step_rows = await _get_step_progress_rows(user_id, session)
        now = utcnow()
        for step_id in ONBOARDING_FLOW_STEPS[flow]:
            step_row = step_rows[(flow, step_id)]
            step_row.status = target_status
            step_row.version = current_version
            step_row.updated_at = now
            if target_status == OnboardingStatus.COMPLETED:
                step_row.completed_at = now
                step_row.skipped_at = None
            else:
                step_row.skipped_at = now
                step_row.completed_at = None
            session.add(step_row)
        _apply_step_flow_aggregate(row, flow, step_rows, now)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _to_progress_item(row, step_rows, include_steps=False)
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


def _apply_step_flow_aggregate(
    flow_row: UserOnboardingProgress,
    flow: OnboardingFlow,
    step_rows: Mapping[tuple[OnboardingFlow, str], UserOnboardingStepProgress],
    now: datetime,
) -> None:
    current_version = ONBOARDING_FLOW_VERSIONS[flow]
    registered = [step_rows[(flow, step_id)] for step_id in ONBOARDING_FLOW_STEPS[flow]]
    current_terminal = [row for row in registered if row.version == current_version and row.status in {OnboardingStatus.COMPLETED, OnboardingStatus.SKIPPED}]

    flow_row.version = current_version
    flow_row.updated_at = now
    if len(current_terminal) != len(registered):
        flow_row.status = OnboardingStatus.PENDING
        flow_row.completed_at = None
        flow_row.skipped_at = None
        return
    if all(row.status == OnboardingStatus.SKIPPED for row in registered):
        flow_row.status = OnboardingStatus.SKIPPED
        flow_row.completed_at = None
        flow_row.skipped_at = now
        return
    flow_row.status = OnboardingStatus.COMPLETED
    flow_row.completed_at = now
    flow_row.skipped_at = None


async def transition_onboarding_step_progress(
    user_id: int,
    flow: OnboardingFlow,
    step_id: str,
    target_status: OnboardingStatus,
    expected_version: int,
    session: AsyncSession,
) -> OnboardingProgressItem:
    """Apply one terminal step transition and recompute the aggregate flow."""
    if target_status not in {OnboardingStatus.COMPLETED, OnboardingStatus.SKIPPED}:
        raise ValueError(f"Unsupported onboarding step terminal status: {target_status.value}")
    registered_steps = ONBOARDING_FLOW_STEPS.get(flow)
    if registered_steps is None or step_id not in registered_steps:
        raise ValueError(f"Unsupported onboarding step '{flow.value}:{step_id}'")
    current_version = ONBOARDING_FLOW_VERSIONS[flow]
    if expected_version != current_version:
        raise OnboardingVersionMismatchError(flow=flow, expected_version=expected_version, current_version=current_version)

    flow_rows = await _ensure_onboarding_progress_uncommitted(user_id, session)
    step_rows = await _get_step_progress_rows(user_id, session)
    flow_row = flow_rows[flow]
    step_row = step_rows[(flow, step_id)]
    if step_row.status == target_status and step_row.version == current_version:
        return _to_progress_item(flow_row, step_rows)

    now = utcnow()
    step_row.status = target_status
    step_row.version = current_version
    step_row.updated_at = now
    if target_status == OnboardingStatus.COMPLETED:
        step_row.completed_at = now
        step_row.skipped_at = None
    else:
        step_row.skipped_at = now
        step_row.completed_at = None
    _apply_step_flow_aggregate(flow_row, flow, step_rows, now)

    session.add(step_row)
    session.add(flow_row)
    await session.commit()
    await session.refresh(step_row)
    await session.refresh(flow_row)
    step_rows[(flow, step_id)] = step_row
    return _to_progress_item(flow_row, step_rows)


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
