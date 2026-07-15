"""
Authentication Schemas

Pydantic models for auth API requests/responses.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from backend.app.schemas.settings import UserSettingsRead
from backend.app.utils.datetime_utils import UTCDateTime

# =============================================================================
# Request Schemas
# =============================================================================


class AuthLoginRequest(BaseModel):
    """Login request with username/email and password."""

    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="Password")


class AuthRegisterRequest(BaseModel):
    """Registration request."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")


class AuthPasswordResetRequest(BaseModel):
    """Password reset request (for terminal CLI)."""

    username: str = Field(..., description="Username to reset")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangePasswordRequest(BaseModel):
    """Change password request (for authenticated users)."""

    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")


class UpdateProfileRequest(BaseModel):
    """Update user profile request. All fields optional."""

    username: str | None = Field(None, min_length=3, max_length=50, description="New username")
    email: EmailStr | None = Field(None, description="New email address")


# =============================================================================
# Response Schemas
# =============================================================================


class AuthUserResponse(BaseModel):
    """User info returned after login or from /me endpoint."""

    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


class AuthLoginResponse(BaseModel):
    """Response after successful login."""

    user: AuthUserResponse
    user_settings: Optional[UserSettingsRead] = None
    message: str = "Login successful"
    # Ephemeral signal: tells the frontend to show the "support LibreFolio" popup for
    # this login only. See backend/app/services/donation_popup_service.py for the rules.
    show_donation_popup: bool = False


class AuthLogoutResponse(BaseModel):
    """Response after logout."""

    message: str = "Logged out successfully"


class AuthMeResponse(BaseModel):
    """Response from /me endpoint."""

    user: AuthUserResponse


class AuthRegisterResponse(BaseModel):
    """Response after successful registration."""

    user: AuthUserResponse
    message: str = "Registration successful"


class ChangePasswordResponse(BaseModel):
    """Response after successful password change."""

    message: str = "Password changed successfully"


class UpdateProfileResponse(BaseModel):
    """Response after successful profile update."""

    user: AuthUserResponse
    message: str = "Profile updated successfully"


class AuthErrorResponse(BaseModel):
    """Error response for auth failures."""

    detail: str
