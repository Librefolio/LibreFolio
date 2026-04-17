"""
Authentication API Endpoints

Provides login, logout, and JWT-based session management.
"""

from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.auth import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthMeResponse,
    AuthRegisterRequest,
    AuthRegisterResponse,
    AuthUserResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
)
from backend.app.services import settings_service, user_service
from backend.app.services.auth_service import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    verify_password,
)
from backend.app.services.global_settings_service import get_session_ttl_hours

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

# Session cookie configuration
SESSION_COOKIE_NAME = "session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours in seconds
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS


def get_session_cookie(request: Request) -> str | None:
    """Extract session cookie from request."""
    return request.cookies.get(SESSION_COOKIE_NAME)


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session_generator)) -> User:
    """
    Dependency to get current authenticated user.
    Raises 401 if not authenticated.
    """
    token = get_session_cookie(request)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = decode_jwt_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Fetch user from database using service
    user = await user_service.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is disabled")

    return user


async def get_optional_user(request: Request, session: AsyncSession = Depends(get_session_generator)) -> User | None:  # pragma: no cover — unused dependency, prepared for future use
    """
    Dependency to get current user if authenticated, None otherwise.
    Does not raise exceptions.
    """
    try:
        return await get_current_user(request, session)
    except HTTPException:
        return None


@router.post("/login", response_model=AuthLoginResponse)
async def login(
    request: AuthLoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Authenticate user and create session.

    Accepts username or email in the `username` field.
    Returns user info and sets session cookie.
    """
    # Try to find user by username or email
    user = await user_service.get_user_by_username_or_email(session, request.username)

    if not user:
        logger.warning("Login failed: user not found", username=request.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        logger.warning("Login failed: user inactive", username=request.username)
        raise HTTPException(status_code=401, detail="Account is disabled")

    if not verify_password(request.password, user.hashed_password):
        logger.warning("Login failed: wrong password", username=request.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get session TTL from global settings (with fallback)
    try:
        ttl_hours = await get_session_ttl_hours(session)
    except Exception as e:
        logger.warning("Failed to read session TTL from DB, using default 24h", error=str(e))
        ttl_hours = 24

    # Create JWT token with dynamic TTL
    token = create_jwt_token(user.id, ttl_hours)

    # Set session cookie (max_age in seconds)
    cookie_max_age = ttl_hours * 60 * 60
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=cookie_max_age,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=SESSION_COOKIE_SECURE,
    )

    logger.info("User logged in", user_id=user.id, username=user.username)

    # Get user settings (may be None if never saved)
    user_settings = await settings_service.get_user_settings(user.id, session)

    return AuthLoginResponse(user=AuthUserResponse.model_validate(user), user_settings=user_settings, message="Login successful")


@router.post("/logout", response_model=AuthLogoutResponse)
async def logout(
    response: Response,
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
        secure=SESSION_COOKIE_SECURE,
    )

    return AuthLogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=AuthMeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    """
    return AuthMeResponse(user=AuthUserResponse.model_validate(current_user))


@router.post("/register", response_model=AuthRegisterResponse, status_code=201)
async def register(request: AuthRegisterRequest, session: AsyncSession = Depends(get_session_generator)):
    """
    Register a new user.

    Note: The first user registered becomes admin (is_superuser=True).
    In production, you may want to add email verification.
    """
    # Check if this is the first user - make them admin
    user_count = await user_service.count_users(session)
    is_first_user = user_count == 0

    # Create user using service
    user, error = await user_service.create_user(
        session,
        username=request.username,
        email=request.email,
        password=request.password,
        is_superuser=is_first_user,  # First user becomes admin
        is_active=True,
    )

    if not user:
        raise HTTPException(status_code=400, detail=error)

    logger.info("User registered", user_id=user.id, username=user.username, is_first_user=is_first_user)

    return AuthRegisterResponse(
        user=AuthUserResponse.model_validate(user),
        message="Registration successful" + (" (Admin)" if is_first_user else ""),
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Change password for the currently authenticated user.

    Requires the current password for verification.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        logger.warning("Password change failed: wrong current password", user_id=current_user.id)
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Check new password is different
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    # Update password
    current_user.hashed_password = hash_password(request.new_password)
    session.add(current_user)
    await session.commit()

    logger.info("Password changed", user_id=current_user.id, username=current_user.username)

    return ChangePasswordResponse(message="Password changed successfully")


@router.put("/profile", response_model=UpdateProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Update profile for the currently authenticated user.

    Allows changing username and/or email.
    Validates uniqueness constraints before committing.
    """
    # Nothing to update
    if request.username is None and request.email is None:
        return UpdateProfileResponse(user=AuthUserResponse.model_validate(current_user), message="No changes requested")

    # Update profile
    updated_user, error = await user_service.update_profile(
        session=session,
        user_id=current_user.id,
        username=request.username,
        email=request.email,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    logger.info("Profile updated", user_id=updated_user.id, username=updated_user.username, email=updated_user.email)

    return UpdateProfileResponse(user=AuthUserResponse.model_validate(updated_user), message="Profile updated successfully")


@router.delete("/users/me", response_model=dict)
async def delete_own_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Delete the currently authenticated user's account.

    This is a destructive action that:
    - Deletes all user data (brokers, transactions, settings)
    - Cannot be undone

    Constraints:
    - Cannot delete if you are the only superuser
    - Session is invalidated after deletion
    """
    # Check if this is the only superuser
    if current_user.is_superuser:
        superuser_count = await user_service.count_superusers(session)
        if superuser_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete account: you are the only administrator")

    # Delete the user (cascades to related data)
    await user_service.delete_user(session, current_user.id)

    logger.warning("User account deleted", user_id=current_user.id, username=current_user.username)

    # Clear session cookie
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=SESSION_COOKIE_SECURE,
    )

    return {"message": "Account deleted successfully"}
