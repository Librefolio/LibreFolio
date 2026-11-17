"""Asset profile endpoints (``/assets/profile``, plan 68 §3.5): ask the enrichers, refresh from them.

The profile is written through ``POST`` and ``PATCH /assets`` (one door to write); here the enrichers are read: ``ask``
without saving, ``refresh`` («Aggiorna») saving as the weekly read does.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import Asset, AssetType, User
from backend.app.db.session import get_session_generator
from backend.app.schemas.assets.profile import FAProfileAskRequest, FAProfileAskResponse, FAProfileAskVoice, FAProfileReadOutcome, FAProfileRefreshResponse, FAProfileRefreshResult
from backend.app.services.enrichers.bindings import load_enrichers
from backend.app.services.enrichers.refresh import ReadOutcome, refresh_assets
from backend.app.services.enrichers.refresh import ask_profile as read_and_merge

profile_router = APIRouter()


def _read_outcome(outcome: ReadOutcome) -> FAProfileReadOutcome:
    return FAProfileReadOutcome(
        code=outcome.code,
        identifier_type=outcome.binding.identifier_type,
        identifier=outcome.binding.identifier,
        status=outcome.status.value,
        voices=sorted(outcome.values),
        error_code=outcome.error_code,
        retry_after=outcome.retry_after,
        from_cache=outcome.from_cache,
    )


@profile_router.post("/profile/ask", response_model=FAProfileAskResponse, tags=["FA Profile"])
async def ask_profile(request: FAProfileAskRequest, session: AsyncSession = Depends(get_session_generator), _current_user: User = Depends(get_current_user)) -> FAProfileAskResponse:
    """What the enrichers give now, merged voice by voice, without saving (a read younger than 30 minutes is reused).

    Either ``asset_id`` (its bindings and type) or ``asset_type`` with ``enrichers`` (an asset not created yet); without
    ``keys`` every voice («Chiedi tutto»). 404 for an ``asset_id`` that does not exist.
    """
    if request.asset_id is not None:
        asset_type = (await session.execute(select(Asset.asset_type).where(Asset.id == request.asset_id))).scalar_one_or_none()
        if asset_type is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {request.asset_id} not found")
        row = (await load_enrichers(session, [request.asset_id])).get(request.asset_id)
        config = row.config if row is not None else {}
        await session.commit()  # nothing held while the enrichers are read
    else:
        asset_type = request.asset_type
        config = {code: binding.model_dump() for code, binding in (request.enrichers or {}).items()}
    result = await read_and_merge(AssetType(asset_type), config, request.keys)
    voices = {key: FAProfileAskVoice(value=voice.value, source=voice.source, source_date=voice.source_date, others=dict(voice.others)) for key, voice in result.voices.items()}
    return FAProfileAskResponse(voices=voices, outcomes=[_read_outcome(outcome) for outcome in result.outcomes])


@profile_router.post("/profile/refresh", response_model=FAProfileRefreshResponse, tags=["FA Profile"])
async def refresh_profile(asset_ids: List[int], session: AsyncSession = Depends(get_session_generator), _current_user: User = Depends(get_current_user)) -> FAProfileRefreshResponse:
    """«Aggiorna»: read the enrichers of those assets and save what changed, as the weekly read does (a read younger than
    30 minutes is reused). Inactive assets are read too. An asset that does not exist gets ``error``."""
    results = await refresh_assets(session, asset_ids)
    return FAProfileRefreshResponse(results=[FAProfileRefreshResult(asset_id=result.asset_id, written=result.written, outcomes=[_read_outcome(outcome) for outcome in result.outcomes], error=result.error) for result in results])
