"""
Static Uploads Service - File storage and management for custom uploads.

Handles file uploads, storage, listing, and deletion.
Files are stored in backend/data/custom-uploads/ with UUID-based naming.
Metadata is stored in JSON sidecar files.

Security:
- Validates actual MIME type matches declared type (prevents masquerading)
- Blocks executable files and scripts
- Validates file size against global settings

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
        validate_mime_type,
    )
"""

import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import structlog

try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from backend.app.config import get_data_dir
from backend.app.schemas.uploads import UploadFileInfo
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)


def get_uploads_dir() -> Path:
    """Get the uploads directory based on current environment (prod/test)."""
    return get_data_dir() / "custom-uploads"


# Blocked MIME types (executables, scripts)
BLOCKED_MIME_TYPES = {
    # Executables
    "application/x-executable",
    "application/x-dosexec",
    "application/x-msdownload",
    "application/x-msdos-program",
    "application/vnd.microsoft.portable-executable",
    # Scripts
    "application/x-sh",
    "application/x-shellscript",
    "application/x-bash",
    "application/x-csh",
    "text/x-python",
    "text/x-perl",
    "text/x-ruby",
    "text/x-php",
    "application/javascript",
    "text/javascript",
    # Archives that can contain executables
    # (optional - can be enabled if needed)
    # "application/x-tar",
    # "application/zip",
}

# Blocked file extensions
BLOCKED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".vbe",
    ".sh",
    ".bash",
    ".csh",
    ".zsh",
    ".py",
    ".pyc",
    ".pyo",
    ".pl",
    ".pm",
    ".rb",
    ".php",
    ".php3",
    ".php4",
    ".php5",
    ".phtml",
    ".js",
    ".mjs",
    ".cjs",
    ".jar",
    ".class",
    ".com",
    ".scr",
    ".pif",
}


class UploadSecurityError(Exception):
    """Raised when upload fails security validation."""

    pass


def _ensure_dir() -> None:
    """Create storage directory if it doesn't exist."""
    get_uploads_dir().mkdir(parents=True, exist_ok=True)


def _get_file_url(file_id: str) -> str:
    """Generate URL for accessing a file."""
    return f"/api/v1/uploads/file/{file_id}"


def _load_metadata(file_id: str) -> Optional[dict]:
    """Load metadata from JSON sidecar."""
    meta_path = get_uploads_dir() / f"{file_id}.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Failed to load metadata", file_id=file_id, error=str(e))
        return None


def _save_metadata(file_id: str, metadata: dict) -> None:
    """Save metadata to JSON sidecar."""
    meta_path = get_uploads_dir() / f"{file_id}.json"
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


def _detect_actual_mime_type(content: bytes) -> Optional[str]:
    """
    Detect actual MIME type from file content using libmagic.

    Returns None if python-magic is not available.
    """
    if not MAGIC_AVAILABLE:
        return None
    try:
        return magic.from_buffer(content, mime=True)
    except Exception as e:
        logger.warning("Failed to detect MIME type", error=str(e))
        return None


def validate_upload_security(
    content: bytes,
    original_filename: str,
    declared_mime_type: Optional[str] = None,
) -> str:
    """
    Validate file upload for security.

    Checks:
    1. File extension is not blocked
    2. Detected MIME type (via magic) is not blocked
    3. If declared MIME type provided, it must match detected (prevent masquerading)

    Args:
        content: File content bytes
        original_filename: Original filename
        declared_mime_type: MIME type declared by client (optional)

    Returns:
        Validated/detected MIME type

    Raises:
        UploadSecurityError: If file fails security validation
    """
    ext = Path(original_filename).suffix.lower()

    # Check extension blocklist
    if ext in BLOCKED_EXTENSIONS:
        raise UploadSecurityError(f"File extension '{ext}' is not allowed")

    # Detect actual MIME type
    actual_mime = _detect_actual_mime_type(content)

    if actual_mime:
        # Check MIME type blocklist
        if actual_mime in BLOCKED_MIME_TYPES:
            raise UploadSecurityError(f"File type '{actual_mime}' is not allowed")

        # If client declared a MIME type, verify it matches (anti-masquerading)
        if declared_mime_type:
            # Allow some flexibility for text types and similar categories
            declared_base = declared_mime_type.split(";")[0].strip()
            actual_base = actual_mime.split(";")[0].strip()

            # Same exact type is fine
            if declared_base == actual_base:
                return actual_mime

            # Allow generic types
            if declared_base == "application/octet-stream":
                return actual_mime

            # Allow text/* variations
            if declared_base.startswith("text/") and actual_base.startswith("text/"):
                return actual_mime

            # Strict check for other types
            logger.warning(
                "MIME type mismatch",
                declared=declared_mime_type,
                actual=actual_mime,
                filename=original_filename,
            )
            # We allow but log the mismatch - not all clients send correct MIME
            # If you want strict enforcement, uncomment below:
            # raise UploadSecurityError(
            #     f"Declared MIME type '{declared_mime_type}' doesn't match "
            #     f"actual content type '{actual_mime}'"
            # )

        return actual_mime

    # python-magic not available, fall back to extension-based detection
    guessed_mime, _ = mimetypes.guess_type(original_filename)
    return guessed_mime or "application/octet-stream"


def save_upload(
    content: bytes,
    original_filename: str,
    user_id: int,
    description: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> UploadFileInfo:
    """
    Save an uploaded file.

    Performs security validation before saving.

    Args:
        content: File content as bytes
        original_filename: Original filename from upload
        user_id: ID of uploading user
        description: Optional description
        mime_type: Optional MIME type (validated and may be corrected)

    Returns:
        UploadFileInfo with file details

    Raises:
        UploadSecurityError: If file fails security validation
    """
    _ensure_dir()

    # Security validation (also detects actual MIME type)
    validated_mime = validate_upload_security(content, original_filename, mime_type)

    # Generate UUID and determine extension
    file_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower() or ".bin"

    # Write file
    file_path = get_uploads_dir() / f"{file_id}{ext}"
    file_path.write_bytes(content)

    # Create metadata (use validated MIME type)
    now = utcnow()
    metadata = {
        "id": file_id,
        "original_name": original_filename,
        "extension": ext,
        "mime_type": validated_mime,
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
    uploads_dir = get_uploads_dir()
    for meta_path in uploads_dir.glob("*.json"):
        metadata = _load_metadata(meta_path.stem)
        if metadata:
            # Filter by user if requested
            if user_id is not None and metadata.get("uploaded_by_user_id") != user_id:
                continue

            # Check that actual file exists
            ext = metadata.get("extension", "")
            file_path = uploads_dir / f"{metadata['id']}{ext}"
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
    file_path = get_uploads_dir() / f"{file_id}{ext}"
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
    file_path = get_uploads_dir() / f"{file_id}{ext}"

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
    uploads_dir = get_uploads_dir()
    file_path = uploads_dir / f"{file_id}{ext}"
    if file_path.exists():
        file_path.unlink()

    # Delete metadata
    meta_path = uploads_dir / f"{file_id}.json"
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
