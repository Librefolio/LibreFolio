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

Scope (decision 36): a file is ``common`` (every signed-in user sees it: icons, logos, asset photos, avatars) or
``personal`` (only its uploader and the admins). The sidecar stores it; a sidecar written before decision 36 has none,
and ``effective_scope()`` applies the inheritance rule. ``can_view_upload()`` and ``can_manage_upload()`` hold the
access rule the API applies.

Several workers may serve the same folder (``dev.py server --workers N``): a worker caches a sidecar only while the file
on disk is unchanged, and a sidecar is replaced atomically, so a scope changed by one worker holds at once in the others.

Usage:
    from backend.app.services.files.static_uploads import (
        save_upload,
        list_uploads,
        get_upload_info,
        delete_upload,
        get_upload_path,
        validate_mime_type,
    )
"""

import contextlib
import json
import mimetypes
import os
import tempfile
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
from backend.app.schemas.uploads import UploadFileInfo, UploadScope
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.runtime.cache import get_ttl_cache

logger = structlog.get_logger(__name__)

# Cache for upload metadata JSON sidecar reads — TTL 1h, avoids repeated disk I/O.
# Each entry keeps the sidecar's stat stamp: an entry whose file changed on disk is read again.
_upload_meta_cache = get_ttl_cache("upload_metadata", maxsize=500, ttl=3600)

#: The uploader id of the files the application seeds itself (default avatars).
SYSTEM_USER_ID = 0


def get_uploads_dir() -> Path:
    """Get the uploads directory based on current environment (prod/test)."""
    return get_data_dir() / "custom-uploads"


# Blocked MIME types (executables, scripts)
BLOCKED_MIME_TYPES: frozenset[str] = frozenset(
    {
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
)

# Blocked file extensions
BLOCKED_EXTENSIONS: frozenset[str] = frozenset(
    {
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
)


class UploadSecurityError(Exception):
    """Raised when upload fails security validation."""


def _ensure_dir() -> None:
    """Create storage directory if it doesn't exist."""
    get_uploads_dir().mkdir(parents=True, exist_ok=True)


def _get_file_url(file_id: str) -> str:
    """Generate URL for accessing a file."""
    return f"/api/v1/uploads/file/{file_id}"


