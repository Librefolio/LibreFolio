"""
Authentication Schemas

Pydantic models for auth API requests/responses.
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


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
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthLoginResponse(BaseModel):
    """Response after successful login."""
    user: AuthUserResponse
    message: str = "Login successful"


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


class AuthErrorResponse(BaseModel):
    """Error response for auth failures."""
    detail: str

