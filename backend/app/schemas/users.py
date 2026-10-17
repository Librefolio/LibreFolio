"""
User schemas for search and public-facing user info.

These schemas are separate from auth.py to keep authentication-specific
schemas distinct from general user info schemas.
"""

from typing import Optional

from pydantic import EmailStr, Field, model_validator

from backend.app.db.models import OnboardingFlow
from backend.app.schemas.common import BaseListResponse, StrictModel
from backend.app.utils.datetime_utils import UTCDateTime


class UserSearchItem(StrictModel):
    """Minimal user info for search results. Does NOT expose email for privacy."""

    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    is_admin: Optional[bool] = Field(None, description="Present only when the request asks for it (admins=True) — for the update-check hint that points non-admins to an administrator")
    email: Optional[str] = Field(None, description="Admin email, present only with admins=True (the ask-admin banner links/copies it). Endpoint is auth-gated, so emails reach logged-in users only.")


class UserSearchResponse(BaseListResponse[UserSearchItem]):
    """Response for user search endpoint."""


# =============================================================================
# Administration (admin only: GET/PATCH /users, invitations, links, sessions, onboarding)
# =============================================================================


class UserUsageRead(StrictModel):
    """Places taken against the limit of the instance; administrators only."""

    used: int = Field(..., description="Active accounts plus live invitations")
    max_users: Optional[int] = Field(None, description="LIBREFOLIO_MAX_USERS; null when there is no limit")
    billing_url: Optional[str] = Field(None, description="LIBREFOLIO_BILLING_URL: where the subscription of a managed instance is managed")


class AdminUserRead(StrictModel):
    """An account as the administrator sees it."""

    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: UTCDateTime
    protected: bool = Field(..., description="Nobody may delete, deactivate or demote this account (the paying administrator of a managed instance)")
    holds_place: bool = Field(default=False, description="Inactive and waiting for its email verification with a live link: it already holds its place, so reactivating it needs none")
    pending_setup: bool = Field(
        default=False,
        description="The initial administrator of LIBREFOLIO_ADMIN_EMAIL waiting for its setup (F02): inactive, with a setup link never used; it activates through that link, never with a reactivation",
    )


class AdminUserListResponse(BaseListResponse[AdminUserRead]):
    """Every account, oldest first, with the usage of the instance."""

    usage: UserUsageRead


class AdminUserUpdateRequest(StrictModel):
    """Change whether an account is active and an administrator; an omitted field stays as it is."""

    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    cancel_setup: bool = Field(
        False,
        description="True when this deactivation is the cancellation of the setup link of the initial administrator waiting for it: refused with 409 SETUP_COMPLETED when the account no longer waits. Only with is_active false.",
    )

    @model_validator(mode="after")
    def _cancel_setup_is_a_deactivation(self) -> "AdminUserUpdateRequest":
        """``cancel_setup`` deactivates the waiting administrator: it goes only with ``is_active`` false (A-51)."""
        if self.cancel_setup and self.is_active is not False:
            raise ValueError("cancel_setup goes only with is_active false")
        return self


class InviteRead(StrictModel):
    """A live invitation."""

    id: int
    grants_admin: bool = Field(..., description="The account it creates is an administrator")
    email: Optional[str] = Field(None, description="The address the administrator wrote, if any")
    created_at: UTCDateTime
    expires_at: UTCDateTime
    created_by_user_id: Optional[int] = Field(None, description="Who created it; null for the command line or a deleted account")


class InviteListResponse(BaseListResponse[InviteRead]):
    """The live invitations, oldest first, with the usage of the instance."""

    usage: UserUsageRead


class InviteCreateRequest(StrictModel):
    """Create an invitation."""

    grants_admin: bool = Field(False, description="The account it creates is an administrator")
    email: Optional[EmailStr] = Field(None, description="Who it is for, if known: kept for reference, not enforced")


class LinkTokenResponse(StrictModel):
    """A single-use link, shown once: the token, its path and, with LIBREFOLIO_PUBLIC_URL, the full address."""

    token: str
    path: str = Field(..., description="The path of the page that takes the token, the token in the fragment")
    url: Optional[str] = Field(None, description="LIBREFOLIO_PUBLIC_URL followed by the path; null when the variable is not set")
    expires_at: UTCDateTime


class InviteCreateResponse(StrictModel):
    """The invitation created, and its link, shown once."""

    invite: InviteRead
    token: str
    path: str = Field(..., description="The path of the page that takes the token, the token in the fragment")
    url: Optional[str] = Field(None, description="LIBREFOLIO_PUBLIC_URL followed by the path; null when the variable is not set")


class BrokerDeletionItemRead(StrictModel):
    """A broker that goes with the account, with its transactions."""

    id: int
    name: str
    transactions: int


class BrokerAccessItemRead(StrictModel):
    """A broker that stays: only the account's access to it goes."""

    id: int
    name: str
    role: str = Field(..., description="The account's role on it: OWNER, EDITOR or VIEWER")


class AccountDeletionPreviewRead(StrictModel):
    """What deleting the account would take with it, before anything is deleted."""

    user_id: int
    username: str
    brokers_deleted: list[BrokerDeletionItemRead] = Field(..., description="The brokers the account is the last owner of: deleted with their transactions and report files")
    brokers_left: list[BrokerAccessItemRead] = Field(..., description="The other brokers: only the account's access goes")
    transfers_unpaired: int = Field(..., description="Transactions that stay but lose the other half of their transfer, which goes with a deleted broker")


class AddressProbeIssued(StrictModel):
    """A nonce for the address probe: send it to ``GET <address>/api/v1/auth/address-probe``."""

    nonce: str
    expires_at: UTCDateTime


class OnboardingResetRequest(StrictModel):
    """Which onboarding flow to put back to pending; all of them when omitted."""

    flow: Optional[OnboardingFlow] = None
