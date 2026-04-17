"""
Uploads API endpoints.

Handles file uploads, listing, retrieval, and deletion.
Also serves static assets from plugins.

Security:
- Files are validated for MIME type (prevents executable/script uploads)
- File size is checked against global settings
"""

import time
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.config import PROJECT_ROOT
from backend.app.db import get_session_generator
from backend.app.db.models import User
from backend.app.schemas.uploads import (
    UploadDeleteResponse,
    UploadFileInfo,
    UploadListResponse,
    UploadResponse,
)
from backend.app.services.global_settings_service import get_max_upload_mb
from backend.app.services.static_uploads import (
    UploadSecurityError,
    delete_upload,
    get_upload_info,
    get_upload_mime_type,
    get_upload_path,
    list_uploads,
    save_upload,
)

logger = structlog.get_logger(__name__)


class PreviewCache:
    """
    In-memory LRU cache for image preview thumbnails.

    Size-limited (default 50MB, configurable via PREVIEW_CACHE_MAX_MB in .env).
    TTL-based eviction (1 hour).

    NOTE: This cache is per-process. With multiple uvicorn workers,
    each worker maintains its own independent cache. For a single-worker
    deployment (recommended for LibreFolio), this is optimal.
    """

    TTL = 3600  # 1 hour

    def __init__(self):
        # Key: (file_id, "WxH"), Value: (bytes, mime_type, timestamp)
        self.entries: dict[tuple[str, str], tuple[bytes, str, float]] = {}
        self.current_bytes: int = 0
        self.max_bytes: int = 50 * 1024 * 1024  # Default 50MB, loaded from settings on first write
        self.config_loaded: bool = False

    def load_config(self) -> None:
        """Load max cache size from application settings."""
        if self.config_loaded:
            return
        try:
            from backend.app.config import get_settings

            self.max_bytes = get_settings().PREVIEW_CACHE_MAX_MB * 1024 * 1024
        except Exception:
            pass  # Keep default
        self.config_loaded = True

    def get(self, file_id: str, size_key: str) -> tuple[bytes, str] | None:
        """Get cached preview if still valid."""
        key = (file_id, size_key)
        entry = self.entries.get(key)
        if entry is None:
            return None
        image_bytes, mime, ts = entry
        if time.time() - ts > self.TTL:
            self.current_bytes -= len(image_bytes)
            del self.entries[key]
            return None
        return image_bytes, mime

    def put(self, file_id: str, size_key: str, image_bytes: bytes, mime: str) -> None:
        """Store preview in cache, evicting oldest entries if over size limit."""
        self.load_config()
        entry_size = len(image_bytes)

        # Don't cache entries larger than 10% of max cache size
        if entry_size > self.max_bytes * 0.1:
            return

        # Evict expired entries first
        now = time.time()
        expired = [k for k, (_, _, ts) in self.entries.items() if now - ts > self.TTL]
        for k in expired:
            self.current_bytes -= len(self.entries[k][0])
            del self.entries[k]

        # Evict oldest until we have room
        while self.current_bytes + entry_size > self.max_bytes and self.entries:
            oldest_key = min(self.entries, key=lambda k: self.entries[k][2])
            self.current_bytes -= len(self.entries[oldest_key][0])
            del self.entries[oldest_key]

        self.entries[(file_id, size_key)] = (image_bytes, mime, now)
        self.current_bytes += entry_size

    def invalidate(self, file_id: str) -> None:
        """Remove all cached previews for a file (call on delete/update)."""
        keys_to_remove = [k for k in self.entries if k[0] == file_id]
        for k in keys_to_remove:
            self.current_bytes -= len(self.entries[k][0])
            del self.entries[k]


# Singleton cache instance
preview_cache = PreviewCache()

router = APIRouter(prefix="/uploads", tags=["Uploads"])

