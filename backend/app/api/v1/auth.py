"""
Authentication API Endpoints

Provides login, logout, and JWT-based session management.
"""

import asyncio
import math
from typing import Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.models import AccountTokenPurpose, User
from backend.app.db.session import get_session_generator
from backend.app.schemas.auth import (
    AddressProbeResult,
    AdminSetupRequest,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthMeResponse,
    AuthRegisterRequest,
    AuthRegisterResponse,
    AuthUserResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    TokenInspectRequest,
    TokenInspectResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
    WhatsNewRead,
)
from backend.app.schemas.users import AccountDeletionPreviewRead, BrokerAccessItemRead, BrokerDeletionItemRead
from backend.app.services.accounts import address_probe, bootstrap_admin_service, login_throttle, password_policy, registration_service, settings_service, token_service, user_service, whats_new_service
from backend.app.services.accounts.auth_service import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    verify_password,
    verify_password_or_dummy,
)
from backend.app.services.accounts.donation_popup_service import record_login_and_maybe_show_popup
from backend.app.services.accounts.global_settings_service import get_session_ttl_hours
from backend.app.services.accounts.registration_service import RegistrationError
from backend.app.services.email import flows as email_flows
from backend.app.services.email import verification as email_verification
from backend.app.services.platform.client_address import rate_limit_address

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _auth_user(user: User) -> AuthUserResponse:
    """The user as the app reads it, with what is new for it since the release it saw last (C-54)."""
    pending = whats_new_service.pending_for(user)
    whats_new = WhatsNewRead(since=pending.since, release=pending.release) if pending is not None else None
    return AuthUserResponse.model_validate(user).model_copy(update={"whats_new": whats_new})


# Session cookie configuration
SESSION_COOKIE_NAME = "session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
# SESSION_COOKIE_SECURE (config): auto | always | never — read once, so a wrong value stops the start.
SESSION_COOKIE_SECURE_MODE = get_settings().SESSION_COOKIE_SECURE


def session_cookie_secure(request: Request) -> bool:
    """Whether the session cookie this response sets or clears carries the Secure attribute.

    ``always`` and ``never`` decide alone. ``auto`` follows the browser: Secure on HTTPS, seen
    directly or reported by a reverse proxy as the first ``X-Forwarded-Proto`` value. The header
    counts whoever sent it, because it can only turn Secure on: a forged ``https`` breaks only the
    sender's own login, and ``never`` is the way out for a proxy that claims https to a browser
    on plain HTTP.
    """
    if SESSION_COOKIE_SECURE_MODE == "always":
        return True
    if SESSION_COOKIE_SECURE_MODE == "never":
        return False
    if request.url.scheme == "https":
        return True
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    return forwarded_proto.split(",", 1)[0].strip().lower() == "https"


def get_session_cookie(request: Request) -> str | None:
    """Extract session cookie from request."""
    return request.cookies.get(SESSION_COOKIE_NAME)


async def _session_ttl_hours(session: AsyncSession) -> int:
    """The session lifetime from the global settings, or 24 hours when they cannot be read."""
    try:
        return await get_session_ttl_hours(session)
    except Exception as e:
        logger.warning("Failed to read session TTL from DB, using default 24h", error=str(e))
        return 24


