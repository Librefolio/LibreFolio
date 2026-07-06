"""
Broker API endpoints for LibreFolio.

Provides RESTful endpoints for broker management:
- POST /brokers: Create brokers (with optional initial deposits)
- GET /brokers: List all brokers
- GET /brokers/{id}: Get broker details
- GET /brokers/{id}/summary: Get broker with balances and holdings
- PATCH /brokers/{id}: Update broker
- DELETE /brokers: Bulk delete brokers

BRIM (Broker Report Import Manager) API endpoints.

Provides RESTful endpoints for broker report file management and parsing:
- POST /import/upload: Upload a broker report file
- GET /import/files: List uploaded/parsed/failed files
- GET /import/files/{file_id}: Get file details
- DELETE /import/files/{file_id}: Delete a file
- POST /import/files/{file_id}/parse: Parse file (auto-moves to parsed/failed)
- GET /import/plugins: List available import plugins

**Flow:**
1. Upload file → POST /import/upload (status: UPLOADED)
2. Parse file → POST /import/files/{id}/parse (status: PARSED or FAILED)
3. Client resolves fake asset IDs to real asset IDs
4. Import transactions → POST /transactions (standard endpoint)
"""

import asyncio
import mimetypes
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User, UserRole
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brim import (
    BRIMAssetCandidate,
    BRIMAssetCandidatesRequest,
    BRIMAssetMapping,
    BRIMFileInfo,
    BRIMFileStatus,
    BRIMParseRequest,
    BRIMParseResponse,
    BRIMPluginInfo,
)
from backend.app.schemas.brokers import (
    BRAccessBulkItem,
    BRAccessBulkResponse,
    BRAccessItem,
    BRAccessListResponse,
    BRBulkCreateResponse,
    BRBulkDeleteResponse,
    BRBulkUpdateResponse,
    BRCreateItem,
    BRDeleteItem,
    BRListResponse,
    BRReadItem,
    BRSummary,
    BRUpdateItem,
)
from backend.app.schemas.uploads import FilePreviewResponse
from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMParseError, detect_tx_duplicates, search_asset_candidates
from backend.app.services.broker_service import BrokerService
from backend.app.services.file_preview import (
    FilePreviewLinks,
    UnsupportedPreviewError,
    build_image_preview_url,
    build_preview_response,
)
from backend.app.services.provider_registry import BRIMProviderRegistry

logger = get_logger(__name__)

broker_router = APIRouter(prefix="/brokers", tags=["BR (Broker)"])

brim_router = APIRouter(prefix="/import", tags=["BR Import"])


