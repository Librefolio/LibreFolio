"""
Transaction API endpoints for LibreFolio.

Part 3 atomic multi-broker API:
- POST   /transactions/bulk           Atomic bulk create (spans multiple brokers)
- PATCH  /transactions/bulk           Atomic bulk update
- DELETE /transactions/bulk?ids=…     Atomic bulk delete
- GET    /transactions                Query with filters (access-scoped)
- GET    /transactions?ids=1,2,3      Batch read preserving input order
- GET    /transactions/types          Transaction type metadata

Semantics:
- Access control is EDITOR on every distinct `broker_id` touched by a batch.
- Any failure → full session rollback, `rolled_back=True`, per-item `status`
  diagnostic (`success | simulated | failed | not_attempted`).
- GET /transactions is filtered to brokers the user can at least VIEW.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import TransactionType, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.transactions import (
    TX_TYPE_METADATA,
    TXBulkCreateResponse,
    TXBulkDeleteResponse,
    TXBulkUpdateResponse,
    TXCreateItem,
    TXEventSuggestRequestItem,
    TXEventSuggestResultItem,
    TXQueryParams,
    TXReadItem,
    TXTypeMetadata,
    TXUpdateItem,
    TXValidateBatch,
    TXValidateResponse,
)
from backend.app.services.transaction_service import TransactionService
from backend.app.utils.datetime_utils import parse_ISO_date

logger = get_logger(__name__)

tx_router = APIRouter(prefix="/transactions", tags=["TX (Transactions)"])


# =============================================================================
# CREATE (atomic bulk, multi-broker)
# =============================================================================


@tx_router.post("/bulk", response_model=TXBulkCreateResponse)
async def create_transactions_bulk(
    items: List[TXCreateItem],
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXBulkCreateResponse:
    """
    Atomic bulk create of transactions spanning one or more brokers.

    Access check EDITOR is applied once per distinct `broker_id`.
    Any failure (validation, balance, access) rolls back the entire batch
    and returns `rolled_back=True` with per-item `status`. The router commits
    only when `rolled_back=False`.

    For linked transactions (TRANSFER, FX_CONVERSION) the two items must
    share the same `link_uuid` and be in the same request — `link_uuid`
    resolution is bidirectional (both rows point to each other).
    """
    # Cache user_id before session ops — rollback expires ORM objects, after
    # which `current_user.id` would trigger a lazy-load and MissingGreenlet.
    user_id = current_user.id

    logger.info("Bulk create %d transactions", len(items), user_id=user_id)

    service = TransactionService(session)
    response = await service.create_bulk(items, user_id=user_id)

    if not response.rolled_back:
        await session.commit()
        logger.info("Committed %d new transactions", response.success_count, user_id=user_id)
    else:
        await session.rollback()
        logger.warning("Bulk create rolled back: %s", response.errors, user_id=user_id)

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
    ids: Optional[List[int]] = Query(None, description="Specific IDs to fetch, returned in input order (mutex with other filters)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> List[TXReadItem]:
    """
    Query transactions with filters, scoped to brokers the user can VIEW.

    When `ids` is provided, results are returned in the exact input order
    (useful for preserving client-side sort); other filters besides access
    are ignored.
    """
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
        ids=ids,
        limit=limit,
        offset=offset,
    )

    service = TransactionService(session)
    return await service.query(params, user_id=current_user.id)


@tx_router.get("/types", response_model=List[TXTypeMetadata])
async def get_transaction_types(_current_user: User = Depends(get_current_user)) -> List[TXTypeMetadata]:
    """Get metadata for all transaction types (icons, rules, signs)."""
    return list(TX_TYPE_METADATA.values())


# =============================================================================
# UPDATE (atomic bulk, multi-broker)
# =============================================================================


@tx_router.patch("/bulk", response_model=TXBulkUpdateResponse)
async def update_transactions_bulk(
    items: List[TXUpdateItem],
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXBulkUpdateResponse:
    """
    Atomic bulk update. Type cannot be changed; `related_transaction_id`
    cannot be updated directly. `asset_event_id=0` unlinks (Part 1 sentinel).
    """
    user_id = current_user.id
    logger.info("Bulk update %d transactions", len(items), user_id=user_id)

    service = TransactionService(session)
    response = await service.update_bulk(items, user_id=user_id)

    if not response.rolled_back:
        await session.commit()
        logger.info("Committed %d transaction updates", response.success_count, user_id=user_id)
    else:
        await session.rollback()
        logger.warning("Bulk update rolled back: %s", response.errors, user_id=user_id)

    return response


# =============================================================================
# DELETE (atomic bulk, multi-broker)
# =============================================================================


@tx_router.delete("/bulk", response_model=TXBulkDeleteResponse)
async def delete_transactions_bulk(
    ids: List[int] = Query(..., description="Transaction IDs to delete"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXBulkDeleteResponse:
    """
    Atomic bulk delete. Linked pairs (TRANSFER, FX_CONVERSION) must be
    deleted together — include both IDs in `ids` or the whole batch is
    rejected.
    """
    user_id = current_user.id
    logger.info("Bulk delete %d transactions", len(ids), user_id=user_id)

    service = TransactionService(session)
    response = await service.delete_bulk(ids, user_id=user_id)

    if not response.rolled_back:
        await session.commit()
        logger.info("Committed %d transaction deletions", response.total_deleted, user_id=user_id)
    else:
        await session.rollback()
        logger.warning("Bulk delete rolled back: %s", response.errors, user_id=user_id)

    return response


# =============================================================================
# VALIDATE (dry-run mixed batch)
# =============================================================================


@tx_router.post("/validate", response_model=TXValidateResponse)
async def validate_transactions(
    batch: TXValidateBatch,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXValidateResponse:
    """
    Dry-run validator for a mixed batch (creates + updates + deletes).

    Semantics:
    - Applies `deletes -> updates -> creates` in a single session that is
      ALWAYS rolled back at the end (never commits).
    - Does NOT stop at the first error: collects the full set of issues so
      the Staging Modal can show all problems at once.
    - `would_rollback=True` whenever any issue OR a balance violation exists.
    - `balance_preview` / `holdings_preview` are populated only when the
      batch would succeed (empty issues and no balance violation).
    """
    service = TransactionService(session)
    return await service.validate_batch(
        creates=batch.creates,
        updates=batch.updates,
        deletes=batch.deletes,
        user_id=current_user.id,
    )


# =============================================================================
# EVENTS SUGGEST
# =============================================================================


@tx_router.post("/events/suggest", response_model=List[TXEventSuggestResultItem])
async def suggest_events(
    requests: List[TXEventSuggestRequestItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
) -> List[TXEventSuggestResultItem]:
    """
    For each `(asset_id, date, type)` return candidate `AssetEvent`s whose
    type maps to the tx type and whose date is within `±tolerance_days`.

    Asset events are global, so no broker access check is needed — the
    caller only has to be authenticated. Results preserve input order and
    each list of candidates is sorted by ascending distance (days).
    """
    if len(requests) > 500:
        # Defensive: Pydantic enforces the cap on the list model, but a raw
        # list body needs an explicit check.
        from fastapi import HTTPException  # noqa: PLC0415

        raise HTTPException(status_code=422, detail="Max 500 requests per call")

    service = TransactionService(session)
    return await service.suggest_events_bulk(requests)