def _issue_session_cookie(response: Response, http_request: Request, user: User, ttl_hours: int) -> None:
    """Set the session cookie: a JWT of the account's current session version, lasting ``ttl_hours``."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_jwt_token(user.id, ttl_hours, user.session_version),
        max_age=ttl_hours * 60 * 60,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=session_cookie_secure(http_request),
    )


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session_generator)) -> User:
    """
    Dependency to get current authenticated user.
    Raises 401 if not authenticated.
    """
    token = get_session_cookie(request)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    claims = decode_jwt_token(token)

    if claims is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Fetch user from database using service
    user = await user_service.get_user_by_id(session, claims.user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is disabled")

    # A password change or reset, a deactivation or a demotion raises the account's session version:
    # a token of an earlier version is refused, whichever device holds it.
    if claims.session_version != user.session_version:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return user


@router.post("/login", response_model=AuthLoginResponse)
async def login(
    request: AuthLoginRequest,
    response: Response,
    http_request: Request,
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Authenticate user and create session.

    Accepts username or email in the `username` field.
    Returns user info and sets session cookie.
    """
    # Too many failures for this identifier or from this address: refused before the account is even looked up (F15)
    address = rate_limit_address(http_request)
    _refuse_too_many_failures(request.username, address)

    # Try to find user by username or email
    user = await user_service.get_user_by_username_or_email(session, request.username)

    # The password comes first, whatever the account: a wrong one gets the same 401 for an unknown,
    # an active or a disabled account, and an unknown one still costs a bcrypt check (dummy hash),
    # so neither the answer nor its timing tells which accounts exist.
    password_ok = await asyncio.to_thread(verify_password_or_dummy, request.password, user.hashed_password if user else None)
    if not password_ok or user is None:
        login_throttle.record_failure(request.username, address)
        # Never what was typed: the field takes an email too, and no address goes in the log (workstream E's rule).
        if user is None:
            logger.warning("Login failed: user not found")
        else:
            logger.warning("Login failed: wrong password", user_id=user.id)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Only the right password learns that the account is disabled.
    if not user.is_active:
        # An account waiting for its email verification (workstream E) is told so: the sign-in offers a new link.
        if await email_verification.awaiting_verification(session, user):
            logger.info("Login refused: email not verified", user_id=user.id)
            raise HTTPException(status_code=403, detail={"error_code": "EMAIL_NOT_VERIFIED", "message": "Verify your email address first"})
        logger.warning("Login failed: user inactive", user_id=user.id)
        raise HTTPException(status_code=403, detail={"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"})

    # Update login/donation-popup counters and decide whether to show the support popup
    # for this login (see donation_popup_service for the trigger rules).
    show_donation_popup = record_login_and_maybe_show_popup(user)
    session.add(user)
    await session.commit()

    _issue_session_cookie(response, http_request, user, await _session_ttl_hours(session))
    login_throttle.record_success(request.username)

    logger.info("User logged in", user_id=user.id, username=user.username)

    # Get user settings (may be None if never saved)
    user_settings = await settings_service.get_user_settings(user.id, session)

    return AuthLoginResponse(
        user=_auth_user(user),
        user_settings=user_settings,
        message="Login successful",
        show_donation_popup=show_donation_popup,
    )


