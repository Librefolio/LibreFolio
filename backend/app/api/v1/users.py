"""
User endpoints.

Provides user search functionality for features like broker sharing.
Does NOT expose email for privacy (GDPR compliance).
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import deletion_preview_read, get_current_user
from backend.app.api.v1.settings import require_admin
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import begin_writes, get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.users import (
    AccountDeletionPreviewRead,
    AddressProbeIssued,
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
from backend.app.services.accounts import address_probe, registration_service, token_service, user_service
from backend.app.services.accounts.onboarding_service import reset_onboarding_progress
from backend.app.services.accounts.registration_service import RegistrationError
from backend.app.services.accounts.user_service import search_users
from backend.app.services.email import verification as email_verification
from backend.app.services.platform.instance_key import InstanceKeyError

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


def _admin_user_read(user: User, *, holds_place: bool = False, pending_setup: bool = False) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        protected=user_service.account_protection(user) is not None,
        holds_place=holds_place,
        pending_setup=pending_setup,
    )


def _protected(user: User) -> Optional[HTTPException]:
    """409 ``ACCOUNT_PROTECTED`` when nobody may delete, deactivate or demote ``user``."""
    reason = user_service.account_protection(user)
    if reason is None:
        return None
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "ACCOUNT_PROTECTED", "message": "This account cannot be deleted, deactivated or demoted", "reason": reason})


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


@router.post("/address-probe", response_model=AddressProbeIssued, summary="A nonce to check that this instance answers at another address (admin)")
def issue_address_probe(admin: Annotated[User, Depends(require_admin)]) -> AddressProbeIssued:
    """A short-lived signed nonce: ``GET <address>/api/v1/auth/address-probe?nonce=…`` answers ``match: true`` only
    when this instance answers at that address. Sync: deriving the key reads the instance key file. An instance key
    that cannot be used answers 503 ``INSTANCE_KEY_UNAVAILABLE`` (H-19): the configuration checks say why.
    """
    try:
        nonce, expires_at = address_probe.issue_probe_nonce()
    except InstanceKeyError:
        logger.warning("Address probe: the instance key cannot be used, no nonce issued", admin_id=admin.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "INSTANCE_KEY_UNAVAILABLE", "message": "The instance key cannot be used: see the configuration checks"},
        ) from None
    return AddressProbeIssued(nonce=nonce, expires_at=expires_at)


@router.get("", response_model=AdminUserListResponse, summary="List every account (admin)")
async def list_accounts(admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> AdminUserListResponse:
    """Every account, oldest first, with the usage of the instance."""
    users = await user_service.list_users(session)
    # The waiting accounts whose live verification link already holds their place: Reactivate needs no free one (workstream E)
    holders = await email_verification.place_holders(session)
    # The initial administrator waiting for its setup link (F02): the tab offers it no reactivation
    pending = await registration_service.pending_admin_ids(session)
    return AdminUserListResponse(
        items=[_admin_user_read(user, holds_place=user.id in holders, pending_setup=user.id in pending) for user in users],
        usage=_usage_read(await registration_service.user_usage(session)),
    )


#: The refusal of a reactivation or a demotion of the initial administrator waiting for its setup (F02, A-43).
_PENDING_SETUP_DETAIL = {"error_code": "PENDING_SETUP", "message": "This administrator activates the account through its setup link"}


@router.patch("/{user_id}", response_model=AdminUserRead, summary="Activate, deactivate, promote or demote an account (admin)")
async def update_account(user_id: int, request: AdminUserUpdateRequest, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> AdminUserRead:
    """Change whether an account is active and an administrator, all or nothing.

    A protected account is neither deactivated nor demoted (409 ``ACCOUNT_PROTECTED``, before any other refusal). The
    last active administrator can be neither deactivated nor demoted (409 ``LAST_ADMIN``); a reactivation needs a free
    place (409 ``USER_LIMIT_REACHED``), except for an account waiting for its email verification with a live link,
    which already holds one. The initial administrator waiting for its setup (F02) is neither reactivated nor demoted
    here (409 ``PENDING_SETUP``): nobody knows its password, and it keeps its role until its setup. Deactivating it
    cancels its setup link (A-43): the link stops working and the account keeps waiting; a protected one refuses that
    too. With ``cancel_setup`` the request is that cancellation and nothing else: an account that no longer waits — its
    setup done since the caller looked — answers 409 ``SETUP_COMPLETED``, nothing changed (A-51). The service decides
    under SQLite's write lock, from the account as it is then. Deactivating or demoting ends every session of the account.
    """
    user = await _user_or_404(session, user_id)
    pending = await registration_service.is_pending_admin(session, user)
    deactivate = request.is_active is False and user.is_active
    # Deactivating the initial administrator waiting for its setup, already inactive, cancels its setup link (A-43):
    # a deactivation all the same, which a protected account refuses
    cancel = request.is_active is False and pending
    demote = request.is_superuser is False and user.is_superuser
    if (deactivate or cancel or demote) and (refusal := _protected(user)):
        raise refusal
    if demote and pending:
        # The initial administrator keeps its role until its setup (A-43): to cancel it, deactivate it or delete it
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PENDING_SETUP_DETAIL)
    if request.is_active is True and not user.is_active:
        if pending:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PENDING_SETUP_DETAIL)
        usage = await registration_service.user_usage(session)
        # An account waiting for its email verification already holds its place while its link is live (workstream E).
        if usage.full and not await email_verification.holds_place(session, user):
            raise _limit_reached(usage)
    outcome = await user_service.update_user_status(session, user, is_active=request.is_active, is_superuser=request.is_superuser, cancel_setup=request.cancel_setup)
    if outcome == "LAST_ADMIN":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "LAST_ADMIN", "message": "The last active administrator can be neither deactivated nor demoted"})
    if outcome == "SETUP_COMPLETED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "SETUP_COMPLETED", "message": "This account does not wait for its setup: nothing was changed"})
    logger.info("Account updated by an administrator", user_id=user.id, admin_id=admin.id, is_active=user.is_active, is_superuser=user.is_superuser)
    # The answer replaces the row in the Users tab: it carries the same flags as the list (workstream E, F02).
    return _admin_user_read(user, holds_place=await email_verification.holds_place(session, user), pending_setup=await registration_service.is_pending_admin(session, user))


@router.get("/{user_id}/deletion-preview", response_model=AccountDeletionPreviewRead, summary="What deleting an account would take with it (admin)")
async def preview_account_deletion(user_id: int, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> AccountDeletionPreviewRead:
    """The brokers that would go with the account, those where only its access would go, and the transfers left
    unpaired. Nothing is written.
    """
    preview = await user_service.preview_user_deletion(session, user_id)
    if preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return deletion_preview_read(preview)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an account (admin)")
async def delete_account(user_id: int, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> Response:
    """Delete an account by the rule of deleting one's own: its brokers per ``deletion-preview``, then the account.

    Refused for the caller's own account (409 ``SELF_DELETION``: that is deleted from the profile), for a protected
    account (409 ``ACCOUNT_PROTECTED``, before any other answer: demoting it would be refused too) and for an
    administrator (409 ``DEMOTE_FIRST``: demote it first, so the last one never goes from here) — but the initial
    administrator waiting for its setup, which cannot be demoted and never was an active one: deleting it is the hard
    cancellation of its setup (A-43); whether it still waits is read again under SQLite's write lock, so one that has just
    completed its setup answers ``DEMOTE_FIRST`` (A-51). All or nothing; cannot be undone.
    """
    user = await _user_or_404(session, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "SELF_DELETION", "message": "Delete your own account from your profile"})
    if refusal := _protected(user):
        raise refusal
    demote_first = {"error_code": "DEMOTE_FIRST", "message": "An administrator must be demoted before it can be deleted"}
    pending = await registration_service.is_pending_admin(session, user)
    if user.is_superuser and not pending:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=demote_first)
    if pending:
        # Read again under SQLite's write lock (A-51): a setup completed since the read above has made it an active
        # administrator, which goes only after its demotion
        await begin_writes(session, User)
        await session.refresh(user)
        if not await registration_service.is_pending_admin(session, user):
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=demote_first)
    # A failed deletion rolls the session back and expires every object in it, the caller's included: read them first
    username, admin_id = user.username, admin.id
    try:
        result = await user_service.delete_account(session, user)
    except Exception as exc:
        logger.exception("Account deletion by an administrator failed: nothing was deleted", user_id=user_id, admin_id=admin_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Account deletion failed: nothing was deleted") from exc
    logger.warning("Account deleted by an administrator", user_id=user_id, username=username, admin_id=admin_id, brokers_deleted=result.deleted_broker_ids, files_removed=result.files_removed)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    await user_service.end_sessions(session, user)
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
