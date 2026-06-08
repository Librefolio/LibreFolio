"""
Settings API endpoints.

Endpoints for managing user and global settings.
"""

from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.settings import (
    GlobalSettingRead,
    GlobalSettingsListResponse,
    GlobalSettingUpdate,
    UserSettingsRead,
    UserSettingsUpdate,
)
from backend.app.services.scheduler import read_job_log
from backend.app.services.scheduler.state import load_state
from backend.app.services.settings_service import (
    get_all_global_settings,
    get_global_setting,
    get_or_create_user_settings,
    initialize_global_settings,
    update_global_setting,
    update_user_settings,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


# ============================================================================
# ADMIN DEPENDENCY
# ============================================================================


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency that requires the user to be an admin."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ============================================================================
# USER SETTINGS ENDPOINTS
# ============================================================================


@router.get("/user", response_model=UserSettingsRead)
async def get_user_settings_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> UserSettingsRead:
    """
    Get current user's settings.

    Creates default settings if they don't exist.
    """
    return await get_or_create_user_settings(current_user.id, session)


@router.put("/user", response_model=UserSettingsRead)
async def update_user_settings_endpoint(
    updates: UserSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> UserSettingsRead:
    """
    Update current user's settings.

    All fields are optional. Only provided fields will be updated.
    """
    logger.info(
        "Updating user settings",
        user_id=current_user.id,
        updates=updates.model_dump(exclude_none=True),
    )
    return await update_user_settings(current_user.id, updates, session)


# ============================================================================
# GLOBAL SETTINGS ENDPOINTS
# ============================================================================


@router.get("/global", response_model=GlobalSettingsListResponse)
async def list_global_settings(
    session: AsyncSession = Depends(get_session_generator),
) -> GlobalSettingsListResponse:
    """
    List all global settings.

    Public read access - anyone can view global settings.
    """
    settings = await get_all_global_settings(session)
    return GlobalSettingsListResponse(items=settings)


@router.get("/global/{key}", response_model=GlobalSettingRead)
async def get_global_setting_endpoint(key: str, session: AsyncSession = Depends(get_session_generator)) -> GlobalSettingRead:
    """
    Get a specific global setting by key.

    Public read access.
    """
    setting = await get_global_setting(key, session)
    if not setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Setting '{key}' not found")
    return setting


@router.put("/global/{key}", response_model=GlobalSettingRead)
async def update_global_setting_endpoint(
    key: str,
    update: GlobalSettingUpdate,
    admin: Annotated[User, Depends(require_admin)],
    session: AsyncSession = Depends(get_session_generator),
) -> GlobalSettingRead:
    """
    Update a global setting.

    Admin only - requires is_superuser=True.
    """
    logger.info("Updating global setting", key=key, value=update.value, admin_id=admin.id)

    result = await update_global_setting(key, update.value, admin.id, session)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Setting '{key}' not found")
    return result


@router.post("/global/initialize", status_code=status.HTTP_200_OK)
async def initialize_global_settings_endpoint(
    admin: Annotated[User, Depends(require_admin)],
    session: AsyncSession = Depends(get_session_generator),
) -> dict:
    """
    Initialize global settings with default values.

    Admin only. Creates only missing settings.
    """
    created = await initialize_global_settings(session)
    return {"message": f"Initialized {created} global settings"}


@router.get("/scheduler/state")
async def get_scheduler_state(
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """
    Get scheduler state (last execution info) — admin only.

    Returns last run timestamps, durations, and item counts
    for both current-price refresh and history sync jobs.
    """
    state = load_state()

    # Determine server timezone name
    try:
        server_tz = datetime.now().astimezone().strftime("%Z")
    except Exception:
        server_tz = "UTC"

    return {
        "current_price": {
            "last_run_at": state.current_price.last_run_at,
            "last_duration_s": state.current_price.last_duration_s,
            "last_status": state.current_price.last_status,
            "last_items_ok": state.current_price.last_items_ok,
            "last_items_err": state.current_price.last_items_err,
        },
        "history_sync": {
            "last_run_at": state.history_sync.last_run_at,
            "last_duration_s": state.history_sync.last_duration_s,
            "last_status": state.history_sync.last_status,
            "last_items_ok": state.history_sync.last_items_ok,
            "last_items_err": state.history_sync.last_items_err,
        },
        "server_tz": server_tz,
    }


@router.get("/scheduler/log")
async def get_scheduler_log(
    admin: Annotated[User, Depends(require_admin)],
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Get scheduler job log entries (newest first) — admin only.

    Returns per-item detail for each scheduler job run, including
    which assets/pairs succeeded or failed and why.
    Paginated with limit/offset (max 100 per page).
    """
    limit = min(limit, 100)
    entries = read_job_log(limit=limit, offset=offset)
    return {"entries": entries, "count": len(entries), "offset": offset}
