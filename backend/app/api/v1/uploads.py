"""
Uploads API endpoints.

Handles file uploads, listing, retrieval, and deletion.
Also serves static assets from plugins.

Security:
- Files are validated for MIME type (prevents executable/script uploads)
- File size is checked against global settings
"""
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
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb} MB"
        )

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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Upload failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to save file")


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
    files, total = list_uploads(user_id=user_filter)

    return UploadListResponse(files=files, total=total)


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

    logger.info("File deleted via API", file_id=file_id, user_id=current_user.id)

    return UploadDeleteResponse(
        success=True,
        message="File deleted successfully",
        file_id=file_id,
    )


@router.get("/file/{file_id}")
async def serve_file(file_id: str):
    """
    Serve the actual file content.

    This endpoint does not require authentication to allow
    embedding in images/documents.

    Args:
        file_id: File UUID

    Returns:
        File content with appropriate MIME type
    """
    file_path = get_upload_path(file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    mime_type = get_upload_mime_type(file_id) or "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
    )


# =============================================================================
# PLUGIN STATIC ASSETS
# =============================================================================

@router.get("/plugin/{provider_type}/{path:path}")
async def serve_plugin_static(provider_type: str, path: str):
    """
    Serve static assets from plugin directories.

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
            detail=f"Invalid provider type. Must be one of: {list(PLUGIN_STATIC_DIRS.keys())}"
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
        raise HTTPException(status_code=400, detail="Invalid path")

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

