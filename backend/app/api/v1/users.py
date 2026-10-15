"""
User endpoints.

Provides user search functionality for features like broker sharing.
Does NOT expose email for privacy (GDPR compliance).
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.settings import require_admin
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.users import (
    AdminUserListResponse,
    AdminUserRead,
    AdminUserUpdateRequest,
    InviteCreateRequest,
    InviteCreateResponse,
    InviteListResponse,
    InviteRead,
    LinkTokenResponse,
    OnboardingResetRequest,
    UserSearchItem,
    UserSearchResponse,
    UserUsageRead,
)
from backend.app.services.accounts import registration_service, token_service, user_service
from backend.app.services.accounts.onboarding_service import reset_onboarding_progress
from backend.app.services.accounts.registration_service import RegistrationError
from backend.app.services.accounts.user_service import search_users

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


# =============================================================================
# Administration (admin only)
# Static paths first: /users/invites must not be read as /users/{user_id}.
# =============================================================================


def _usage_read(usage: registration_service.UserUsage) -> UserUsageRead:
    """The usage of the instance as administrators see it, the subscription link included."""
    return UserUsageRead(used=usage.used, max_users=usage.max_users, billing_url=registration_service.billing_link())


def _limit_reached(usage: registration_service.UserUsage) -> HTTPException:
    """409 for an administrator who asks past the limit: with the numbers and the subscription link."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error_code": "USER_LIMIT_REACHED", "message": "The instance has reached its maximum number of users", "limit": usage.max_users, "used": usage.used, "billing_url": registration_service.billing_link()},
    )


def _invite_read(invite: AccountToken) -> InviteRead:
    return InviteRead(id=invite.id, grants_admin=invite.grants_admin, email=invite.email, created_at=invite.created_at, expires_at=invite.expires_at, created_by_user_id=invite.created_by_user_id)


def _admin_user_read(user: User) -> AdminUserRead:
    return AdminUserRead(id=user.id, username=user.username, email=user.email, is_active=user.is_active, is_superuser=user.is_superuser, created_at=user.created_at)


async def _user_or_404(session: AsyncSession, user_id: int) -> User:
    user = await user_service.get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/invites", response_model=InviteListResponse, summary="List the live invitations (admin)")
async def list_invites(admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> InviteListResponse:
    """The invitations still waiting to be used, oldest first, with the usage of the instance."""
    invites = await registration_service.list_pending_invites(session)
    return InviteListResponse(items=[_invite_read(invite) for invite in invites], usage=_usage_read(await registration_service.user_usage(session)))


@router.post("/invites", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED, summary="Create an invitation (admin)")
async def create_invite(request: InviteCreateRequest, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> InviteCreateResponse:
    """Create an invitation and return its link, once. Refused when registration is disabled or no place is left."""
    try:
        issued = await registration_service.create_invite(session, created_by_user_id=admin.id, grants_admin=request.grants_admin, email=request.email)
    except RegistrationError as exc:
        await session.rollback()
        if exc.code == "USER_LIMIT_REACHED":
            raise _limit_reached(await registration_service.user_usage(session)) from None
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": exc.code, "message": exc.message}) from None
    await session.commit()
    path = token_service.token_path(AccountTokenPurpose.INVITE, issued.token)
    return InviteCreateResponse(invite=_invite_read(issued.record), token=issued.token, path=path, url=registration_service.public_link(path))


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke an invitation (admin)")
async def revoke_invite(invite_id: int, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> Response:
    """Revoke a live invitation: its link stops working and its place is freed."""
    if not await registration_service.revoke_invite(session, invite_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    await session.commit()
    logger.info("Invitation revoked by an administrator", invite_id=invite_id, admin_id=admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=AdminUserListResponse, summary="List every account (admin)")
async def list_accounts(admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> AdminUserListResponse:
    """Every account, oldest first, with the usage of the instance."""
    users = await user_service.list_users(session)
    return AdminUserListResponse(items=[_admin_user_read(user) for user in users], usage=_usage_read(await registration_service.user_usage(session)))


@router.patch("/{user_id}", response_model=AdminUserRead, summary="Activate, deactivate, promote or demote an account (admin)")
async def update_account(user_id: int, request: AdminUserUpdateRequest, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> AdminUserRead:
    """Change whether an account is active and an administrator, all or nothing.

    The last active administrator can be neither deactivated nor demoted (409 ``LAST_ADMIN``); a reactivation needs a
    free place (409 ``USER_LIMIT_REACHED``). Deactivating or demoting ends every session of the account.
    """
    user = await _user_or_404(session, user_id)
    if request.is_active is True and not user.is_active:
        usage = await registration_service.user_usage(session)
        if usage.full:
            raise _limit_reached(usage)
    if await user_service.update_user_status(session, user, is_active=request.is_active, is_superuser=request.is_superuser) == "LAST_ADMIN":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "LAST_ADMIN", "message": "The last active administrator can be neither deactivated nor demoted"})
    logger.info("Account updated by an administrator", user_id=user.id, admin_id=admin.id, is_active=user.is_active, is_superuser=user.is_superuser)
    return _admin_user_read(user)


@router.post("/{user_id}/password-reset-link", response_model=LinkTokenResponse, status_code=status.HTTP_201_CREATED, summary="Create a password-reset link (admin)")
async def create_password_reset_link(user_id: int, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> LinkTokenResponse:
    """A single-use link to set a new password, shown once; the links issued before for that account stop working."""
    user = await _user_or_404(session, user_id)
    issued = await user_service.create_password_reset(session, user, created_by_user_id=admin.id)
    await session.commit()
    path = token_service.token_path(AccountTokenPurpose.PASSWORD_RESET, issued.token)
    return LinkTokenResponse(token=issued.token, path=path, url=registration_service.public_link(path), expires_at=issued.record.expires_at)


@router.post("/{user_id}/sessions/revoke", status_code=status.HTTP_204_NO_CONTENT, summary="Sign an account out everywhere (admin)")
async def revoke_account_sessions(user_id: int, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> Response:
    """End every session of the account: each device is signed out at its next request."""
    user = await _user_or_404(session, user_id)
    user_service.end_sessions(user)
    session.add(user)
    await session.commit()
    logger.info("Sessions ended by an administrator", user_id=user.id, admin_id=admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/onboarding/reset", status_code=status.HTTP_204_NO_CONTENT, summary="Restart the onboarding of an account (admin)")
async def reset_account_onboarding(
    user_id: int,
    admin: Annotated[User, Depends(require_admin)],
    request: Optional[OnboardingResetRequest] = None,
    session: AsyncSession = Depends(get_session_generator),
) -> Response:
    """Put the onboarding flows of the account — all of them, or ``flow`` — back to pending, steps included."""
    user = await _user_or_404(session, user_id)
    flow = request.flow if request is not None else None
    await reset_onboarding_progress(session, user.id, flow)
    logger.info("Onboarding reset by an administrator", user_id=user.id, admin_id=admin.id, flow=flow.value if flow else None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
