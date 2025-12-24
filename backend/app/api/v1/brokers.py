"""
Broker API endpoints for LibreFolio.

Provides RESTful endpoints for broker management:
- POST /brokers: Create brokers (with optional initial deposits)
- GET /brokers: List all brokers
- GET /brokers/{id}: Get broker details
- GET /brokers/{id}/summary: Get broker with balances and holdings
- PATCH /brokers/{id}: Update broker
- DELETE /brokers: Bulk delete brokers
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
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
from backend.app.services.broker_service import BrokerService

logger = get_logger(__name__)

broker_router = APIRouter(prefix="/brokers", tags=["brokers"])


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