async def _get_brim_file_with_access(
    file_id: str,
    current_user: User,
    session: AsyncSession,
    *,
    min_role: Optional[UserRole] = None,
    denied_detail: str = "Access denied",
) -> BRIMFileInfo:
    """Load a BRIM file and validate broker access when needed."""
    file_info = brim_provider.get_file_info(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    if file_info.target_broker_id and not current_user.is_superuser:
        broker_service = BrokerService(session)
        role = await broker_service._check_user_access(file_info.target_broker_id, current_user.id, min_role=min_role)
        if role is None:
            raise HTTPException(status_code=403, detail=denied_detail)

    return file_info


# =============================================================================
# CREATE
# =============================================================================


@broker_router.post("", response_model=BRBulkCreateResponse)
async def create_brokers(
    items: List[BRCreateItem],
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> BRBulkCreateResponse:
    """
    Create multiple brokers.

    If initial_balances is provided, automatically creates DEPOSIT
    transactions for each currency.

    The current user becomes the OWNER of all created brokers.

    Args:
        items: List of brokers to create

    Returns:
        BRBulkCreateResponse with results for each item
    """
    # Cache user_id before session operations (avoid lazy load issues after rollback)
    user_id = current_user.id

    logger.info(f"Creating {len(items)} brokers", user_id=user_id)

    service = BrokerService(session)
    response = await service.create_bulk(items, user_id=user_id)

    if not response.errors:
        await session.commit()
        logger.info(f"Created {response.success_count} brokers successfully", user_id=user_id)
    else:
        await session.rollback()
        logger.warning(f"Broker creation had errors: {response.errors}", user_id=user_id)

    return response


# =============================================================================
# READ
# =============================================================================


@broker_router.get("", response_model=BRListResponse)
async def list_brokers(
    current_user: Annotated[User, Depends(get_current_user)],
    as_user_id: Optional[str] = Query(None, description="Superuser: impersonate user ID or 'all'"),
    include_inaccessible: bool = Query(False, description="Include existing brokers without access in minimal discovery payload"),
    session: AsyncSession = Depends(get_session_generator),
) -> BRListResponse:
    """
    List brokers accessible by the current user.

    Superusers can use as_user_id to impersonate another user or see all brokers.

    Returns basic broker information without balances.
    Use GET /brokers/{id}/summary for full details.

    Returns:
        List of brokers ordered by name
    """
    # Validate as_user_id permission
    if as_user_id is not None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can use as_user_id parameter")

    service = BrokerService(session)
    return await service.get_all(user_id=current_user.id, as_user_id=as_user_id, include_inaccessible=include_inaccessible)


@broker_router.get("/{broker_id}", response_model=BRReadItem)
async def get_broker(
    broker_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    as_user_id: Optional[str] = Query(None, description="Superuser: impersonate user ID or 'all'"),
    session: AsyncSession = Depends(get_session_generator),
) -> BRReadItem:
    """
    Get a single broker by ID.

    Superusers can use as_user_id to impersonate another user.

    Returns basic broker information without balances.
    Use GET /brokers/{id}/summary for full details.

    Args:
        broker_id: Broker ID

    Returns:
        Broker details

    Raises:
        HTTPException 404: If broker not found or not accessible
    """
    # Validate as_user_id permission
    if as_user_id is not None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can use as_user_id parameter")

    service = BrokerService(session)
    result = await service.get_by_id(broker_id, user_id=current_user.id, as_user_id=as_user_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Broker {broker_id} not found")

    return result


@broker_router.get("/{broker_id}/summary", response_model=BRSummary)
async def get_broker_summary(
    broker_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    as_user_id: Optional[str] = Query(None, description="Superuser: impersonate user ID or 'all'"),
    session: AsyncSession = Depends(get_session_generator),
) -> BRSummary:
    """
    Get broker with full summary.

    Superusers can use as_user_id to impersonate another user.

    Includes:
    - Basic broker info
    - Cash balances per currency
    - Asset holdings with cost basis and market value

    Args:
        broker_id: Broker ID

    Returns:
        BRSummary with full details

    Raises:
        HTTPException 404: If broker not found or not accessible
    """
    # Validate as_user_id permission
    if as_user_id is not None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can use as_user_id parameter")

    service = BrokerService(session)
    result = await service.get_summary(broker_id, user_id=current_user.id, as_user_id=as_user_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Broker {broker_id} not found")

    return result


# =============================================================================
# UPDATE
# =============================================================================


@broker_router.patch("/{broker_id}", response_model=BRBulkUpdateResponse)
async def update_broker(
    broker_id: int,
    item: BRUpdateItem,
    current_user: Annotated[User, Depends(get_current_user)],
    as_user_id: Optional[str] = Query(None, description="Superuser: impersonate user ID or 'all'"),
    session: AsyncSession = Depends(get_session_generator),
) -> BRBulkUpdateResponse:
    """
    Update a broker.

    Only provided fields will be updated.
    Requires at least EDITOR access (OWNER or EDITOR can modify).

    Superusers can use as_user_id to impersonate another user.

    If disabling overdraft/shorting flags, validates that current
    balances don't violate the new constraints.

    Args:
        broker_id: Broker ID to update
        item: Update data

    Returns:
        BRBulkUpdateResponse with result
    """
    # Cache user_id before session operations (avoid lazy load issues after rollback)
    user_id = current_user.id

    # Validate as_user_id permission
    if as_user_id is not None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can use as_user_id parameter")

    logger.info(f"Updating broker {broker_id}", user_id=user_id)

    service = BrokerService(session)
    response = await service.update_bulk([item], [broker_id], user_id=user_id, as_user_id=as_user_id)

    if not response.errors and response.success_count > 0:
        await session.commit()
        logger.info(f"Updated broker {broker_id} successfully", user_id=user_id)
    else:
        await session.rollback()
        if response.results and not response.results[0].success:
            logger.warning(f"Broker update failed: {response.results[0].error}", user_id=user_id)

    return response


# =============================================================================
# DELETE
# =============================================================================


@broker_router.delete("", response_model=BRBulkDeleteResponse)
async def delete_brokers(
    current_user: Annotated[User, Depends(get_current_user)],
    ids: List[int] = Query(..., description="Broker IDs to delete"),
    force: bool = Query(False, description="Force delete with transactions"),
    as_user_id: Optional[str] = Query(None, description="Superuser: impersonate user ID or 'all'"),
    session: AsyncSession = Depends(get_session_generator),
) -> BRBulkDeleteResponse:
    """
    Delete multiple brokers.

    Requires OWNER access to each broker.
    Superusers can use as_user_id to impersonate another user.

    If force=False (default), fails if broker has any transactions.
    If force=True, cascade deletes all transactions.

    Args:
        ids: List of broker IDs to delete
        force: If True, delete broker even if it has transactions

    Returns:
        BRBulkDeleteResponse with results
    """
    # Cache user_id before session operations (avoid lazy load issues after rollback)
    user_id = current_user.id

    # Validate as_user_id permission
    if as_user_id is not None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can use as_user_id parameter")

    logger.info(f"Deleting {len(ids)} brokers (force={force})", user_id=user_id)

    items = [BRDeleteItem(id=id_, force=force) for id_ in ids]

    service = BrokerService(session)
    response = await service.delete_bulk(items, user_id=user_id, as_user_id=as_user_id)

    if not response.errors:
        await session.commit()
        logger.info(f"Deleted {response.total_deleted} brokers successfully", user_id=user_id)
    else:
        await session.rollback()
        logger.warning(f"Broker deletion had errors: {response.errors}", user_id=user_id)

    return response


# =============================================================================
# BROKER ACCESS MANAGEMENT
# =============================================================================


@broker_router.get("/{broker_id}/access", response_model=BRAccessListResponse)
async def list_broker_access(
    broker_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> BRAccessListResponse:
    """
    List all users with access to a broker.

    Any user with access to the broker can view the access list.
    Superusers can view any broker's access list.
    """
    service = BrokerService(session)
    broker = await service.get_by_id(
        broker_id=broker_id,
        user_id=current_user.id,
        as_user_id="all",
    )
    if not broker:
        raise HTTPException(status_code=404, detail=f"Broker {broker_id} not found")

    accesses = await service.list_accesses(
        broker_id=broker_id,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )

    return BRAccessListResponse(
        items=[BRAccessItem(**a) for a in accesses],
    )


@broker_router.put("/{broker_id}/access", response_model=BRAccessBulkResponse)
async def bulk_update_broker_access(
    broker_id: int,
    items: List[BRAccessBulkItem],
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> BRAccessBulkResponse:
    """
    Atomically replace the access configuration for a broker.

    Sends the COMPLETE desired access list. The backend computes the diff
    (adds, updates, removes) and applies all changes in a single transaction.

    Rules:
    - Only OWNERs (or superusers) can call this endpoint.
    - At least one OWNER must remain after the operation.
    - Only OWNERs can have share_percentage > 0.
    - Sum of all share_percentage values must be ≤ 1.0 (fraction, not percent).
    - The calling user cannot remove themselves as the last OWNER.
    """
    if not items:
        raise HTTPException(status_code=422, detail="At least one access item is required")

    service = BrokerService(session)
    success, message, accesses = await service.bulk_update_access(
        broker_id=broker_id,
        desired_accesses=items,
        current_user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )

    if not success:
        if "Only OWNERs can" in message or "Access denied" in message:
            raise HTTPException(status_code=403, detail=message)
        raise HTTPException(status_code=400, detail=message)

    await session.commit()

    # Fetch fresh access list after commit
    fresh_accesses = await service.list_accesses(broker_id, current_user.id, is_superuser=True)
    access_items = [BRAccessItem(**a) for a in fresh_accesses]

    logger.info(
        f"Bulk updated access for broker {broker_id} ({len(access_items)} users)",
        user_id=current_user.id,
    )

    return BRAccessBulkResponse(
        results=access_items,
        success_count=len(access_items),
    )


# =============================================================================
# BRIM PROVIDER MANAGEMENT
# =============================================================================


# Maximum file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024


# =============================================================================
# FILE MANAGEMENT
# =============================================================================


@brim_router.post("/upload", response_model=BRIMFileInfo)
async def upload_file(
    file: UploadFile = File(..., description="Broker report file to upload"),
    broker_id: int = Form(..., description="Target broker ID for this report"),
    custom_filename: Optional[str] = Form(None, description="Override filename (user-renamed)"),
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

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Get filename: prefer user-provided custom_filename over original file.filename
    filename = custom_filename.strip() if custom_filename and custom_filename.strip() else (file.filename or "unknown")

    # Save file with user_id and broker_id
    file_info = brim_provider.save_uploaded_file(
        content,
        filename,
        user_id=current_user.id,
        broker_id=broker_id,
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


@brim_router.get("/files", response_model=List[BRIMFileInfo])
async def list_files(
    status: Optional[BRIMFileStatus] = Query(default=None, description="Filter by status: uploaded, imported, failed"),
    broker_ids: Optional[List[int]] = Query(default=None, description="Filter by broker IDs (repeated query params, e.g., ?broker_ids=1&broker_ids=2)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> List[BRIMFileInfo]:
    """
    List all uploaded broker report files.

    Optionally filter by status and/or broker IDs.
    Non-superusers can only see files for brokers they have access to.
    Results are sorted by upload time (newest first).
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

    return brim_provider.list_files(status=status, broker_ids=accessible_broker_ids)


@brim_router.get("/files/{file_id}", response_model=BRIMFileInfo)
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMFileInfo:
    """
    Get details for a specific file.

    User must have access to the file's broker.
    """
    return await _get_brim_file_with_access(file_id, current_user, session)


@brim_router.get("/files/{file_id}/preview", response_model=FilePreviewResponse)
async def get_brim_file_preview(
    file_id: str,
    sheet_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> FilePreviewResponse:
    """Get structured preview data for a BRIM file."""
    file_info = await _get_brim_file_with_access(file_id, current_user, session)

    file_path = brim_provider.get_file_path(file_id)
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
    except UnsupportedPreviewError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Failed to build BRIM file preview", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to build file preview") from e


@brim_router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> dict:
    """
    Delete a file and its metadata.

    Requires EDITOR or OWNER access on the file's broker.
    """
    await _get_brim_file_with_access(
        file_id,
        current_user,
        session,
        min_role=UserRole.EDITOR,
        denied_detail="EDITOR or OWNER access required to delete files",
    )
    deleted = brim_provider.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    logger.info("File deleted", file_id=file_id, user_id=current_user.id)
    return {"success": True, "file_id": file_id}


@brim_router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    download: bool = True,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
):
    """
    Download a file by its ID.

    Returns the file content with appropriate headers for download.
    Any user with access to the broker can download files (VIEWER+).
    """
    file_info = await _get_brim_file_with_access(file_id, current_user, session)

    file_path = brim_provider.get_file_path(file_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File content not found")

    media_type = mimetypes.guess_type(file_info.filename)[0] or "application/octet-stream"

    return FileResponse(
        path=file_path,
        filename=file_info.filename,
        media_type=media_type,
        content_disposition_type="attachment" if download else "inline",
    )


@brim_router.get("/files/{file_id}/last-parse")
async def get_last_parse_result(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> Optional[dict]:
    """
    Get the cached result from the last successful parse.

    Useful for reloading a preview without re-parsing the file.
    Returns None if no parse result is cached.
    """
    file_info = await _get_brim_file_with_access(file_id, current_user, session)
    return file_info.last_parse_result


# =============================================================================
# PARSING & IMPORT
# =============================================================================


@brim_router.post("/files/{file_id}/parse", response_model=BRIMParseResponse)
async def parse_file(
    file_id: str,
    request: BRIMParseRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMParseResponse:
    """
    Parse a file and return transactions for preview.

    This is a preview operation - no data is persisted to the database.
    The user can review and modify the parsed transactions before
    sending them to POST /transactions endpoint.

    Requires EDITOR or OWNER access on the file's broker.

    If plugin_code is 'auto' (default), the system will automatically
    detect the best plugin based on file content analysis.

    Returns:
    - transactions: Parsed transactions (may have fake asset IDs)
    - asset_mappings: Mapping from fake IDs to candidate real assets
    - duplicates: Report of potential duplicate transactions
    - warnings: Parser warnings (skipped rows, etc.)

    Note: Asset mapping and duplicate detection are done in CORE,
    not in the plugin. Plugins only parse the file format.
    """
    # Get file info and check permissions
    await _get_brim_file_with_access(
        file_id,
        current_user,
        session,
        min_role=UserRole.EDITOR,
        denied_detail="EDITOR or OWNER access required to parse files",
    )

    # Determine plugin to use
    plugin_code = request.plugin_code
    if plugin_code == "auto":
        # Auto-detect plugin based on file content
        file_path = brim_provider.get_file_path(file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")

        detected_plugin = BRIMProviderRegistry.auto_detect_plugin(file_path)
        if detected_plugin:
            plugin_code = detected_plugin
            logger.info("Auto-detected plugin for file", file_id=file_id, detected_plugin=plugin_code)
        else:
            # Fallback to generic CSV
            plugin_code = "broker_generic_csv"
            logger.info("No specific plugin detected, using generic CSV", file_id=file_id)

    try:
        # 1. Parse file using plugin (plugin only reads file format)
        parse_output = brim_provider.parse_file(file_id=file_id, plugin_code=plugin_code, broker_id=request.broker_id)
        transactions = parse_output.transactions
        warnings = parse_output.warnings
        validation_issues = parse_output.validation_issues
        field_todos = parse_output.field_todos
        extracted_assets = parse_output.extracted_assets

        # 2. Build asset mappings (CORE responsibility)
        # Search DB for candidates for each extracted asset
        asset_mappings = []
        for fake_id, info in extracted_assets.items():
            candidates, auto_selected = await search_asset_candidates(
                session=session,
                extracted_symbol=info.extracted_symbol,
                extracted_isin=info.extracted_isin,
                extracted_name=info.extracted_name,
            )
            asset_mappings.append(
                BRIMAssetMapping(
                    fake_asset_id=fake_id,
                    extracted_symbol=info.extracted_symbol,
                    extracted_isin=info.extracted_isin,
                    extracted_name=info.extracted_name,
                    candidates=candidates,
                    selected_asset_id=auto_selected,
                )
            )

        # 3. Detect duplicates (CORE responsibility)
        # Query DB for existing transactions that match
        # Pass asset_mappings for asset-aware duplicate detection
        duplicates = await detect_tx_duplicates(
            transactions=transactions,
            broker_id=request.broker_id,
            session=session,
            asset_mappings=asset_mappings,
        )

        # Move file to parsed folder on success
        brim_provider.move_to_parsed(file_id)

        # Build response
        response = BRIMParseResponse(
            file_id=file_id,
            plugin_code=plugin_code,  # Return actual plugin used (after auto-detection)
            broker_id=request.broker_id,
            transactions=transactions,
            asset_mappings=asset_mappings,
            duplicates=duplicates,
            warnings=warnings,
            validation_issues=validation_issues,
            field_todos=field_todos,
        )

        # Cache the parse result in file metadata for later retrieval.
        # The current plugin_version is resolved by save_parse_result via
        # the registry (single source of truth) and persisted alongside
        # plugin_code so BRIMFileInfo can compute parse_is_stale if the
        # plugin is bumped later.
        brim_provider.save_parse_result(
            file_id,
            response.model_dump(mode="json"),
            plugin_code=plugin_code,
        )

        logger.info(
            "File parsed with asset mapping and duplicate detection",
            file_id=file_id,
            plugin_code=plugin_code,
            transaction_count=len(transactions),
            asset_mappings_count=len(asset_mappings),
            unique_tx_count=len(duplicates.tx_unique_indices),
            possible_duplicates=len(duplicates.tx_possible_duplicates),
            likely_duplicates=len(duplicates.tx_likely_duplicates),
        )

        return response

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None

    except ValueError as e:
        # Parse failed - move to failed folder
        brim_provider.move_to_failed(file_id, str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    except BRIMParseError as e:
        # Parse failed - move to failed folder
        brim_provider.move_to_failed(file_id, e.message)
        raise HTTPException(status_code=400, detail=f"Parse error: {e.message}") from e


# =============================================================================
# PLUGIN INFO
# =============================================================================


@brim_router.get("/plugins", response_model=List[BRIMPluginInfo])
async def list_plugins(_current_user: User = Depends(get_current_user)) -> List[BRIMPluginInfo]:
    """
    List all available import plugins.

    Returns plugin metadata including code, name, description,
    and supported file extensions.
    """
    return BRIMProviderRegistry.list_plugin_info()


@brim_router.post(
    "/asset-candidates",
    response_model=List[BRIMAssetCandidate],
    summary="Compute asset candidates for extracted identifiers",
)
async def get_asset_candidates(
    request: BRIMAssetCandidatesRequest,
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> List[BRIMAssetCandidate]:
    """
    Re-run the asset candidate search for given extracted identifiers.

    Called by the frontend after the user updates an asset's identifier so the
    match confidence can be re-derived from the current database state rather
    than cached parse-time data.
    """
    candidates, _ = await search_asset_candidates(
        session=session,
        extracted_symbol=request.extracted_symbol,
        extracted_isin=request.extracted_isin,
        extracted_name=request.extracted_name,
    )
    return candidates


# ============================================================================
# Include sub-routes in main router
# ============================================================================
broker_router.include_router(brim_router)
