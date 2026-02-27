"""
User schemas for search and public-facing user info.

These schemas are separate from auth.py to keep authentication-specific
schemas distinct from general user info schemas.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import BaseListResponse


class UserSearchItem(BaseModel):
    """Minimal user info for search results. Does NOT expose email for privacy."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")


class UserSearchResponse(BaseListResponse[UserSearchItem]):
    """Response for user search endpoint."""
    pass

