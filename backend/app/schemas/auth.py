"""
Authentication Schemas

Pydantic models for auth API requests/responses.
"""

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from backend.app.schemas.common import StrictModel
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
    password: str = Field(..., min_length=1, description="Password: the password rules apply (GET /system/instance, accounts.password_rules)")
    invite_token: Optional[str] = Field(None, min_length=1, max_length=200, description="Token of an invitation link: required when registration is by invitation, optional otherwise; it sets the role of the account")


class TokenInspectRequest(StrictModel):
    """``POST /auth/tokens/inspect``: what a link's token is worth, asked by whoever holds it."""

    token: str = Field(..., min_length=1, max_length=200, description="The token of the link")
    purpose: Literal["invite", "password_reset", "admin_setup"] = Field(..., description="What the link is for: a token of another purpose is unknown")


class PasswordResetRequest(StrictModel):
    """``POST /auth/password-reset``: spend a password-reset link."""

    token: str = Field(..., min_length=1, max_length=200, description="The token of the password-reset link")
    new_password: str = Field(..., min_length=1, description="New password: the password rules apply (GET /system/instance, accounts.password_rules)")


class ChangePasswordRequest(BaseModel):
    """Change password request (for authenticated users)."""

    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=1, description="New password: the password rules apply (GET /system/instance, accounts.password_rules)")


class UpdateProfileRequest(BaseModel):
    """Update user profile request. All fields optional."""

    username: str | None = Field(None, min_length=3, max_length=50, description="New username")
    email: EmailStr | None = Field(None, description="New email address")
    current_password: str | None = Field(None, min_length=1, description="Current password: required to change the email")


# =============================================================================
# Response Schemas
# =============================================================================


class WhatsNewRead(BaseModel):
    """What is new for the user since the release whose changelog it saw last (C-54)."""

    since: Optional[str] = Field(None, description="The release whose changelog the user saw last; null for an account from before this feature, which sees the release chapter only")
    release: str = Field(..., description="The release the instance runs")


class AuthUserResponse(BaseModel):
    """User info returned after login or from /me endpoint."""

    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: UTCDateTime
    whats_new: Optional[WhatsNewRead] = Field(None, description="The changelog chapters to show once, after an update; null when there is nothing new")

    model_config = {"from_attributes": True}


class AuthLoginResponse(BaseModel):
    """Response after successful login."""

    user: AuthUserResponse
    user_settings: Optional[UserSettingsRead] = None
    message: str = "Login successful"
    # Ephemeral signal: tells the frontend to show the "support LibreFolio" popup for
    # this login only. See backend/app/services/accounts/donation_popup_service.py for the rules.
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
    verification_required: bool = Field(default=False, description="The account waits for its email verification: signing in works once its owner confirms the address with the emailed link; whether that email leaves now is verification_email")
    verification_email: Optional[Literal["sending", "held"]] = Field(
        default=None,
        description=(
            "The state of the sending of the verification email, not an address. Only when verification_required: 'sending' when the email leaves after "
            "this answer (it can still fail later, unseen here: the recipient mailbox's limit, the instance's hourly budget, the SMTP server); 'held' when "
            "no email goes now (this client address reached its hourly limit of activation and reset emails, or the instance reached its hourly email budget): "
            "the owner signs in to ask for the link again, from verification_retry_after_seconds on. null without verification."
        ),
    )
    verification_retry_after_seconds: Optional[int] = Field(
        default=None,
        description=("Only when verification_email is 'held': in how many seconds the counters that held it (the client address's and the instance's) will admit a new email, as a whole number of seconds rounded up, at least 1. null otherwise: when the email is sending, and without verification."),
    )


class TokenInspectResponse(StrictModel):
    """The status of a link's token; the details only when it is valid, and only to whoever holds it."""

    status: Literal["valid", "expired", "consumed", "revoked", "unknown"] = Field(..., description="unknown also for a token of another purpose")
    purpose: Literal["invite", "password_reset", "admin_setup"]
    expires_at: Optional[UTCDateTime] = Field(None, description="When the link stops working (valid links only)")
    grants_admin: Optional[bool] = Field(None, description="Invitation only: the account it creates is an administrator")
    email: Optional[str] = Field(None, description="Invitation only: the address the administrator wrote, if any (a suggestion, not a constraint)")
    username: Optional[str] = Field(None, description="Password reset and administrator setup: the account the link sets the password of")


class PasswordResetResponse(StrictModel):
    """Response after a password reset through a link."""

    message: str = "Password reset successfully"


class AddressProbeResult(StrictModel):
    """``GET /auth/address-probe``: whether this instance issued the nonce, and nothing else."""

    match: bool


class PasswordRuleRead(StrictModel):
    """One password rule as the app checks it while the user types (decision 37); ``value`` only for ``min_length``."""

    code: str = Field(..., description="min_length, uppercase, lowercase, digit or special; an app that does not know a code lets the server decide")
    value: Optional[int] = Field(None, description="The rule's value, when it has one: the minimum length")


class AccountsInstanceConfig(StrictModel):
    """The accounts part of ``GET /system/instance``: public, the same for whoever asks."""

    registration_mode: Literal["open", "invite", "disabled"] = Field(..., description="Who may create an account: open (anyone), invite (an invitation link), disabled (nobody)")
    registration_locked: bool = Field(..., description="LIBREFOLIO_REGISTRATION pins the mode: the global setting cannot change it")
    first_account_open: bool = Field(False, description="No account yet: the next registration creates the first account, an administrator, whatever the mode")
    password_rules: list[PasswordRuleRead] = Field(default_factory=list, description="The rules every new password must meet, in order (decision 37)")


class ChangePasswordResponse(BaseModel):
    """Response after successful password change."""

    message: str = "Password changed successfully"


class UpdateProfileResponse(BaseModel):
    """Response after successful profile update."""

    user: AuthUserResponse
    message: str = "Profile updated successfully"


class AdminSetupRequest(StrictModel):
    """``POST /auth/setup``: the setup link of the initial administrator (F02) and the password chosen with it."""

    token: str = Field(..., min_length=1, max_length=200, description="The token of the setup link")
    new_password: str = Field(..., min_length=1, description="The administrator's password: the password rules apply (GET /system/instance, accounts.password_rules)")
