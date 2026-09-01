"""
User schemas for search and public-facing user info.

These schemas are separate from auth.py to keep authentication-specific
schemas distinct from general user info schemas.
"""

from typing import Optional

from pydantic import Field

from backend.app.schemas.common import BaseListResponse, StrictModel


class UserSearchItem(StrictModel):
    """Minimal user info for search results. Does NOT expose email for privacy."""

    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    is_admin: Optional[bool] = Field(None, description="Present only when the request asks for it (admins=True) — for the update-check hint that points non-admins to an administrator")


class UserSearchResponse(BaseListResponse[UserSearchItem]):
    """Response for user search endpoint."""