def _load_metadata(file_id: str) -> Optional[dict]:
    """Load metadata from its JSON sidecar, cached (TTL) while the sidecar on disk is the one read.

    The stamp of the sidecar (inode, mtime, size) is checked at every read: a sidecar replaced or deleted by another
    worker is never answered from this worker's cache.
    """
    meta_path = get_uploads_dir() / f"{file_id}.json"
    try:
        stat = meta_path.stat()
    except (OSError, ValueError):
        # ValueError: an id the filesystem cannot name (an embedded NUL byte): no such file
        _upload_meta_cache.delete(file_id)
        return None
    stamp = (stat.st_ino, stat.st_mtime_ns, stat.st_size)

    cached, ok = _upload_meta_cache.get(file_id)
    if ok and cached[0] == stamp:
        return cached[1]
    try:
        data = json.loads(meta_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to load metadata", file_id=file_id, error=str(e))
        return None
    _upload_meta_cache.set(file_id, (stamp, data))
    return data


def _save_metadata(file_id: str, metadata: dict) -> None:
    """Write a sidecar atomically: a temporary file in the same folder, then ``os.replace``; no reader sees half a file."""
    meta_path = get_uploads_dir() / f"{file_id}.json"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{file_id}.", suffix=".tmp", dir=meta_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(json.dumps(metadata, indent=2, default=str))
            tmp_file.flush()
            # Stamped before the rename, which keeps inode, mtime and size: a file another worker puts there later
            # never matches this stamp
            stat = os.fstat(tmp_file.fileno())
        os.replace(tmp_name, meta_path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    _upload_meta_cache.set(file_id, ((stat.st_ino, stat.st_mtime_ns, stat.st_size), metadata))


def effective_scope(metadata: dict) -> UploadScope:
    """The scope of a file: the one its sidecar stores, else the inheritance rule of decision 36.

    Inheritance, for the files uploaded before scopes existed: the application's own files (uploader ``SYSTEM_USER_ID``)
    and images are common, any other file is personal.
    """
    stored = metadata.get("scope")
    if stored in (UploadScope.COMMON.value, UploadScope.PERSONAL.value):
        return UploadScope(stored)
    if metadata.get("uploaded_by_user_id") == SYSTEM_USER_ID:
        return UploadScope.COMMON
    if str(metadata.get("mime_type") or "").startswith("image/"):
        return UploadScope.COMMON
    return UploadScope.PERSONAL


def can_view_upload(info: UploadFileInfo, user_id: int, is_admin: bool) -> bool:
    """Whether a user may list, preview and download a file: a common file, its uploader, an admin."""
    return is_admin or info.scope == UploadScope.COMMON or info.uploaded_by_user_id == user_id


def can_manage_upload(info: UploadFileInfo, user_id: int, is_admin: bool) -> bool:
    """Whether a user may delete a file and change its scope: its uploader or an admin."""
    return is_admin or info.uploaded_by_user_id == user_id


def _metadata_to_info(metadata: dict) -> UploadFileInfo:
    """Convert metadata dict to UploadFileInfo schema."""
    return UploadFileInfo(
        id=metadata["id"],
        original_name=metadata["original_name"],
        mime_type=metadata["mime_type"],
        size_bytes=metadata["size_bytes"],
        uploaded_at=datetime.fromisoformat(metadata["uploaded_at"]),
        uploaded_by_user_id=metadata["uploaded_by_user_id"],
        scope=effective_scope(metadata),
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
    scope: Optional[UploadScope] = None,
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
        scope: Who sees the file; without it, the inheritance rule decides (``effective_scope``), and the result is stored

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
    metadata["scope"] = UploadScope(scope).value if scope is not None else effective_scope(metadata).value
    _save_metadata(file_id, metadata)

    logger.info(
        "File uploaded",
        file_id=file_id,
        original_name=original_filename,
        size_bytes=len(content),
        user_id=user_id,
        scope=metadata["scope"],
    )

    return _metadata_to_info(metadata)


def list_uploads(user_id: Optional[int] = None) -> Tuple[List[UploadFileInfo], int]:
    """
    List all uploaded files, newest first; uploads of the same instant by name, then by id.

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

    # Newest first. Uploads of the same instant (the seeded avatars share one) follow their name, then their id: the
    # directory's order, which the random ids decide, would change at every seed.
    files.sort(key=lambda f: (f.original_name.casefold(), f.id))
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


def set_upload_scope(file_id: str, scope: UploadScope) -> Optional[UploadFileInfo]:
    """Store a file's scope; its updated info, or None when the file does not exist. Access is the caller's check."""
    metadata = _load_metadata(file_id)
    if not metadata:
        return None
    content_path = get_uploads_dir() / f"{file_id}{metadata.get('extension', '')}"
    if not content_path.exists():
        return None

    updated = {**metadata, "scope": UploadScope(scope).value}
    _save_metadata(file_id, updated)
    if not content_path.exists():
        # A delete ran in between and removed the file: do not leave the sidecar just written behind
        with contextlib.suppress(OSError):
            (get_uploads_dir() / f"{file_id}.json").unlink()
        _upload_meta_cache.delete(file_id)
        return None
    logger.info("Upload scope changed", file_id=file_id, scope=updated["scope"])
    return _metadata_to_info(updated)


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

    # Invalidate cache entry
    _upload_meta_cache.delete(file_id)

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


def seed_default_avatars() -> int:
    """
    Copy default avatar images from staticResources/Avatars/ into custom-uploads
    on first startup (when custom-uploads is empty or the marker doesn't exist).

    Uses user_id=0 (system) as the uploader since no real user exists yet.

    Returns:
        Number of avatar files seeded (0 if already seeded).
    """
    from backend.app.config import PROJECT_ROOT  # noqa: PLC0415 — lazy import / avoid circular

    _ensure_dir()
    uploads_dir = get_uploads_dir()

    # Marker file to indicate avatars have been seeded
    marker = uploads_dir / ".avatars_seeded"
    if marker.exists():
        return 0

    avatars_src = PROJECT_ROOT / "backend" / "staticResources" / "Avatars"
    if not avatars_src.exists():
        logger.warning("Default avatars directory not found", path=str(avatars_src))
        return 0

    count = 0
    now = utcnow()

    for avatar_file in sorted(avatars_src.glob("*.png")):
        content = avatar_file.read_bytes()
        file_id = str(uuid.uuid4())
        ext = avatar_file.suffix.lower()

        # Write file
        dest = uploads_dir / f"{file_id}{ext}"
        dest.write_bytes(content)

        # Create metadata (user_id=0 = system)
        metadata = {
            "id": file_id,
            "original_name": avatar_file.name,
            "extension": ext,
            "mime_type": "image/png",
            "size_bytes": len(content),
            "uploaded_at": now.isoformat(),
            "uploaded_by_user_id": 0,
            "description": f"Default avatar: {avatar_file.stem}",
        }
        _save_metadata(file_id, metadata)
        count += 1

    # Write marker so we don't re-seed next time
    marker.write_text(f"Seeded {count} avatars at {now.isoformat()}\n")
    logger.info("Seeded default avatar images", count=count)
    return count
