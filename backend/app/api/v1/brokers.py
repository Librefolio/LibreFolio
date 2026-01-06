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
    )
from backend.app.schemas.brokers import (
    BRCreateItem,
    BRReadItem,
    BRSummary,
    BRUpdateItem,
    BRDeleteItem,
    BRBulkCreateResponse,
    BRBulkUpdateResponse,
    BRBulkDeleteResponse,
    )
from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMParseError
from backend.app.services.broker_service import BrokerService
from backend.app.services.provider_registry import BRIMProviderRegistry

logger = get_logger(__name__)

broker_router = APIRouter(prefix="/brokers", tags=["BR (Broker)"])

brim_router = APIRouter(prefix="/import", tags=["BR Import"])


# =============================================================================
# CREATE
# =============================================================================

@broker_router.post("", response_model=BRBulkCreateResponse)
async def create_brokers(
    items: List[BRCreateItem],
    session: AsyncSession = Depends(get_session_generator),
    ) -> BRBulkCreateResponse:
    """
    Create multiple brokers.

    If initial_balances is provided, automatically creates DEPOSIT
    transactions for each currency.

    Args:
        items: List of brokers to create

    Returns:
        BRBulkCreateResponse with results for each item
    """
    logger.info(f"Creating {len(items)} brokers")

    service = BrokerService(session)
    response = await service.create_bulk(items)

    if not response.errors:
        await session.commit()
        logger.info(f"Created {response.success_count} brokers successfully")
    else:
        await session.rollback()
        logger.warning(f"Broker creation had errors: {response.errors}")

    return response


# =============================================================================
# READ
# =============================================================================

@broker_router.get("", response_model=List[BRReadItem])
async def list_brokers(
    session: AsyncSession = Depends(get_session_generator),
    ) -> List[BRReadItem]:
    """
    List all brokers.

    Returns basic broker information without balances.
    Use GET /brokers/{id}/summary for full details.

    Returns:
        List of brokers ordered by name
    """
    service = BrokerService(session)
    return await service.get_all()


@broker_router.get("/{broker_id}", response_model=BRReadItem)
async def get_broker(
    broker_id: int,
    session: AsyncSession = Depends(get_session_generator),
    ) -> BRReadItem:
    """
    Get a single broker by ID.

    Returns basic broker information without balances.
    Use GET /brokers/{id}/summary for full details.

    Args:
        broker_id: Broker ID

    Returns:
        Broker details

    Raises:
        HTTPException 404: If broker not found
    """
    service = BrokerService(session)
    result = await service.get_by_id(broker_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Broker {broker_id} not found")

    return result


@broker_router.get("/{broker_id}/summary", response_model=BRSummary)
async def get_broker_summary(
    broker_id: int,
    session: AsyncSession = Depends(get_session_generator),
    ) -> BRSummary:
    """
    Get broker with full summary.

    Includes:
    - Basic broker info
    - Cash balances per currency
    - Asset holdings with cost basis and market value

    Args:
        broker_id: Broker ID

    Returns:
        BRSummary with full details

    Raises:
        HTTPException 404: If broker not found
    """
    service = BrokerService(session)
    result = await service.get_summary(broker_id)

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
    session: AsyncSession = Depends(get_session_generator),
    ) -> BRBulkUpdateResponse:
    """
    Update a broker.

    Only provided fields will be updated.

    If disabling overdraft/shorting flags, validates that current
    balances don't violate the new constraints.

    Args:
        broker_id: Broker ID to update
        item: Update data

    Returns:
        BRBulkUpdateResponse with result
    """
    logger.info(f"Updating broker {broker_id}")

    service = BrokerService(session)
    response = await service.update_bulk([item], [broker_id])

    if not response.errors and response.success_count > 0:
        await session.commit()
        logger.info(f"Updated broker {broker_id} successfully")
    else:
        await session.rollback()
        if response.results and not response.results[0].success:
            logger.warning(f"Broker update failed: {response.results[0].error}")

    return response


# =============================================================================
# DELETE
# =============================================================================

@broker_router.delete("", response_model=BRBulkDeleteResponse)
async def delete_brokers(
    ids: List[int] = Query(..., description="Broker IDs to delete"),
    force: bool = Query(False, description="Force delete with transactions"),
    session: AsyncSession = Depends(get_session_generator),
    ) -> BRBulkDeleteResponse:
    """
    Delete multiple brokers.

    If force=False (default), fails if broker has any transactions.
    If force=True, cascade deletes all transactions.

    Args:
        ids: List of broker IDs to delete
        force: If True, delete broker even if it has transactions

    Returns:
        BRBulkDeleteResponse with results
    """
    logger.info(f"Deleting {len(ids)} brokers (force={force})")

    items = [BRDeleteItem(id=id_, force=force) for id_ in ids]

    service = BrokerService(session)
    response = await service.delete_bulk(items)

    if not response.errors:
        await session.commit()
        logger.info(f"Deleted {response.total_deleted} brokers successfully")
    else:
        await session.rollback()
        logger.warning(f"Broker deletion had errors: {response.errors}")

    return response


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
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB"
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
    from backend.app.schemas.brim import BRIMAssetMapping
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
        # Pass asset_mappings for asset-aware duplicate detection
        duplicates = await detect_tx_duplicates(
            transactions=transactions,
            broker_id=request.broker_id,
            session=session,
            asset_mappings=asset_mappings
            )

        # Move file to parsed folder on success
        brim_provider.move_to_parsed(file_id)

        logger.info(
            "File parsed with asset mapping and duplicate detection",
            file_id=file_id,
            plugin_code=request.plugin_code,
            transaction_count=len(transactions),
            asset_mappings_count=len(asset_mappings),
            unique_tx_count=len(duplicates.tx_unique_indices),
            possible_duplicates=len(duplicates.tx_possible_duplicates),
            likely_duplicates=len(duplicates.tx_likely_duplicates)
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
        # Parse failed - move to failed folder
        brim_provider.move_to_failed(file_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except BRIMParseError as e:
        # Parse failed - move to failed folder
        brim_provider.move_to_failed(file_id, e.message)
        raise HTTPException(
            status_code=400,
            detail=f"Parse error: {e.message}"
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


# ============================================================================
# Include sub-routes in main router
# ============================================================================
broker_router.include_router(brim_router)
