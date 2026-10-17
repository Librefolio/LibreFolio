"""
Uploads API endpoints.

Handles file uploads, listing, retrieval, and deletion.
Also serves static assets from plugins.

Security:
- Files are validated for MIME type (prevents executable/script uploads)
- File size is checked against global settings
- Scope (decision 36): a common file is seen by every signed-in user, a personal one only by its uploader and the
  admins. A personal file of someone else answers 404, the same answer as a file that does not exist; deleting a file
  and changing its scope belong to its uploader and the admins (403 for a common file of someone else).
- Thumbnails are ``Cache-Control: private``: they are signed-in content, never for a shared cache.
"""

import asyncio
import time
from pathlib import Path
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
    FilePreviewResponse,
    UploadDeleteResponse,
    UploadFileInfo,
    UploadListResponse,
    UploadResponse,
    UploadScope,
    UploadUpdateRequest,
)
from backend.app.services.accounts.global_settings_service import get_max_upload_mb
from backend.app.services.files.file_preview import (
    FilePreviewLinks,
    UnsupportedPreviewError,
    build_image_preview_url,
    build_preview_response,
)
from backend.app.services.files.static_uploads import (
    UploadSecurityError,
    can_manage_upload,
    can_view_upload,
    delete_upload,
    get_upload_info,
    get_upload_path,
    list_uploads,
    save_upload,
    set_upload_scope,
)
from backend.app.utils.runtime.paths import confined_path

logger = structlog.get_logger(__name__)

#: The answer to a file that does not exist, and to a personal file of someone else: the two cannot be told apart.
FILE_NOT_FOUND = "File not found"

#: Thumbnails are signed-in content: the browser may keep them, a shared cache must not.
THUMBNAIL_CACHE_CONTROL = {"Cache-Control": "private, max-age=3600"}

# OpenAPI documentation for endpoints that stream raw file bytes (no JSON body).
BINARY_FILE_RESPONSE: dict = {
    200: {
        "description": "Raw file content",
        "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
    }
}


