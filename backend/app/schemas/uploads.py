"""
Schemas for static file uploads and file preview.

DTOs for file upload operations.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.utils.datetime_utils import UTCDateTime


class UploadFileInfo(BaseModel):
    """Information about an uploaded file."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., description="Unique file ID (UUID)")
    original_name: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type of the file")
    size_bytes: int = Field(..., description="File size in bytes")
    uploaded_at: UTCDateTime = Field(..., description="Upload timestamp (UTC)")
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


from backend.app.schemas.common import BaseListResponse


class UploadListResponse(BaseListResponse[UploadFileInfo]):
    """Response for listing uploads."""

    pass


class UploadDeleteResponse(BaseModel):
    """Response after file deletion."""

    success: bool
    message: str
    file_id: str


class FilePreviewType(str, Enum):
    """Supported inline file preview categories."""

    IMAGE = "image"
    TEXT = "text"
    MARKDOWN = "markdown"
    TABLE = "table"
    PDF = "pdf"
    UNSUPPORTED = "unsupported"


class FilePreviewResponse(BaseModel):
    """Structured response for file preview endpoints."""

    model_config = ConfigDict(extra="forbid")

    preview_type: FilePreviewType = Field(..., description="Detected preview type")
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="Resolved MIME type")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")

    source_url: str = Field(..., description="Inline content URL suitable for embedding or opening in preview components")
    download_url: str = Field(..., description="Download URL for the original file")
    preview_url: Optional[str] = Field(default=None, description="Optimized preview URL for images when available")

    text_content: Optional[str] = Field(default=None, description="Raw text/markdown content")
    total_lines: Optional[int] = Field(default=None, ge=0, description="Total line count for text-like previews")
    detected_encoding: Optional[str] = Field(default=None, description="Detected text encoding")

    table_rows: Optional[List[List[str]]] = Field(default=None, description="Tabular preview matrix")
    total_rows: Optional[int] = Field(default=None, ge=0, description="Total row count for table previews")
    total_cols: Optional[int] = Field(default=None, ge=0, description="Total column count for table previews")
    sheet_names: List[str] = Field(default_factory=list, description="Workbook sheet names for Excel previews")
    active_sheet_name: Optional[str] = Field(default=None, description="Currently selected sheet name for Excel previews")
    csv_delimiter: Optional[str] = Field(default=None, description="Detected CSV delimiter when applicable")

    image_width: Optional[int] = Field(default=None, ge=0, description="Original image width in pixels")
    image_height: Optional[int] = Field(default=None, ge=0, description="Original image height in pixels")
