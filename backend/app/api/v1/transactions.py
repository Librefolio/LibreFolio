"""
Transaction API endpoints for LibreFolio.

0
Unified Batch Pipeline:
- POST   /transactions/validate       Dry-run: always rollback
- POST   /transactions/commit         Commit if no issues
- GET    /transactions                Query with filters (access-scoped)
- GET    /transactions?ids=1,2,3      Batch read preserving input order
- GET    /transactions/types          Transaction type metadata

Semantics:
- Access control is EDITOR on every distinct `broker_id` touched by a batch.
- Any failure → full session rollback, `committed=False`, per-item issues.
- GET /transactions is filtered to brokers the user can at least VIEW.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import TransactionType, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.transactions import (
    TX_TYPE_METADATA,
    TXBatchResponse,
    TXCreateItem,
    TXEventSuggestRequestItem,
    TXEventSuggestResultItem,
    TXMixedBatch,
    TXQueryParams,
    TXReadItem,
    TXTransferPromoteRequest,
    TXTransferPromoteResponse,
    TXTypeMetadata,
    TXUpdateItem,
)
from backend.app.services.transaction_service import TransactionService
from backend.app.utils.datetime_utils import parse_ISO_date

logger = get_logger(__name__)

tx_router = APIRouter(prefix="/transactions", tags=["TX (Transactions)"])


# =============================================================================
# VALIDATE (dry-run unified batch)
# =============================================================================


@tx_router.post(
    "/validate",
    response_model=TXBatchResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "creates": {"type": "array", "items": TXCreateItem.model_json_schema()},
                            "updates": {"type": "array", "items": TXUpdateItem.model_json_schema()},
                            "deletes": {"type": "array", "items": {"type": "integer"}},
                        },
                    }
                }
            }
        }
    },
)
async def validate_transactions(
    batch: TXMixedBatch,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXBatchResponse:
    """
    Dry-run validator for a mixed batch (creates + updates + deletes).

    Semantics:
    - Applies `deletes -> updates -> creates` in a single session that is
      ALWAYS rolled back at the end (never commits).
    - Does NOT stop at the first error: collects the full set of issues so
      the UI can show all problems at once.
    - Schema errors and balance violations coexist in the same response.
    - `committed` is always False.
    """
    user_id = current_user.id
    service = TransactionService(session)
    response = await service.execute_batch(
        creates_raw=batch.creates,
        updates_raw=batch.updates,
        deletes=batch.deletes,
        user_id=user_id,
        commit=False,
    )
    # Always rollback for dry-run
    await session.rollback()
    return response


# =============================================================================
# COMMIT (unified batch)
# =============================================================================


@tx_router.post(
    "/commit",
    response_model=TXBatchResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "creates": {"type": "array", "items": TXCreateItem.model_json_schema()},
                            "updates": {"type": "array", "items": TXUpdateItem.model_json_schema()},
                            "deletes": {"type": "array", "items": {"type": "integer"}},
                        },
                    }
                }
            }
        }
    },
)
async def commit_transactions(
    batch: TXMixedBatch,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXBatchResponse:
    """
    Commit a mixed batch (creates + updates + deletes).

    Semantics:
    - If any issue is detected → rollback, `committed=False`.
    - If clean → commit, `committed=True`, `results` populated.
    """
    user_id = current_user.id
    logger.info(
        "Commit batch: %d creates, %d updates, %d deletes",
        len(batch.creates),
        len(batch.updates),
        len(batch.deletes),
        user_id=user_id,
    )

    service = TransactionService(session)
    response = await service.execute_batch(
        creates_raw=batch.creates,
        updates_raw=batch.updates,
        deletes=batch.deletes,
        user_id=user_id,
        commit=True,
    )

    if response.committed:
        await session.commit()
        logger.info("Batch committed", user_id=user_id)
    else:
        await session.rollback()
        logger.warning("Batch rolled back: %d issues", len(response.issues), user_id=user_id)

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
    amount_abs_min: Optional[Decimal] = Query(None, description="ABS(amount) >= N (H.3 transfer-match)"),
    amount_abs_max: Optional[Decimal] = Query(None, description="ABS(amount) <= N (H.3 transfer-match)"),
    only_unlinked: bool = Query(False, description="Only transactions without related_transaction_id"),
    exclude_ids: Optional[List[int]] = Query(None, description="Exclude specific IDs (ignored when `ids` is set)"),
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
        amount_abs_min=amount_abs_min,
        amount_abs_max=amount_abs_max,
        only_unlinked=only_unlinked,
        exclude_ids=exclude_ids,
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

        raise HTTPException(status_code=422, detail="Max 500 requests per call")

    service = TransactionService(session)
    return await service.suggest_events_bulk(requests)


# =============================================================================
# TRANSFER PROMOTION (Block H.4)
# =============================================================================


@tx_router.post("/transfers/promote", response_model=TXTransferPromoteResponse)
async def promote_transfer(
    req: TXTransferPromoteRequest,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXTransferPromoteResponse:
    """
    Promote a DEPOSIT/WITHDRAWAL pair into TRANSFER or FX_CONVERSION.

    Atomic: deletes the original pair and creates the new pair in the same
    session. Any failure rolls back the whole operation. `type` being
    immutable on PATCH means this is the only way to change a cash pair
    into a typed asset transfer or currency conversion.
    """
    user_id = current_user.id
    logger.info(
        "Promote transfer %s+%s -> %s",
        req.from_tx_id,
        req.to_tx_id,
        req.new_type.value,
        user_id=user_id,
    )

    service = TransactionService(session)
    response = await service.promote_transfer(req, user_id=user_id)

    if not response.rolled_back:
        await session.commit()
        logger.info(
            "Promoted transfer: new ids %s,%s",
            response.new_from_tx_id,
            response.new_to_tx_id,
            user_id=user_id,
        )
    else:
        await session.rollback()
        logger.warning("Promote transfer rolled back: %s", response.errors, user_id=user_id)

    return response
