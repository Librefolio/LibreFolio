"""Lookup routes of BRIM: duplicate detection, the plugin list and the asset candidates."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User, UserRole
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brim import (
    BRIMAssetCandidate,
    BRIMAssetCandidatesRequest,
    BRIMDuplicateCheckRequest,
    BRIMDuplicateReport,
    BRIMPluginInfo,
)
from backend.app.services.brim.candidates import search_asset_candidates
from backend.app.services.brim.duplicates import detect_tx_duplicates
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brokers.broker_service import BrokerService

logger = get_logger(__name__)

lookup_router = APIRouter()


@lookup_router.post("/duplicates", response_model=BRIMDuplicateReport)
async def check_duplicates(
    request: BRIMDuplicateCheckRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMDuplicateReport:
    """
    Re-run duplicate detection on transactions in their current, user-edited state.

    ``/parse`` also returns a duplicate report, but it is computed on the plugin's raw
    output. That verdict goes stale as soon as the user changes anything: a row the
    plugin could only book as a cash movement — because the file did not give it the
    instrument — gets compared against cash movements rather than against the purchase
    it really is, and correcting it later never re-opens the question.

    Call this once the transactions are final (assets unified, flagged rows corrected)
    to get a verdict computed on the data that will actually be imported.

    Requires EDITOR or OWNER access on the target broker.
    """
    broker_service = BrokerService(session)
    role = await broker_service._check_user_access(request.broker_id, current_user.id, min_role=UserRole.EDITOR)
    if not current_user.is_superuser and role is None:
        raise HTTPException(status_code=403, detail="EDITOR or OWNER access required to check duplicates for this broker")

    duplicates = await detect_tx_duplicates(
        transactions=request.transactions,
        broker_id=request.broker_id,
        session=session,
        asset_mappings=request.asset_mappings,
    )

    logger.info(
        "Duplicate check re-run on corrected transactions",
        broker_id=request.broker_id,
        transaction_count=len(request.transactions),
        unique_tx_count=len(duplicates.tx_unique_indices),
        possible_duplicates=len(duplicates.tx_possible_duplicates),
        likely_duplicates=len(duplicates.tx_likely_duplicates),
    )

    return duplicates


# =============================================================================
# PLUGIN INFO
# =============================================================================


@lookup_router.get("/plugins", response_model=List[BRIMPluginInfo])
async def list_plugins(_current_user: User = Depends(get_current_user)) -> List[BRIMPluginInfo]:
    """
    List all available import plugins.

    Returns plugin metadata including code, name, description,
    and supported file extensions.
    """
    return BRIMProviderRegistry.list_plugin_info()


@lookup_router.post(
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