@router.post("/logout", response_model=AuthLogoutResponse)
async def logout(
    response: Response,
    http_request: Request,
):
    """
    Logout current user and clear session cookie.
    JWT is stateless — logout simply clears the cookie client-side.
    """

    # Clear session cookie
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=session_cookie_secure(http_request),
    )

    return AuthLogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=AuthMeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    """
    return AuthMeResponse(user=_auth_user(current_user))


@router.post("/whats-new/seen", status_code=204, summary="Mark the changelog of the running release as seen")
async def mark_whats_new_seen(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session_generator)) -> Response:
    """The user closed the «What's new» modal (C-54): the running release becomes the last one it saw, so the modal does
    not come back until the next update. The server writes its own release, never one from the client. 204, idempotent.
    """
    user = await user_service.get_user_by_id(session, current_user.id)
    if user is not None:
        await whats_new_service.mark_seen(session, user)
    return Response(status_code=204)


# The answer of POST /auth/register to each refusal of the registration rule. An account that already exists keeps the
# plain 400 it always had; the others carry an error code the login page translates.
_REGISTRATION_REFUSALS: dict[str, int] = {
    "REGISTRATION_DISABLED": 403,
    "INVITE_REQUIRED": 403,
    "INVITE_INVALID": 400,
    "USER_LIMIT_REACHED": 409,
    # Email verification is required and no email with a link can go now (workstream E): nobody gets an account they
    # cannot activate.
    "EMAIL_VERIFICATION_UNAVAILABLE": 409,
    # A new username against its rules, by the service's code (A-21a, A-47): over HTTP the @, since the request schema
    # answers a length outside 3–50 with 422 first
    "USERNAME_INVALID": 400,
}


def _refuse_too_many_failures(identifier: str, address: str | None) -> None:
    """429 ``TOO_MANY_ATTEMPTS`` with ``Retry-After`` once the failed checks of a password reach their limit (F15).

    Before any password is checked, and the same whether an account matches ``identifier`` or not.
    """
    refused = login_throttle.refusal(identifier, address)
    if refused is not None:
        raise HTTPException(
            status_code=429,
            detail={"error_code": "TOO_MANY_ATTEMPTS", "message": "Too many failed attempts: try again later"},
            headers={"Retry-After": str(max(1, math.ceil(refused.retry_after)))},
        )


def _refuse_weak_password(password: str) -> None:
    """400 ``PASSWORD_TOO_WEAK`` naming the rules a new password misses (decision 37), before anything else is read."""
    failed = password_policy.failed_rules(password)
    if failed:
        raise HTTPException(status_code=400, detail={"error_code": "PASSWORD_TOO_WEAK", "message": "The password does not meet the password rules", "rules": failed})


@router.post("/register", response_model=AuthRegisterResponse, status_code=201)
async def register(request: AuthRegisterRequest, background: BackgroundTasks, http_request: Request, session: AsyncSession = Depends(get_session_generator)):
    """
    Register a new user, under the registration mode and the limit of the instance.

    The first account of an empty instance becomes an administrator, whatever the mode. Otherwise ``disabled`` refuses
    everyone, ``invite`` requires ``invite_token``, and ``open`` accepts anyone; a valid invitation sets the role.
    A refusal for the limit tells nothing about how many accounts exist: whoever asks is not signed in.

    With email verification required (workstream E), the new account waits for its link: ``verification_required`` is
    true, and ``verification_email`` says what became of its email (lot E-26). ``sending``: the email goes after the
    answer, so a failure then (the recipient mailbox's limit, the hourly budget, the SMTP server) is only logged.
    ``held``: this client address already asked for as many activation or reset emails as the instance allows in the hour
    (``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``, 20 by default; registrations, «send the link again» and «forgot
    password» share that count), or the hourly budget of the instance is spent, so the account waits without it.
    ``verification_retry_after_seconds`` then says in how many seconds both counters will admit it (rounded up, at least 1);
    its owner can ask for the link again from the sign-in page from then on. Without verification ``verification_email``
    is null. 409 ``EMAIL_VERIFICATION_UNAVAILABLE`` when the option is on and no email with a link can go out now.
    """
    _refuse_weak_password(request.password)
    try:
        user = await registration_service.register_user(
            session,
            username=request.username,
            email=request.email,
            password=request.password,
            invite_token=request.invite_token,
        )
    except RegistrationError as exc:
        if exc.code not in _REGISTRATION_REFUSALS:
            raise HTTPException(status_code=400, detail=exc.message) from None
        raise HTTPException(status_code=_REGISTRATION_REFUSALS[exc.code], detail={"error_code": exc.code, "message": exc.message}) from None

    verification_required = not user.is_active
    verification_email: Literal["sending", "held"] | None = None
    verification_retry_after_seconds: int | None = None
    if verification_required:
        verdict = await email_verification.registration_email_verdict(rate_limit_address(http_request))
        if verdict.allowed:
            # The session of this request ends with it: the work opens its own, on the same database.
            background.add_task(email_verification.registration_email_work, user.id, engine=session.bind)
            verification_email = "sending"
        else:
            # The client address's counter or the instance's budget is full: the account waits without its email (workstream E).
            logger.info("Verification email held: address limit or instance budget reached", user_id=user.id, by_address=verdict.by_address, by_instance=verdict.by_instance)
            verification_email = "held"
            verification_retry_after_seconds = max(1, math.ceil(verdict.retry_after))
    outcome = {
        None: "",
        "sending": ": check your email to activate the account",
        "held": ": the activation email is held (too many registrations from this address); sign in to ask for a new link",
    }[verification_email]
    return AuthRegisterResponse(
        user=_auth_user(user),
        message="Registration successful" + outcome + (" (Admin)" if user.is_superuser else ""),
        verification_required=verification_required,
        verification_email=verification_email,
        verification_retry_after_seconds=verification_retry_after_seconds,
    )


@router.post("/tokens/inspect", response_model=TokenInspectResponse)
async def inspect_link_token(request: TokenInspectRequest, session: AsyncSession = Depends(get_session_generator)):
    """
    What a link's token is worth: an invitation, a password-reset link, or the setup link of the initial administrator.

    Public: it answers whoever holds the token, and a token of another purpose is ``unknown``. The details — when it
    expires, the role and address of an invitation, the account of a reset or setup link — come only with a valid
    token.
    """
    purpose = AccountTokenPurpose(request.purpose)
    inspection = await token_service.inspect_token(session, request.token, purpose)
    if inspection.status != token_service.TokenStatus.VALID or inspection.record is None:
        return TokenInspectResponse(status=inspection.status.value, purpose=request.purpose)
    record = inspection.record
    if purpose == AccountTokenPurpose.INVITE:
        return TokenInspectResponse(status="valid", purpose=request.purpose, expires_at=record.expires_at, grants_admin=record.grants_admin, email=record.email)
    owner = await user_service.get_user_by_id(session, record.user_id) if record.user_id is not None else None
    return TokenInspectResponse(status="valid", purpose=request.purpose, expires_at=record.expires_at, username=owner.username if owner else None)


@router.post("/password-reset", response_model=PasswordResetResponse)
async def reset_password_with_link(request: PasswordResetRequest, session: AsyncSession = Depends(get_session_generator)):
    """
    Spend a password-reset link: the new password is set and every session of the account ends.

    A link that is not valid — used, expired, revoked, unknown, or of another purpose — changes nothing.
    """
    _refuse_weak_password(request.new_password)
    user = await user_service.complete_password_reset(session, request.token, request.new_password)
    if user is None:
        raise HTTPException(status_code=400, detail={"error_code": "TOKEN_INVALID", "message": "This password-reset link is not valid"})
    return PasswordResetResponse()


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    response: Response,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Change password for the currently authenticated user.

    Requires the current password for verification. Every other session of the account ends; this one
    receives a new session cookie in the response, and carries on.
    """
    # The current password is guessed no faster here than at the sign-in: the account's username, the same limit (F15)
    address = rate_limit_address(http_request)
    _refuse_too_many_failures(current_user.username, address)
    _refuse_weak_password(request.new_password)

    # Verify current password
    if not await asyncio.to_thread(verify_password, request.current_password, current_user.hashed_password):
        login_throttle.record_failure(current_user.username, address)
        logger.warning("Password change failed: wrong current password", user_id=current_user.id)
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    login_throttle.record_success(current_user.username)

    # Check new password is different
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    # Update password, and end every session of the account: this one gets a new cookie below. The live password-reset
    # links of the account die with the old password (A-27), in the same commit; a setup link left is retired (A-32).
    current_user.hashed_password = await asyncio.to_thread(hash_password, request.new_password)
    await user_service.end_sessions(session, current_user)
    await token_service.revoke_tokens(session, user_id=current_user.id, purpose=AccountTokenPurpose.PASSWORD_RESET)
    await token_service.retire_tokens(session, user_id=current_user.id, purpose=AccountTokenPurpose.ADMIN_SETUP)
    session.add(current_user)
    await session.commit()
    _issue_session_cookie(response, http_request, current_user, await _session_ttl_hours(session))

    logger.info("Password changed, other sessions ended", user_id=current_user.id, username=current_user.username)

    return ChangePasswordResponse(message="Password changed successfully")


@router.put("/profile", response_model=UpdateProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    response: Response,
    http_request: Request,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Update profile for the currently authenticated user.

    Allows changing username and/or email.
    Validates uniqueness constraints before committing.

    Changing the email needs the current password (A6e): with a «forgot password» link, a new address is a way to take
    the account over. It is checked before anything else, so whoever lacks it cannot probe which addresses are taken.
    The change ends every other session of the account; this one receives a new session cookie and carries on. When
    email works, the address the account had before gets a notice after the answer (workstream E), which shows nothing
    of the new one (N62).
    """
    # Nothing to update
    if request.username is None and request.email is None:
        return UpdateProfileResponse(user=_auth_user(current_user), message="No changes requested")

    # The same address in another case is no change (decision P18): no password, no session ended.
    email_changes = request.email is not None and not user_service.same_email(request.email, current_user.email)
    # Read before the change: the account below is the same object, and the notice goes to this address.
    old_email = current_user.email
    if email_changes:
        if request.current_password is None:
            raise HTTPException(status_code=400, detail={"error_code": "CURRENT_PASSWORD_REQUIRED", "message": "Changing the email needs the current password"})
        # The same limit as the sign-in, under the account's username (F15)
        address = rate_limit_address(http_request)
        _refuse_too_many_failures(current_user.username, address)
        if not await asyncio.to_thread(verify_password, request.current_password, current_user.hashed_password):
            login_throttle.record_failure(current_user.username, address)
            logger.warning("Email change refused: wrong current password", user_id=current_user.id)
            raise HTTPException(status_code=400, detail={"error_code": "CURRENT_PASSWORD_INVALID", "message": "Current password is incorrect"})
        login_throttle.record_success(current_user.username)

    # Update profile
    updated_user, error = await user_service.update_profile(
        session=session,
        user_id=current_user.id,
        username=request.username,
        email=request.email,
    )

    if error:
        # A new username against its rules (A-21a) comes with its code, so the profile says it in the user's language: the
        # service's code decides, never the wording (A-47)
        if error.code == "USERNAME_INVALID":
            raise HTTPException(status_code=400, detail={"error_code": "USERNAME_INVALID", "message": str(error)})
        raise HTTPException(status_code=400, detail=str(error))

    if email_changes:
        # update_profile ended every session of the account with the change: this one gets a new cookie.
        _issue_session_cookie(response, http_request, updated_user, await _session_ttl_hours(session))
        logger.info("Email changed, other sessions ended", user_id=updated_user.id)
        # The notice to the old address (workstream E): after the answer, with a session of its own; never raises.
        background.add_task(email_flows.email_changed_work, updated_user.id, old_email, updated_user.email, engine=session.bind)

    # Never the address in the log (workstream E's rule): whether it changed is enough.
    logger.info("Profile updated", user_id=updated_user.id, username=updated_user.username, email_changed=email_changes)

    return UpdateProfileResponse(user=_auth_user(updated_user), message="Profile updated successfully")


def deletion_preview_read(preview: user_service.AccountDeletionPreview) -> AccountDeletionPreviewRead:
    """The preview as the API returns it, to the account itself or to an administrator (``api/v1/users.py``)."""
    return AccountDeletionPreviewRead(
        user_id=preview.user_id,
        username=preview.username,
        brokers_deleted=[BrokerDeletionItemRead(id=item.broker_id, name=item.name, transactions=item.transactions) for item in preview.brokers_deleted],
        brokers_left=[BrokerAccessItemRead(id=item.broker_id, name=item.name, role=item.role.value) for item in preview.brokers_left],
        transfers_unpaired=preview.transfers_unpaired,
    )


@router.get("/users/me/deletion-preview", response_model=AccountDeletionPreviewRead)
async def preview_own_account_deletion(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session_generator)) -> AccountDeletionPreviewRead:
    """What deleting your own account would take with it: the brokers that go, those you only leave, the transfers
    left unpaired. Nothing is written.
    """
    preview = await user_service.preview_user_deletion(session, current_user.id)
    if preview is None:
        raise HTTPException(status_code=401, detail="User not found")
    return deletion_preview_read(preview)


@router.get("/address-probe", response_model=AddressProbeResult)
def answer_address_probe(response: Response, nonce: str = "") -> AddressProbeResult:
    """Whether this instance issued ``nonce`` (``POST /users/address-probe``), and nothing else.

    Public and readable from any origin: an administrator's browser asks it at another address to check that this
    instance answers there. Any other nonce — forged, of another instance, expired — is ``match: false``. Sync:
    deriving the key reads the instance key file.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store"
    return AddressProbeResult(match=address_probe.verify_probe_nonce(nonce))


@router.delete("/users/me", response_model=dict)
async def delete_own_account(
    response: Response,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Delete the currently authenticated user's account.

    This is a destructive action that, broker by broker, applies the last-owner rule (the
    same as leaving a broker): a broker the user was the last owner of is deleted with its
    transactions and its BRIM report files; on the others only the user's access goes.
    Then the user and its settings. All or nothing: a technical error deletes nothing.
    Cannot be undone.

    Constraints:
    - Cannot delete if you are the last active administrator (an inactive one cannot log in): 400 ``LAST_ADMIN``,
      decided under SQLite's write lock (A-52); an account deleted meanwhile answers 404 (A-54)
    - Session is invalidated after deletion
    """
    # Decided under SQLite's write lock, from the account as it is then (A-52): of the last two active administrators
    # deleting their own accounts at once, the second sees the first gone
    if not await user_service.refreshed_under_lock(session, current_user):
        raise HTTPException(status_code=404, detail="User not found")
    # The last active administrator stays: inactive admins cannot log in to administer the instance
    if current_user.is_superuser:
        other_active_admins = await user_service.count_active_superusers(session, excluding_user_id=current_user.id)
        if other_active_admins == 0:
            await session.rollback()
            raise HTTPException(status_code=400, detail={"error_code": "LAST_ADMIN", "message": "Cannot delete account: you are the last active administrator"})

    # A failed deletion rolls the session back and expires every object in it, current_user included: read it first
    user_id, username = current_user.id, current_user.username
    try:
        # The deleted brokers' report files live on disk: removed after the commit, like DELETE /brokers
        result = await user_service.delete_account(session, current_user)
    except Exception as exc:
        logger.exception("Account deletion failed: nothing was deleted", user_id=user_id)
        raise HTTPException(status_code=500, detail="Account deletion failed: nothing was deleted") from exc

    logger.warning("User account deleted", user_id=user_id, username=username, brokers_deleted=result.deleted_broker_ids, brim_files_removed=result.files_removed)

    # Clear session cookie
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=session_cookie_secure(http_request),
    )

    return {"message": "Account deleted successfully"}


@router.post("/setup", response_model=AuthLoginResponse)
async def setup_admin(
    request: AdminSetupRequest,
    response: Response,
    http_request: Request,
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Spend the setup link of the initial administrator (F02): choose the password, activate the account, sign in.

    The password rules come first (400 ``PASSWORD_TOO_WEAK``). A link that is not a live setup link (used, expired,
    revoked, unknown, of another purpose, of an account already active, or of an account set up before through another
    of its setup links — whose setup links are then retired, A-32 and A-42) answers 400 ``TOKEN_INVALID``. On success the answer and the session cookie are the login's.
    """
    _refuse_weak_password(request.new_password)
    user = await bootstrap_admin_service.complete_admin_setup(session, request.token, request.new_password)
    if user is None:
        raise HTTPException(status_code=400, detail={"error_code": "TOKEN_INVALID", "message": "This setup link is not valid"})

    show_donation_popup = record_login_and_maybe_show_popup(user)
    session.add(user)
    await session.commit()

    _issue_session_cookie(response, http_request, user, await _session_ttl_hours(session))
    logger.info("Initial administrator signed in after the setup", user_id=user.id, username=user.username)

    user_settings = await settings_service.get_user_settings(user.id, session)
    return AuthLoginResponse(
        user=_auth_user(user),
        user_settings=user_settings,
        message="Setup complete",
        show_donation_popup=show_donation_popup,
    )
