"""
Authentication API Endpoints

Provides login, logout, and session management.
"""
from typing import Literal
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from backend.app.db.session import get_session_generator
from backend.app.db.models import User
from backend.app.schemas.auth import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthMeResponse,
    AuthUserResponse,
    AuthRegisterRequest,
    AuthRegisterResponse,
)
from backend.app.services.auth_service import (
    verify_password,
    create_session,
    get_user_id_from_session,
    delete_session,
)
from backend.app.services import user_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Session cookie configuration
SESSION_COOKIE_NAME = "session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours in seconds
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS


def get_session_cookie(request: Request) -> str | None:
    """Extract session cookie from request."""
    return request.cookies.get(SESSION_COOKIE_NAME)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session_generator)
) -> User:
    """
    Dependency to get current authenticated user.
    Raises 401 if not authenticated.
    """
    session_id = get_session_cookie(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_user_id_from_session(session_id)

    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Fetch user from database using service
    user = await user_service.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is disabled")

    return user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_session_generator)
) -> User | None:
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
    session: AsyncSession = Depends(get_session_generator)
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

    # Create session
    session_id = create_session(user.id)

    # Set session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=SESSION_COOKIE_SECURE,
    )

    logger.info("User logged in", user_id=user.id, username=user.username)

    return AuthLoginResponse(
        user=AuthUserResponse.model_validate(user),
        message="Login successful"
    )


@router.post("/logout", response_model=AuthLogoutResponse)
async def logout(
    request: Request,
    response: Response,
):
    """
    Logout current user and destroy session.
    """
    session_id = get_session_cookie(request)

    if session_id:
        delete_session(session_id)

    # Clear session cookie
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=SESSION_COOKIE_SECURE,
    )

    return AuthLogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=AuthMeResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user info.
    """
    return AuthMeResponse(
        user=AuthUserResponse.model_validate(current_user)
    )


@router.post("/register", response_model=AuthRegisterResponse, status_code=201)
async def register(
    request: AuthRegisterRequest,
    session: AsyncSession = Depends(get_session_generator)
):
    """
    Register a new user.

    Note: In production, you may want to add email verification.
    """
    # Create user using service
    user, error = await user_service.create_user(
        session,
        username=request.username,
        email=request.email,
        password=request.password,
        is_superuser=False,
        is_active=True,
    )

    if not user:
        raise HTTPException(status_code=400, detail=error)

    logger.info("User registered", user_id=user.id, username=user.username)

    return AuthRegisterResponse(
        user=AuthUserResponse.model_validate(user),
        message="Registration successful"
    )

