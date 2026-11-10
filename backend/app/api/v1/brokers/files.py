"""Report-file routes of BRIM: upload, list, preview, delete, download and the plugin check (``/brokers/import/...``)."""

import asyncio
import mimetypes
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.file_fetch_guard import refuse_script_destination
from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.brokers.guards import get_brim_file_with_access
from backend.app.db.models import User, UserRole
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brim import (
    BRIMFileInfo,
    BRIMFileListItem,
    BRIMFileStatus,
    BRIMPluginCheck,
)
from backend.app.schemas.uploads import FilePreviewResponse
from backend.app.services.accounts.global_settings_service import get_max_upload_mb
from backend.app.services.brim import brim_provider
from backend.app.services.brim.brim_file_settings import apply_settings_staleness
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.services.files.file_preview import (
    FilePreviewLinks,
    build_image_preview_url,
    build_preview_response,
    preview_failure_detail,
)
from backend.app.services.files.inline_media import INLINE_SAFE_MEDIA_TYPES
from backend.app.services.files.static_uploads import BLOCKED_EXTENSIONS
from backend.app.services.platform.storage_limit import StorageLimitExceededError, require_room_for, storage_limit_detail

logger = get_logger(__name__)

file_router = APIRouter()


# =============================================================================
# FILE MANAGEMENT
# =============================================================================


@file_router.post("/upload", response_model=BRIMFileInfo, responses={507: {"description": "The file would take the data past the space limit (code `storage_limit_exceeded`, with `required_mb` and `disk_missing_bytes`)"}})
async def upload_file(
    file: UploadFile = File(..., description="Broker report file to upload"),
    broker_id: int = Form(..., description="Target broker ID for this report"),
    custom_filename: Optional[str] = Form(None, description="Override filename (user-renamed)"),
    batch_id: Optional[str] = Form(None, description="Upload batch (UUID): files uploaded together form a report set"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMFileInfo:
    """
    Upload a broker report file for future processing.

    The file is saved with a UUID-based name. Compatible plugins are
    auto-detected based on file extension and content.

    Requires EDITOR or OWNER access on the target broker.

    Returns file metadata including compatible plugins.
    """
    # Verify user has EDITOR+ access to the broker
    broker_service = BrokerService(session)
    role = await broker_service._check_user_access(broker_id, current_user.id, min_role=UserRole.EDITOR)

    if not current_user.is_superuser and role is None:
        raise HTTPException(status_code=403, detail="EDITOR or OWNER access required to upload files to this broker")

    if batch_id is not None:
        try:
            batch_id = str(uuid.UUID(batch_id))
        except ValueError:
            raise HTTPException(status_code=422, detail="batch_id must be a UUID") from None

    max_mb = await get_max_upload_mb(session)
    max_bytes = max_mb * 1024 * 1024

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb} MB",
        )

    # Get filename: prefer user-provided custom_filename over original file.filename
    filename = custom_filename.strip() if custom_filename and custom_filename.strip() else (file.filename or "unknown")
    # A report is never a script or a program (H-55 v2): the static uploads' blocklist, before anything is written
    for name in {filename, file.filename or ""}:
        extension = Path(name).suffix.lower()
        if extension in BLOCKED_EXTENSIONS:
            logger.warning("Broker report upload blocked by its extension", extension=extension, user_id=current_user.id, broker_id=broker_id)
            raise HTTPException(status_code=400, detail=f"File extension '{extension}' is not allowed")

    # The space limit (C8): a report that would take the data past it is refused, before anything is written
    try:
        await asyncio.to_thread(require_room_for, len(content))
    except StorageLimitExceededError as exc:
        logger.warning("Broker report upload refused: the space limit would be passed", user_id=current_user.id, broker_id=broker_id, size_bytes=len(content), limit_mb=exc.problem.limit_mb)
        raise HTTPException(status_code=status.HTTP_507_INSUFFICIENT_STORAGE, detail=storage_limit_detail(exc.problem)) from None

    # Save file with user_id and broker_id.
    # Writing the payload, sniffing the compatible plugins (which re-reads it) and writing
    # the sidecar are all blocking filesystem I/O: run them off the loop, or a handful of
    # simultaneous uploads freeze every other request in the application.
    file_info = await asyncio.to_thread(
        brim_provider.save_uploaded_file,
        content,
        filename,
        user_id=current_user.id,
        broker_id=broker_id,
        batch_id=batch_id,
    )

    logger.info(
        "File uploaded",
        file_id=file_info.file_id,
        filename=filename,
        size_bytes=len(content),
        compatible_plugins=file_info.compatible_plugins,
        user_id=current_user.id,
        broker_id=broker_id,
    )

    return file_info