class PreviewCache:
    """
    In-memory cache for image preview thumbnails.

    Size-limited (default 50MB, configurable via PREVIEW_CACHE_MAX_MB in .env).
    Eviction is TTL-based (1 hour) plus oldest-write eviction when over the size
    limit — reads do NOT refresh timestamps, so this is not a strict LRU.

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
            from backend.app.config import get_settings  # noqa: PLC0415 — lazy import / avoid circular

            self.max_bytes = get_settings().PREVIEW_CACHE_MAX_MB * 1024 * 1024
        except Exception as exc:
            # Non-critical: keep the default cache limit if settings cannot load.
            logger.debug("Failed to load preview cache size setting; keeping default", error=str(exc))
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


def _for_user(info: UploadFileInfo, user: User) -> UploadFileInfo:
    """``info`` as ``user`` gets it: ``can_delete`` set for that user."""
    return info.model_copy(update={"can_delete": can_manage_upload(info, user.id, user.is_superuser)})


async def _visible_upload(file_id: str, user: User) -> UploadFileInfo:
    """The info of a file ``user`` may see; 404 otherwise, the same answer as a file that does not exist."""
    info = await asyncio.to_thread(get_upload_info, file_id)
    if info is None or not can_view_upload(info, user.id, user.is_superuser):
        raise HTTPException(status_code=404, detail=FILE_NOT_FOUND)
    return info


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(default=None),
    scope: Optional[UploadScope] = Form(default=None),
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
        scope: common (the image pickers) or personal (the Files page); without it, images are common and the rest
            personal

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

    # Save file (includes security validation), off the event loop: it writes the file and its sidecar
    try:
        file_info = await asyncio.to_thread(
            save_upload,
            content=content,
            original_filename=file.filename or "unnamed",
            user_id=current_user.id,
            description=description,
            mime_type=file.content_type,
            scope=scope,
        )

        logger.info(
            "File uploaded via API",
            file_id=file_info.id,
            user_id=current_user.id,
            size_bytes=file_info.size_bytes,
            scope=file_info.scope.value,
        )

        return UploadResponse(file=_for_user(file_info, current_user))

    except UploadSecurityError as e:
        logger.warning(
            "Upload blocked by security",
            error=str(e),
            filename=file.filename,
            user_id=current_user.id,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Upload failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to save file") from e


@router.get("", response_model=UploadListResponse)
async def list_files(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    my_files_only: bool = False,
):
    """
    List the uploaded files the user may see: every common file and the user's own personal ones (an admin sees all).

    Args:
        my_files_only: If True, only show files uploaded by current user

    Returns:
        List of files with metadata
    """
    user_filter = current_user.id if my_files_only else None
    files, _ = await asyncio.to_thread(list_uploads, user_id=user_filter)
    visible = [_for_user(info, current_user) for info in files if can_view_upload(info, current_user.id, current_user.is_superuser)]

    return UploadListResponse(items=visible)


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
    return _for_user(await _visible_upload(file_id, current_user), current_user)


@router.get("/{file_id}/preview", response_model=FilePreviewResponse)
async def get_upload_file_preview(
    file_id: str,
    sheet_name: Optional[str] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> FilePreviewResponse:
    """Get structured preview data for an uploaded file."""
    info = await _visible_upload(file_id, current_user)

    file_path = await asyncio.to_thread(get_upload_path, file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File content not found")

    mime_type = info.mime_type
    source_url = f"/api/v1/uploads/file/{file_id}"
    links = FilePreviewLinks(
        source_url=source_url,
        download_url=f"{source_url}?download=true",
        preview_url=build_image_preview_url(source_url),
    )

    try:
        return await asyncio.to_thread(
            build_preview_response,
            file_path,
            info.original_name,
            mime_type,
            info.size_bytes,
            links,
            sheet_name=sheet_name,
        )
    except UnsupportedPreviewError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to build upload preview", error=str(e), file_id=file_id)
        raise HTTPException(status_code=500, detail="Failed to build file preview") from e


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
    info = await _visible_upload(file_id, current_user)

    # Check ownership (superusers can delete any file)
    if not can_manage_upload(info, current_user.id, current_user.is_superuser):
        raise HTTPException(status_code=403, detail="Cannot delete files uploaded by other users")

    success = await asyncio.to_thread(delete_upload, file_id)
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


@router.patch("/{file_id}", response_model=UploadFileInfo)
async def update_file(
    file_id: str,
    body: UploadUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Change the scope of an uploaded file: common (every signed-in user) or personal (its uploader and the admins).

    Only its uploader and the admins may change it: 403 for a common file of someone else, 404 for a personal one.
    """
    info = await _visible_upload(file_id, current_user)
    if not can_manage_upload(info, current_user.id, current_user.is_superuser):
        raise HTTPException(status_code=403, detail="Cannot change files uploaded by other users")

    updated = await asyncio.to_thread(set_upload_scope, file_id, body.scope)
    if updated is None:
        raise HTTPException(status_code=404, detail=FILE_NOT_FOUND)

    logger.info("File scope changed via API", file_id=file_id, user_id=current_user.id, scope=updated.scope.value)
    return _for_user(updated, current_user)


def _resize_image(file_path: Path, max_width: int, max_height: int) -> bytes | None:
    """Sync Pillow resize (CPU+IO bound) — call via ``asyncio.to_thread``.

    Returns the resized image bytes, or ``None`` when the source is already
    smaller than requested (the caller then serves the file directly).
    """
    import io  # noqa: PLC0415 — local to keep the module import light

    from PIL import Image  # noqa: PLC0415 — lazy import / avoid circular

    img = Image.open(file_path)
    orig_width, orig_height = img.size
    ratio = min(max_width / orig_width, max_height / orig_height)
    if ratio >= 1:
        return None

    new_width = int(orig_width * ratio)
    new_height = int(orig_height * ratio)
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img_format = img.format or "PNG"
    img.save(output, format=img_format, quality=85, optimize=True)
    return output.getvalue()


