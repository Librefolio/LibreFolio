"""Broker CRUD routes: create, list, read, update and delete (``/brokers``)."""

import asyncio
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brokers import (
    BRBulkCreateResponse,
    BRBulkDeleteResponse,
    BRBulkUpdateResponse,
    BRCreateItem,
    BRDeleteItem,
    BRListResponse,
    BRReadItem,
    BRUpdateItem,
)
from backend.app.services.brim import brim_provider
from backend.app.services.brokers.broker_service import BROKER_NAME_RECOVERY, BrokerService

logger = get_logger(__name__)

crud_router = APIRouter(prefix="/brokers")

# =============================================================================
# CREATE
# =============================================================================


@crud_router.post("", response_model=BRBulkCreateResponse)
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
        try:
            await session.commit()
        except IntegrityError:
            # The duplicate-name check inside `create_bulk` is a SELECT followed
            # by an INSERT, so two requests racing on the same name both pass it
            # and the loser only finds out at flush time. Without this the user
            # gets a bare 500 instead of the reason, which is the one thing that
            # would let them fix it.
            await session.rollback()
            logger.warning("Broker creation lost a uniqueness race", user_id=user_id)
            raise HTTPException(
                status_code=409,
                detail=f"A broker with that name already exists. {BROKER_NAME_RECOVERY}",
            ) from None
        logger.info(f"Created {response.success_count} brokers successfully", user_id=user_id)
    else:
        await session.rollback()
        logger.warning(f"Broker creation had errors: {response.errors}", user_id=user_id)

    return response


# =============================================================================
# READ
# =============================================================================


@crud_router.get("", response_model=BRListResponse)
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

    Returns:
        List of brokers ordered by name
    """
    # Validate as_user_id permission
    if as_user_id is not None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can use as_user_id parameter")

    service = BrokerService(session)
    return await service.get_all(user_id=current_user.id, as_user_id=as_user_id, include_inaccessible=include_inaccessible)


@crud_router.get("/{broker_id}", response_model=BRReadItem)
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


# =============================================================================
# UPDATE
# =============================================================================


@crud_router.patch("/{broker_id}", response_model=BRBulkUpdateResponse)
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


@crud_router.delete("", response_model=BRBulkDeleteResponse)
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
        # Cascade-delete orphaned BRIM import files for each broker that was actually
        # deleted (files are on the filesystem, so the ORM cascade misses them). Done
        # post-commit and best-effort so a filesystem hiccup never fails the delete.
        deleted_broker_ids = [r.id for r in response.results if r.success]
        files_removed = await asyncio.to_thread(brim_provider.delete_files_for_brokers, deleted_broker_ids)
        logger.info(f"Deleted {response.total_deleted} brokers successfully", user_id=user_id, brim_files_removed=files_removed)
    else:
        await session.rollback()
        logger.warning(f"Broker deletion had errors: {response.errors}", user_id=user_id)

    return response