@file_router.get("/files", response_model=List[BRIMFileListItem])
async def list_files(
    status: Optional[BRIMFileStatus] = Query(default=None, description="Filter by status: uploaded, imported, failed"),
    broker_ids: Optional[List[int]] = Query(default=None, description="Filter by broker IDs (repeated query params, e.g., ?broker_ids=1&broker_ids=2)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> List[BRIMFileListItem]:
    """
    List all uploaded broker report files.

    Optionally filter by status and/or broker IDs. With ``broker_ids`` the list holds only those brokers' files: the
    files with no broker (uploaded by an older version) are listed only without that filter, on the Files page (W-B32).
    Non-superusers see the files of the brokers they have a role on, and the files with no broker they uploaded
    themselves (decision 36). Each item says whether the user may delete it (``can_delete``). Results are sorted by
    upload time (newest first).
    """
    # Determine accessible broker IDs
    if current_user.is_superuser:
        # Superuser can see all - use provided filter or all
        accessible_broker_ids = broker_ids
    else:
        # Get brokers user has access to
        broker_service = BrokerService(session)
        user_broker_ids = await broker_service.get_accessible_broker_ids(current_user.id)

        if broker_ids:
            # Intersect requested with accessible
            accessible_broker_ids = [b for b in broker_ids if b in user_broker_ids]
        else:
            # Use all accessible
            accessible_broker_ids = user_broker_ids

    # Off the event loop: listing reads every sidecar and may detect old files' plugins again (item 8).
    files = await asyncio.to_thread(brim_provider.list_files, status=status, broker_ids=accessible_broker_ids)
    await apply_settings_staleness(files, current_user.id)
    if broker_ids:
        # A broker's list holds that broker's files only; list_files also keeps the ones with no broker (W-B32).
        files = [file for file in files if file.target_broker_id is not None]
    if current_user.is_superuser:
        return [BRIMFileListItem(**file.model_dump(), can_delete=True) for file in files]

    # A file with no broker, uploaded by an older version, is its uploader's only (decision 36).
    files = [file for file in files if file.target_broker_id is not None or file.uploaded_by_user_id == current_user.id]
    editable = set(await broker_service.get_accessible_broker_ids(current_user.id, min_role=UserRole.EDITOR))
    return [BRIMFileListItem(**file.model_dump(), can_delete=file.target_broker_id in editable if file.target_broker_id is not None else True) for file in files]


@file_router.get("/files/{file_id}/preview", response_model=FilePreviewResponse)
async def get_brim_file_preview(
    file_id: str,
    sheet_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> FilePreviewResponse:
    """Get structured preview data for a BRIM file."""
    file_info = await get_brim_file_with_access(file_id, current_user, session)

    file_path = await asyncio.to_thread(brim_provider.get_file_path, file_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File content not found")

    source_url = f"/api/v1/brokers/import/files/{file_id}/download?download=false"
    links = FilePreviewLinks(
        source_url=source_url,
        download_url=f"/api/v1/brokers/import/files/{file_id}/download",
        preview_url=build_image_preview_url(source_url),
    )

    try:
        return await asyncio.to_thread(
            build_preview_response,
            file_path,
            file_info.filename,
            None,
            file_info.size_bytes,
            links,
            sheet_name=sheet_name,
        )
    except ValueError as e:  # UnsupportedPreviewError and UnreadablePreviewError are ValueErrors: coded by preview_failure_detail
        raise HTTPException(status_code=400, detail=preview_failure_detail(e)) from e
    except Exception as e:
        logger.exception("Failed to build BRIM file preview", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to build file preview") from e


@file_router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> dict:
    """
    Delete a file and its metadata.

    Requires EDITOR or OWNER access on the file's broker; a file with no broker only its uploader or the
    administrator may delete (decision 36).
    """
    await get_brim_file_with_access(
        file_id,
        current_user,
        session,
        min_role=UserRole.EDITOR,
        denied_detail="EDITOR or OWNER access required to delete files",
    )
    # Off the event loop: the delete holds the broker's metadata lock, which a combine may be holding.
    deleted = await asyncio.to_thread(brim_provider.delete_file, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    logger.info("File deleted", file_id=file_id, user_id=current_user.id)
    return {"success": True, "file_id": file_id}


@file_router.get("/files/{file_id}/download", dependencies=[Depends(refuse_script_destination)])
async def download_file(
    file_id: str,
    download: bool = True,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Download a file by its ID.

    Returns the file content with appropriate headers for download.
    Any user with access to the broker can download files (VIEWER+); a file with no broker only its uploader and the
    administrator (decision 36).
    """
    file_info = await get_brim_file_with_access(file_id, current_user, session)

    file_path = await asyncio.to_thread(brim_provider.get_file_path, file_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File content not found")

    guessed = mimetypes.guess_type(file_info.filename)[0] or "application/octet-stream"

    # Shown in the browser only when the type cannot carry active content; anything else is a download, and a download
    # is application/octet-stream whatever its name, so no file of a report is ever served as a script (H-55 v2)
    inline = not download and guessed in INLINE_SAFE_MEDIA_TYPES
    media_type = guessed if inline else "application/octet-stream"

    return FileResponse(
        path=file_path,
        filename=file_info.filename,
        media_type=media_type,
        content_disposition_type="inline" if inline else "attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@file_router.get("/files/{file_id}/plugin-check", response_model=BRIMPluginCheck)
async def check_file_plugin(
    file_id: str,
    plugin_code: str = Query(..., min_length=1, description="Plugin to ask, e.g. the broker's default import plugin"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMPluginCheck:
    """
    Ask one plugin whether it reads an uploaded file and, if not, why.

    The import wizard calls it right after an upload, for the broker's default plugin: a
    refusal comes with the plugin's English reason and, when the plugin gives one, a stable
    code the frontend translates. Nothing is parsed and the file does not change status.

    Any user with access to the file's broker can ask (VIEWER+). 404 for an unknown file
    or plugin.
    """
    await get_brim_file_with_access(file_id, current_user, session)
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_code}' not found")
    # Off the event loop: the plugin reads the file.
    check = await asyncio.to_thread(brim_provider.check_file_with_plugin, file_id, plugin)
    if check is None:
        raise HTTPException(status_code=404, detail="File content not found")
    return check
