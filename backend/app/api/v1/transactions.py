"""
Transaction API endpoints for LibreFolio.

Provides RESTful endpoints for transaction management:
- POST /transactions: Bulk create transactions
- GET /transactions: Query transactions with filters
- GET /transactions/{id}: Get single transaction
- PATCH /transactions: Bulk update transactions
- DELETE /transactions: Bulk delete transactions
- GET /transactions/types: Get transaction type metadata
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import TransactionType
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.transactions import (
    TXCreateItem,
    TXReadItem,
    TXUpdateItem,
    TXDeleteItem,
    TXQueryParams,
    TXBulkCreateResponse,
    TXBulkUpdateResponse,
    TXBulkDeleteResponse,
    TXTypeMetadata,
    TX_TYPE_METADATA,
    )
from backend.app.services.transaction_service import TransactionService
from backend.app.utils.datetime_utils import parse_ISO_date

logger = get_logger(__name__)

tx_router = APIRouter(prefix="/transactions", tags=["TX (Transactions)"])


# =============================================================================
# CREATE
# =============================================================================

@tx_router.post("", response_model=TXBulkCreateResponse)
async def create_transactions(
    items: List[TXCreateItem],
    session: AsyncSession = Depends(get_session_generator),
    ) -> TXBulkCreateResponse:
    """
    Create multiple transactions.

    For linked transactions (TRANSFER, FX_CONVERSION), use the same
    link_uuid for both transactions in the request.

    Args:
        items: List of transactions to create

    Returns:
        TXBulkCreateResponse with results for each item
    """
    logger.info(f"Creating {len(items)} transactions")

    service = TransactionService(session)
    response = await service.create_bulk(items)

    # Commit if no validation errors
    if not response.errors:
        await session.commit()
        logger.info(f"Created {response.success_count} transactions successfully")
    else:
        await session.rollback()
        logger.warning(f"Transaction creation had errors: {response.errors}")

    return response


# =============================================================================
# READ
# =============================================================================

@tx_router.get("", response_model=List[TXReadItem])
async def query_transactions(
    broker_id: Optional[int] = Query(None, gt=0, description="Filter by broker"),
    asset_id: Optional[int] = Query(None, gt=0, description="Filter by asset"),
    types: Optional[List[TransactionType]] = Query(None, description="Filter by types"),
    date_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    currency: Optional[str] = Query(None, max_length=3, description="Filter by currency"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session_generator),
    ) -> List[TXReadItem]:
    """
    Query transactions with filters.

    All filters are optional. Results ordered by date desc, id desc.

    Args:
        broker_id: Filter by broker
        asset_id: Filter by asset
        types: Filter by transaction types
        date_start: Filter by start date (inclusive)
        date_end: Filter by end date (inclusive)
        tags: Filter by tags (any match)
        currency: Filter by currency code
        limit: Max results (default 100, max 1000)
        offset: Offset for pagination (first index to of list return (use if limit is low then the total size of the assets, to move the show window)

    Returns:
        List of matching transactions
    """
    # Build date range if provided
    date_range = None
    if date_start:
        start = parse_ISO_date(date_start)
        end = parse_ISO_date(date_end) if date_end else None
        date_range = DateRangeModel(start=start, end=end)

    params = TXQueryParams(
        broker_id=broker_id,
        asset_id=asset_id,
        types=types,
        date_range=date_range,
        tags=tags,
        currency=currency,
        limit=limit,
        offset=offset,
        )

    service = TransactionService(session)
    return await service.query(params)


@tx_router.get("/types", response_model=List[TXTypeMetadata])
async def get_transaction_types() -> List[TXTypeMetadata]:
    """
    Get metadata for all transaction types.

    Returns icons, descriptions, and validation rules for each type.
    Frontend uses this to validate user input and show correct UI.

    Returns:
        List of transaction type metadata
    """
    return list(TX_TYPE_METADATA.values())


@tx_router.get("/{tx_id}", response_model=TXReadItem)
async def get_transaction(
    tx_id: int,
    session: AsyncSession = Depends(get_session_generator),
    ) -> TXReadItem:
    """
    Get a single transaction by ID.

    Args:
        tx_id: Transaction ID

    Returns:
        Transaction details

    Raises:
        HTTPException 404: If transaction not found
    """
    service = TransactionService(session)
    result = await service.get_by_id(tx_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")

    return result


# =============================================================================
# UPDATE
# =============================================================================

@tx_router.patch("", response_model=TXBulkUpdateResponse)
async def update_transactions(
    items: List[TXUpdateItem],
    session: AsyncSession = Depends(get_session_generator),
    ) -> TXBulkUpdateResponse:
    """
    Update multiple transactions.

    Only provided fields will be updated.
    Type cannot be changed. related_transaction_id cannot be updated directly.

    Args:
        items: List of updates (each must include id)

    Returns:
        TXBulkUpdateResponse with results for each item
    """
    logger.info(f"Updating {len(items)} transactions")

    service = TransactionService(session)
    response = await service.update_bulk(items)

    if not response.errors:
        await session.commit()
        logger.info(f"Updated {response.success_count} transactions successfully")
    else:
        await session.rollback()
        logger.warning(f"Transaction update had errors: {response.errors}")

    return response


# =============================================================================
# DELETE
# =============================================================================

@tx_router.delete("", response_model=TXBulkDeleteResponse)
async def delete_transactions(
    ids: List[int] = Query(..., description="Transaction IDs to delete"),
    session: AsyncSession = Depends(get_session_generator),
    ) -> TXBulkDeleteResponse:
    """
    Delete multiple transactions.

    For linked transactions, both must be included in the delete request.
    Validates balances after deletion.

    Args:
        ids: List of transaction IDs to delete

    Returns:
        TXBulkDeleteResponse with results
    """
    logger.info(f"Deleting {len(ids)} transactions")

    items = [TXDeleteItem(id=id_) for id_ in ids]

    service = TransactionService(session)
    response = await service.delete_bulk(items)

    if not response.errors:
        await session.commit()
        logger.info(f"Deleted {response.total_deleted} transactions successfully")
    else:
        await session.rollback()
        logger.warning(f"Transaction deletion had errors: {response.errors}")

    return response