# Plugin static directories
PLUGIN_STATIC_DIRS = {
    "brim": PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "static",
    "fx": PROJECT_ROOT / "backend" / "app" / "services" / "fx_providers" / "static",
    "asset": PROJECT_ROOT / "backend" / "app" / "services" / "asset_source_providers" / "static",
}


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(default=None),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Upload a file.

    Files are stored with UUID-based names for security.
    Executable files and scripts are blocked.

    Args:
        file: File to upload
        description: Optional description

    Returns:
        UploadResponse with file info

    Raises:
        400: If file type is not allowed (executable/script)
        413: If file is too large
    """
    # Check file size
    max_mb = await get_max_upload_mb(session)
    max_bytes = max_mb * 1024 * 1024

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {max_mb} MB")

    # Save file (includes security validation)
    try:
        file_info = save_upload(
            content=content,
            original_filename=file.filename or "unnamed",
            user_id=current_user.id,
            description=description,
            mime_type=file.content_type,
        )

        logger.info(
            "File uploaded via API",
            file_id=file_info.id,
            user_id=current_user.id,
            size_bytes=file_info.size_bytes,
        )

        return UploadResponse(file=file_info)

    except UploadSecurityError as e:
        logger.warning(
            "Upload blocked by security",
            error=str(e),
            filename=file.filename,
            user_id=current_user.id,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Upload failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to save file") from e


@router.get("", response_model=UploadListResponse)
async def list_files(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    my_files_only: bool = False,
):
    """
    List all uploaded files.

    Args:
        my_files_only: If True, only show files uploaded by current user

    Returns:
        List of files with metadata
    """
    user_filter = current_user.id if my_files_only else None
    files, _ = list_uploads(user_id=user_filter)

    return UploadListResponse(items=files)


@router.get("/{file_id}", response_model=UploadFileInfo)
async def get_file_info(
    file_id: str,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Get metadata for a specific file.

    Args:
        file_id: File UUID

    Returns:
        File metadata
    """
    info = get_upload_info(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")
    return info


@router.delete("/{file_id}", response_model=UploadDeleteResponse)
async def delete_file(
    file_id: str,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Delete an uploaded file.

    Users can only delete their own files unless they are superuser.

    Args:
        file_id: File UUID

    Returns:
        Deletion confirmation
    """
    info = get_upload_info(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")

    # Check ownership (superusers can delete any file)
    if not current_user.is_superuser and info.uploaded_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete files uploaded by other users")

    success = delete_upload(file_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete file")

    # Invalidate any cached preview thumbnails
    preview_cache.invalidate(file_id)

    logger.info("File deleted via API", file_id=file_id, user_id=current_user.id)

    return UploadDeleteResponse(
        success=True,
        message="File deleted successfully",
        file_id=file_id,
    )


@router.get("/file/{file_id}")
async def serve_file(
    file_id: str,
    download: bool = False,
    offset: Optional[int] = None,
    window: Optional[int] = None,
    img_preview: Optional[str] = None,
    _current_user: User = Depends(get_current_user),
):
    """
    Serve the actual file content.

    Requires authentication via session cookie.
    Browser <img> tags automatically include cookies,
    so embedded images work seamlessly.

    Preview modes:
    - Text preview: ?offset=0&window=1000 (returns first 1000 chars)
    - Image preview: ?img_preview=200x200 (returns resized image, max dimension)

    Args:
        file_id: File UUID
        download: If True, force download with original filename
        offset: Start byte for text preview (text files only)
        window: Number of bytes to read for text preview (text files only)
        img_preview: Image resize format "WIDTHxHEIGHT" (images only)

    Returns:
        File content with appropriate MIME type

    Raises:
        400: If preview params used on incompatible file type
        404: If file not found
    """
    file_path = get_upload_path(file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    mime_type = get_upload_mime_type(file_id) or "application/octet-stream"

    # Text preview mode
    if offset is not None or window is not None:
        if not mime_type.startswith("text/"):
            raise HTTPException(status_code=400, detail=f"Text preview not supported for {mime_type}. Only text/* files supported.")

        # Read text file window
        try:
            with open(file_path, encoding="utf-8") as f:
                if offset:
                    f.seek(offset)
                content = f.read(window) if window else f.read()

            from fastapi.responses import PlainTextResponse

            return PlainTextResponse(content=content, media_type=mime_type)
        except Exception as e:
            logger.error("Failed to read text preview", error=str(e), file_id=file_id)
            raise HTTPException(status_code=500, detail="Failed to read file preview") from e

    # Image preview mode
    if img_preview:
        if not mime_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"Image preview not supported for {mime_type}. Only image/* files supported.")

        # Parse dimensions (format: "200x200")
        try:
            width_str, height_str = img_preview.lower().split("x")
            max_width = int(width_str)
            max_height = int(height_str)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid img_preview format. Expected: WIDTHxHEIGHT (e.g., 200x200)") from None

        # Check cache first
        size_key = f"{max_width}x{max_height}"
        cached = preview_cache.get(file_id, size_key)
        if cached:
            image_bytes, cached_mime = cached
            import io

            from fastapi.responses import StreamingResponse

            return StreamingResponse(io.BytesIO(image_bytes), media_type=cached_mime, headers={"Cache-Control": "public, max-age=3600"})

        # Generate resized image (synchronous - Pillow is fast for simple resizes)
        try:
            import io

            from PIL import Image

            img = Image.open(file_path)

            # Calculate resize dimensions (maintain aspect ratio, use most restrictive dimension)
            orig_width, orig_height = img.size
            ratio = min(max_width / orig_width, max_height / orig_height)

            if ratio >= 1:
                # Requested size >= original — serve file directly, no processing needed
                return FileResponse(path=file_path, media_type=mime_type, headers={"Cache-Control": "public, max-age=3600"})

            new_width = int(orig_width * ratio)
            new_height = int(orig_height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            img_format = img.format or "PNG"
            img.save(output, format=img_format, quality=85, optimize=True)
            image_bytes = output.getvalue()

            # Store in cache
            preview_cache.put(file_id, size_key, image_bytes, mime_type)

            from fastapi.responses import StreamingResponse

            return StreamingResponse(io.BytesIO(image_bytes), media_type=mime_type, headers={"Cache-Control": "public, max-age=3600"})

        except Exception as e:
            logger.error("Failed to generate image preview", error=str(e), file_id=file_id)
            raise HTTPException(status_code=500, detail="Failed to generate image preview") from e

    # Normal file serving (no preview)
    # Get original filename for downloads
    filename = None
    if download:
        info = get_upload_info(file_id)
        if info:
            filename = info.original_name

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename or file_path.name,
    )


# =============================================================================
# PLUGIN STATIC ASSETS
# =============================================================================


@router.get("/plugin/{provider_type}/{path:path}")
async def serve_plugin_static(
    provider_type: str,
    path: str,
    _current_user: User = Depends(get_current_user),
):
    """
    Serve static assets from plugin directories.

    Requires authentication via session cookie.

    Plugin developers can place static files (icons, images, etc.)
    in their plugin's static/ folder.

    Structure:
        brim_providers/static/{path}
        fx_providers/static/{path}
        asset_source_providers/static/{path}

    Example URLs:
        /api/v1/uploads/plugin/brim/directa/logo.png
        /api/v1/uploads/plugin/fx/ecb/icon.svg
        /api/v1/uploads/plugin/asset/yfinance/logo.png

    Args:
        provider_type: One of 'brim', 'fx', 'asset'
        path: Path to file within static folder

    Returns:
        File content
    """
    # Validate provider type
    if provider_type not in PLUGIN_STATIC_DIRS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider type. Must be one of: {list(PLUGIN_STATIC_DIRS.keys())}",
        )

    # Build path and validate
    base_dir = PLUGIN_STATIC_DIRS[provider_type]
    file_path = base_dir / path

    # Security: prevent path traversal
    try:
        file_path = file_path.resolve()
        base_resolved = base_dir.resolve()
        if not str(file_path).startswith(str(base_resolved)):
            raise HTTPException(status_code=403, detail="Access denied")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid path") from None

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Guess MIME type
    import mimetypes

    mime_type, _ = mimetypes.guess_type(str(file_path))
    mime_type = mime_type or "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
    )
