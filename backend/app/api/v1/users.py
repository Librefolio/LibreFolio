"""
User endpoints.

Provides user search functionality for features like broker sharing.
Does NOT expose email for privacy (GDPR compliance).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.users import UserSearchItem, UserSearchResponse
from backend.app.services.user_service import search_users

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/search", response_model=UserSearchResponse, response_model_exclude_unset=True, summary="Search users by username")
async def search_users_endpoint(
    q: str = Query("", description="Search query; empty lists all active users (used to pre-populate selects)"),
    exclude_broker_id: int | None = Query(None, description="Exclude users already on this broker"),
    admins: bool = Query(False, description="If true, return only superusers, each flagged is_admin=true"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Search for users by username (ILIKE match). Does NOT expose email for privacy. An empty query returns every active user so pickers can show the full list up-front. Optionally excludes users already having access to a specific broker. With admins=true, returns only superusers (used by the update-check hint that points non-admins to an administrator).
    """
    results = await search_users(
        session=session,
        query=q,
        exclude_broker_id=exclude_broker_id,
        admins_only=admins,
    )

    users = [UserSearchItem(**r) for r in results]
    return UserSearchResponse(items=users)