@router.get("/file/{file_id}", response_class=FileResponse, responses=BINARY_FILE_RESPONSE)
async def serve_file(  # noqa: C901 — flat preview-mode dispatch with early returns
    file_id: str,
    download: bool = False,
    offset: Optional[int] = None,
    window: Optional[int] = None,
    img_preview: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Serve the actual file content.

    Requires authentication via session cookie.
    Browser <img> tags automatically include cookies,
    so embedded images work seamlessly. A personal file of someone else answers 404, before any cache is read.

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
    info = await _visible_upload(file_id, current_user)
    file_path = await asyncio.to_thread(get_upload_path, file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail=FILE_NOT_FOUND)

    mime_type = info.mime_type or "application/octet-stream"

    # Text preview mode
    if offset is not None or window is not None:
        if not mime_type.startswith("text/"):
            raise HTTPException(status_code=400, detail=f"Text preview not supported for {mime_type}. Only text/* files supported.")

        # Read text file window
        def _read_text_preview() -> str:
            with open(file_path, encoding="utf-8") as f:
                if offset:
                    f.seek(offset)
                return f.read(window) if window else f.read()

        try:
            content = await asyncio.to_thread(_read_text_preview)

            from fastapi.responses import PlainTextResponse  # noqa: PLC0415 — lazy import / avoid circular

            # Always plain text, whatever the stored type: an uploaded document is shown, never run.
            return PlainTextResponse(content=content, headers={"X-Content-Type-Options": "nosniff"})
        except Exception as e:
            logger.exception("Failed to read text preview", error=str(e), file_id=file_id)
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
            import io  # noqa: PLC0415 — lazy import / avoid circular

            from fastapi.responses import StreamingResponse  # noqa: PLC0415 — avoid circular import

            return StreamingResponse(io.BytesIO(image_bytes), media_type=cached_mime, headers=THUMBNAIL_CACHE_CONTROL)

        # Generate resized image OFF the event loop (Pillow is sync CPU+IO —
        # a big upload would otherwise stall every concurrent request).
        try:
            image_bytes = await asyncio.to_thread(_resize_image, file_path, max_width, max_height)

            if image_bytes is None:
                # Requested size >= original — serve file directly, no processing needed
                return FileResponse(path=file_path, media_type=mime_type, headers=THUMBNAIL_CACHE_CONTROL)

            # Store in cache
            preview_cache.put(file_id, size_key, image_bytes, mime_type)

            import io  # noqa: PLC0415 — lazy import / avoid circular

            from fastapi.responses import StreamingResponse  # noqa: PLC0415 — lazy import / avoid circular

            return StreamingResponse(io.BytesIO(image_bytes), media_type=mime_type, headers=THUMBNAIL_CACHE_CONTROL)

        except Exception as e:
            logger.exception("Failed to generate image preview", error=str(e), file_id=file_id)
            raise HTTPException(status_code=500, detail="Failed to generate image preview") from e

    # Normal file serving (no preview)
    # Get original filename for downloads
    filename = info.original_name if download else None

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename or file_path.name,
    )


# =============================================================================
# PLUGIN STATIC ASSETS
# =============================================================================


@router.get("/plugin/{provider_type}/{path:path}", response_class=FileResponse, responses=BINARY_FILE_RESPONSE)
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

    # Security: the requested path must stay inside the plugin's static folder
    file_path = confined_path(base_dir, path)
    if file_path is None:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Guess MIME type
    import mimetypes  # noqa: PLC0415 — lazy import / avoid circular

    mime_type, _ = mimetypes.guess_type(str(file_path))
    mime_type = mime_type or "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
    )
