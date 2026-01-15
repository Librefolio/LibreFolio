"""
Schemas for static file uploads.

DTOs for file upload operations.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class UploadFileInfo(BaseModel):
    """Information about an uploaded file."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., description="Unique file ID (UUID)")
    original_name: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type of the file")
    size_bytes: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(..., description="Upload timestamp (UTC)")
    uploaded_by_user_id: int = Field(..., description="ID of user who uploaded the file")

    # Optional metadata
    description: Optional[str] = Field(default=None, description="User-provided description")

    # Computed URL for access
    url: str = Field(..., description="URL to access the file")


class UploadResponse(BaseModel):
    """Response after successful upload."""
    success: bool = Field(default=True)
    file: UploadFileInfo = Field(..., description="Uploaded file info")
    message: str = Field(default="File uploaded successfully")


class UploadListResponse(BaseModel):
    """Response for listing uploads."""
    files: List[UploadFileInfo] = Field(default_factory=list)
    total: int = Field(..., description="Total number of files")


class UploadDeleteResponse(BaseModel):
    """Response after file deletion."""
    success: bool
    message: str
    file_id: str
