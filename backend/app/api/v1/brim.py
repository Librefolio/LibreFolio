"""
BRIM (Broker Report Import Manager) API endpoints.

Provides RESTful endpoints for broker report file management and import:
- POST /brim/upload: Upload a broker report file
- GET /brim/files: List uploaded files
- GET /brim/files/{file_id}: Get file details
- DELETE /brim/files/{file_id}: Delete a file
- POST /brim/files/{file_id}/parse: Parse file (preview)
- POST /brim/files/{file_id}/import: Import transactions
- GET /brim/plugins: List available import plugins
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brim import (
    BRIMFileInfo,
    BRIMFileStatus,
    BRIMPluginInfo,
    BRIMParseRequest,
    BRIMParseResponse,
    BRIMImportRequest,
)
from backend.app.schemas.transactions import TXBulkCreateResponse
from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMParseError
from backend.app.services.provider_registry import BRIMProviderRegistry
from backend.app.services.transaction_service import TransactionService

logger = get_logger(__name__)

brim_router = APIRouter(prefix="/brim", tags=["brim"])

# Maximum file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024


# =============================================================================
# FILE MANAGEMENT
# =============================================================================

@brim_router.post("/upload", response_model=BRIMFileInfo)
async def upload_file(
    file: UploadFile = File(..., description="Broker report file to upload"),
) -> BRIMFileInfo:
    """
    Upload a broker report file for future processing.

    The file is saved with a UUID-based name. Compatible plugins are
    auto-detected based on file extension and content.

    Returns file metadata including compatible plugins.
    """
    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file"
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB"
        )

    # Get original filename
    filename = file.filename or "unknown"

    # Save file
    file_info = brim_provider.save_uploaded_file(content, filename)

    logger.info(
        "File uploaded",
        file_id=file_info.file_id,
        filename=filename,
        size_bytes=len(content),
        compatible_plugins=file_info.compatible_plugins
    )

    return file_info


@brim_router.get("/files", response_model=List[BRIMFileInfo])
async def list_files(
    status: Optional[BRIMFileStatus] = Query(
        default=None,
        description="Filter by status: uploaded, imported, failed"
    ),
) -> List[BRIMFileInfo]:
    """
    List all uploaded broker report files.

    Optionally filter by status. Results are sorted by upload time (newest first).
    """
    return brim_provider.list_files(status)


@brim_router.get("/files/{file_id}", response_model=BRIMFileInfo)
async def get_file(file_id: str) -> BRIMFileInfo:
    """
    Get details for a specific file.
    """
    file_info = brim_provider.get_file_info(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    return file_info


@brim_router.delete("/files/{file_id}")
async def delete_file(file_id: str) -> dict:
    """
    Delete a file and its metadata.
    """
    deleted = brim_provider.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    logger.info("File deleted", file_id=file_id)
    return {"success": True, "file_id": file_id}


# =============================================================================
# PARSING & IMPORT
# =============================================================================

@brim_router.post("/files/{file_id}/parse", response_model=BRIMParseResponse)
async def parse_file(
    file_id: str,
    request: BRIMParseRequest,
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMParseResponse:
    """
    Parse a file and return transactions for preview.

    This is a preview operation - no data is persisted to the database.
    The user can review and modify the parsed transactions before
    sending them to the /import endpoint.

    Returns:
    - transactions: Parsed transactions (may have fake asset IDs)
    - asset_mappings: Mapping from fake IDs to candidate real assets
    - duplicates: Report of potential duplicate transactions
    - warnings: Parser warnings (skipped rows, etc.)

    Note: Asset mapping and duplicate detection are done in CORE,
    not in the plugin. Plugins only parse the file format.
    """
    from backend.app.schemas.brim import BRIMAssetMapping, BRIMDuplicateReport
    from backend.app.services.brim_provider import (
        search_asset_candidates,
        detect_tx_duplicates
    )

    try:
        # 1. Parse file using plugin (plugin only reads file format)
        transactions, warnings, extracted_assets = brim_provider.parse_file(
            file_id=file_id,
            plugin_code=request.plugin_code,
            broker_id=request.broker_id
        )

        # 2. Build asset mappings (CORE responsibility)
        # Search DB for candidates for each extracted asset
        asset_mappings = []
        for fake_id, info in extracted_assets.items():
            candidates, auto_selected = await search_asset_candidates(
                session=session,
                extracted_symbol=info.get('extracted_symbol'),
                extracted_isin=info.get('extracted_isin'),
                extracted_name=info.get('extracted_name')
            )
            asset_mappings.append(BRIMAssetMapping(
                fake_asset_id=fake_id,
                extracted_symbol=info.get('extracted_symbol'),
                extracted_isin=info.get('extracted_isin'),
                extracted_name=info.get('extracted_name'),
                candidates=candidates,
                selected_asset_id=auto_selected
            ))

        # 3. Detect duplicates (CORE responsibility)
        # Query DB for existing transactions that match
        duplicates = await detect_tx_duplicates(
            transactions=transactions,
            broker_id=request.broker_id,
            session=session
        )

        logger.info(
            "File parsed with asset mapping and duplicate detection",
            file_id=file_id,
            plugin_code=request.plugin_code,
            transaction_count=len(transactions),
            asset_mappings_count=len(asset_mappings),
            unique_tx_count=len(duplicates.tx_unique_indices),
            possible_duplicates=len(duplicates.tx_possible_duplicates),
            certain_duplicates=len(duplicates.tx_certain_duplicates)
        )

        return BRIMParseResponse(
            file_id=file_id,
            plugin_code=request.plugin_code,
            broker_id=request.broker_id,
            transactions=transactions,
            asset_mappings=asset_mappings,
            duplicates=duplicates,
            warnings=warnings
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except BRIMParseError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Parse error: {e.message}"
        )


@brim_router.post("/files/{file_id}/import", response_model=TXBulkCreateResponse)
async def import_transactions(
    file_id: str,
    request: BRIMImportRequest,
    session: AsyncSession = Depends(get_session_generator),
) -> TXBulkCreateResponse:
    """
    Import transactions from a parsed file.

    Accepts the (potentially user-modified) list of transactions.
    Uses TransactionService.create_bulk() - same as manual transaction creation.

    IMPORTANT: All fake asset IDs must be replaced with real asset IDs
    before calling this endpoint. Transactions with unresolved fake IDs
    will be rejected.

    On success, moves the file to 'imported' folder.
    On failure, moves the file to 'failed' folder with error details.
    """
    from backend.app.schemas.brim import is_fake_asset_id

    # Verify file exists
    file_info = brim_provider.get_file_info(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    if request.file_id != file_id:
        raise HTTPException(
            status_code=400,
            detail="file_id in request body must match URL parameter"
        )

    transactions = request.transactions

    # Validate: no fake asset IDs should remain
    # Frontend must replace fake IDs with real asset IDs before import
    unresolved_fake_ids = []
    for idx, tx in enumerate(transactions):
        if tx.asset_id is not None and is_fake_asset_id(tx.asset_id):
            unresolved_fake_ids.append({
                "row": idx,
                "fake_asset_id": tx.asset_id,
                "type": tx.type.value
            })

    if unresolved_fake_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Transactions contain unresolved fake asset IDs. Please map all assets before importing.",
                "unresolved": unresolved_fake_ids
            }
        )

    # Add extra tags if provided
    if request.tags:
        for tx in transactions:
            existing_tags = tx.tags or []
            tx.tags = list(set(existing_tags + request.tags))

    try:
        # Use TransactionService.create_bulk() - same as manual creation!
        result = await TransactionService.create_bulk(transactions, session)

        # If any transactions were created, move file to imported
        if result.created_count > 0:
            brim_provider.move_to_imported(file_id)
            logger.info(
                "Transactions imported successfully",
                file_id=file_id,
                created_count=result.created_count,
                failed_count=result.failed_count
            )
        elif result.failed_count > 0:
            # All failed - move to failed folder
            error_messages = [r.error for r in result.results if r.error]
            brim_provider.move_to_failed(
                file_id,
                f"All {result.failed_count} transactions failed: {'; '.join(error_messages[:3])}"
            )

        return result

    except Exception as e:
        # Move file to failed on unexpected error
        brim_provider.move_to_failed(file_id, str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(e)}"
        )


# =============================================================================
# PLUGIN INFO
# =============================================================================

@brim_router.get("/plugins", response_model=List[BRIMPluginInfo])
async def list_plugins() -> List[BRIMPluginInfo]:
    """
    List all available import plugins.

    Returns plugin metadata including code, name, description,
    and supported file extensions.
    """
    return BRIMProviderRegistry.list_plugin_info()

