"""Broker access routes: who may reach a broker, and what role they hold (``/brokers/{id}/access``)."""

import asyncio
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brokers import (
    BRAccessBulkItem,
    BRAccessBulkResponse,
    BRAccessItem,
    BRAccessListResponse,
    BRSelfAccessResponse,
    BRSelfRoleUpdate,
)
from backend.app.services.brim import brim_provider
from backend.app.services.brokers.broker_service import BrokerService

logger = get_logger(__name__)

access_router = APIRouter(prefix="/brokers")

# =============================================================================
# BROKER ACCESS MANAGEMENT
# =============================================================================


@access_router.get("/{broker_id}/access", response_model=BRAccessListResponse)
async def list_broker_access(
    broker_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> BRAccessListResponse:
    """
    List all users with access to a broker.

    Any authenticated user can read the access list of any existing broker, email addresses included; a broker that
    does not exist answers 404.
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


@access_router.put("/{broker_id}/access", response_model=BRAccessBulkResponse)
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
    - At least one OWNER must remain after the operation: nobody, the caller included, can remove or downgrade the
      last one.
    - Only OWNERs can have share_percentage > 0.
    - Sum of all share_percentage values must be ≤ 1.0 (fraction, not percent).
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


@access_router.patch("/{broker_id}/access/me", response_model=BRSelfAccessResponse)
async def update_own_broker_role(
    broker_id: int,
    item: BRSelfRoleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> BRSelfAccessResponse:
    """
    Self-service role change (F4) — demotion only:
    - EDITOR → VIEWER
    - OWNER → EDITOR/VIEWER, only when at least one other OWNER remains
      (the last OWNER must promote someone else first).

    Promotions are reserved to the OWNER-only bulk PUT endpoint.
    """
    service = BrokerService(session)
    success, message = await service.update_own_role(broker_id, current_user.id, item.role)
    if not success:
        status = 403 if "no access" in message else 400
        raise HTTPException(status_code=status, detail=message)

    await session.commit()
    logger.info(f"User self-demoted on broker {broker_id}", user_id=current_user.id, new_role=item.role.value)
    return BRSelfAccessResponse(success=True, message=message, broker_deleted=False)


@access_router.delete("/{broker_id}/access/me", response_model=BRSelfAccessResponse)
async def leave_broker_access(
    broker_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session_generator),
) -> BRSelfAccessResponse:
    """
    Remove the caller's own access to a broker (F4).

    - EDITOR/VIEWER: always allowed.
    - OWNER: allowed when another OWNER remains.
    - The LAST owner leaving deletes the broker entirely — cascade over
      transactions and BRIM report files (confirmed F4 semantics).
    """
    service = BrokerService(session)
    success, message, broker_deleted = await service.leave_broker(broker_id, current_user.id)
    if not success:
        status = 403 if "no access" in message else 400
        raise HTTPException(status_code=status, detail=message)

    await session.commit()

    if broker_deleted:
        # Same orphaned-BRIM-file cleanup as the bulk delete endpoint
        files_removed = await asyncio.to_thread(brim_provider.delete_files_for_brokers, [broker_id])
        logger.info(f"Broker {broker_id} cascade-deleted: last owner left", user_id=current_user.id, brim_files_removed=files_removed)
    else:
        logger.info(f"User left broker {broker_id}", user_id=current_user.id)

    return BRSelfAccessResponse(success=True, message=message, broker_deleted=broker_deleted)
