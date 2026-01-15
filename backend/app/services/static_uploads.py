"""
Static Uploads Service - File storage and management for custom uploads.

Handles file uploads, storage, listing, and deletion.
Files are stored in backend/data/custom-uploads/ with UUID-based naming.
Metadata is stored in JSON sidecar files.

Storage structure:
    backend/data/custom-uploads/
    ├── {uuid}.{ext}     # Actual file
    └── {uuid}.json      # Metadata sidecar

Usage:
    from backend.app.services.static_uploads import (
        save_upload,
        list_uploads,
        get_upload_info,
        delete_upload,
        get_upload_path,
    )
"""
import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import structlog

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.uploads import UploadFileInfo
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)

# Storage directory
UPLOADS_DIR = PROJECT_ROOT / "backend" / "data" / "custom-uploads"


def _ensure_dir() -> None:
    """Create storage directory if it doesn't exist."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _get_file_url(file_id: str) -> str:
    """Generate URL for accessing a file."""
    return f"/api/v1/uploads/file/{file_id}"


def _load_metadata(file_id: str) -> Optional[dict]:
    """Load metadata from JSON sidecar."""
    meta_path = UPLOADS_DIR / f"{file_id}.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Failed to load metadata", file_id=file_id, error=str(e))
        return None


def _save_metadata(file_id: str, metadata: dict) -> None:
    """Save metadata to JSON sidecar."""
    meta_path = UPLOADS_DIR / f"{file_id}.json"
    meta_path.write_text(json.dumps(metadata, indent=2, default=str))


def _metadata_to_info(metadata: dict) -> UploadFileInfo:
    """Convert metadata dict to UploadFileInfo schema."""
    return UploadFileInfo(
        id=metadata["id"],
        original_name=metadata["original_name"],
        mime_type=metadata["mime_type"],
        size_bytes=metadata["size_bytes"],
        uploaded_at=datetime.fromisoformat(metadata["uploaded_at"]),
        uploaded_by_user_id=metadata["uploaded_by_user_id"],
        description=metadata.get("description"),
        url=_get_file_url(metadata["id"]),
    )


def save_upload(
    content: bytes,
    original_filename: str,
    user_id: int,
    description: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> UploadFileInfo:
    """
    Save an uploaded file.

    Args:
        content: File content as bytes
        original_filename: Original filename from upload
        user_id: ID of uploading user
        description: Optional description
        mime_type: Optional MIME type (auto-detected if not provided)

    Returns:
        UploadFileInfo with file details
    """
    _ensure_dir()

    # Generate UUID and determine extension
    file_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower() or ".bin"

    # Auto-detect MIME type if not provided
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(original_filename)
        mime_type = mime_type or "application/octet-stream"

    # Write file
    file_path = UPLOADS_DIR / f"{file_id}{ext}"
    file_path.write_bytes(content)

    # Create metadata
    now = utcnow()
    metadata = {
        "id": file_id,
        "original_name": original_filename,
        "extension": ext,
        "mime_type": mime_type,
        "size_bytes": len(content),
        "uploaded_at": now.isoformat(),
        "uploaded_by_user_id": user_id,
        "description": description,
    }
    _save_metadata(file_id, metadata)

    logger.info(
        "File uploaded",
        file_id=file_id,
        original_name=original_filename,
        size_bytes=len(content),
        user_id=user_id,
    )

    return _metadata_to_info(metadata)


def list_uploads(user_id: Optional[int] = None) -> Tuple[List[UploadFileInfo], int]:
    """
    List all uploaded files.

    Args:
        user_id: If provided, filter by uploading user

    Returns:
        Tuple of (list of files, total count)
    """
    _ensure_dir()

    files = []
    for meta_path in UPLOADS_DIR.glob("*.json"):
        metadata = _load_metadata(meta_path.stem)
        if metadata:
            # Filter by user if requested
            if user_id is not None and metadata.get("uploaded_by_user_id") != user_id:
                continue

            # Check that actual file exists
            ext = metadata.get("extension", "")
            file_path = UPLOADS_DIR / f"{metadata['id']}{ext}"
            if file_path.exists():
                files.append(_metadata_to_info(metadata))

    # Sort by upload date (newest first)
    files.sort(key=lambda f: f.uploaded_at, reverse=True)

    return files, len(files)


def get_upload_info(file_id: str) -> Optional[UploadFileInfo]:
    """
    Get info for a specific file.

    Args:
        file_id: File UUID

    Returns:
        UploadFileInfo or None if not found
    """
    metadata = _load_metadata(file_id)
    if not metadata:
        return None

    # Check that actual file exists
    ext = metadata.get("extension", "")
    file_path = UPLOADS_DIR / f"{file_id}{ext}"
    if not file_path.exists():
        return None

    return _metadata_to_info(metadata)


def get_upload_path(file_id: str) -> Optional[Path]:
    """
    Get filesystem path for a file.

    Args:
        file_id: File UUID

    Returns:
        Path object or None if not found
    """
    metadata = _load_metadata(file_id)
    if not metadata:
        return None

    ext = metadata.get("extension", "")
    file_path = UPLOADS_DIR / f"{file_id}{ext}"

    if not file_path.exists():
        return None

    return file_path


def get_upload_mime_type(file_id: str) -> Optional[str]:
    """
    Get MIME type for a file.

    Args:
        file_id: File UUID

    Returns:
        MIME type string or None if not found
    """
    metadata = _load_metadata(file_id)
    if not metadata:
        return None
    return metadata.get("mime_type", "application/octet-stream")


def delete_upload(file_id: str) -> bool:
    """
    Delete an uploaded file and its metadata.

    Args:
        file_id: File UUID

    Returns:
        True if deleted, False if not found
    """
    metadata = _load_metadata(file_id)
    if not metadata:
        return False

    # Delete file
    ext = metadata.get("extension", "")
    file_path = UPLOADS_DIR / f"{file_id}{ext}"
    if file_path.exists():
        file_path.unlink()

    # Delete metadata
    meta_path = UPLOADS_DIR / f"{file_id}.json"
    if meta_path.exists():
        meta_path.unlink()

    logger.info("File deleted", file_id=file_id)
    return True


def get_upload_by_user(file_id: str, user_id: int) -> Optional[UploadFileInfo]:
    """
    Get upload info only if uploaded by specific user.

    Args:
        file_id: File UUID
        user_id: User ID to check ownership

    Returns:
        UploadFileInfo or None if not found or not owned by user
    """
    info = get_upload_info(file_id)
    if info and info.uploaded_by_user_id == user_id:
        return info
    return None

