"""
User schemas for search and public-facing user info.

These schemas are separate from auth.py to keep authentication-specific
schemas distinct from general user info schemas.
"""

from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class UserSearchItem(BaseModel):
    """Minimal user info for search results. Does NOT expose email for privacy."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")


class UserSearchResponse(BaseModel):
    """Response for user search endpoint."""

    model_config = ConfigDict(extra="forbid")

    users: List[UserSearchItem] = Field(default_factory=list, description="Matching users")
    count: int = Field(..., description="Number of matching users")

