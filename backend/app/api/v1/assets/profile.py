"""Asset profile endpoints (``/assets/profile``, plan 68 §3.5): read it, its catalogue, forget rows; ask the enrichers.

The profile is written through ``POST`` and ``PATCH /assets`` (one door to write). Here:

- ``query`` reads voices as steps in a date range, and a page of changes (D1);
- ``catalogue`` lists the voices, for the forms (D1);
- ``DELETE`` forgets rows («Dimentica»), all or nothing, guarded by the ``as_of`` of the read the page shows (D1);
- ``ask`` reads the enrichers without saving, ``refresh`` («Aggiorna») saves as the weekly read does (B5a).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.assets.providers import enforce_probe_limit
from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import Asset, AssetType, User
from backend.app.db.session import get_session_generator
from backend.app.schemas.assets.profile import (
    FAProfileAskRequest,
    FAProfileAskResponse,
    FAProfileAskVoice,
    FAProfileCatalogueResponse,
    FAProfileChange,
    FAProfileChangesPage,
    FAProfileForgetItem,
    FAProfileForgetResponse,
    FAProfileForgetResult,
    FAProfileQueryItem,
    FAProfileQueryResponse,
    FAProfileQueryResult,
    FAProfileReadOutcome,
    FAProfileRefreshResponse,
    FAProfileRefreshResult,
    FAProfileStepPoint,
)
from backend.app.services.assets.profile.catalogue import CATALOGUE
from backend.app.services.assets.profile.store import CHANGES_PAGE_SIZE, ProfileChangesPage, ProfileUpdatesNewer, ProfileUpdatesNotFound, forget_updates, read_steps, recent_changes
from backend.app.services.enrichers.bindings import load_enrichers
from backend.app.services.enrichers.refresh import ReadOutcome, refresh_assets
from backend.app.services.enrichers.refresh import ask_profile as read_and_merge
from backend.app.utils.date_range_limits import MAX_BULK_ITEMS, MAX_BULK_WRITE_ITEMS, bulk_too_many_items_detail
from backend.app.utils.datetime_utils import utcnow

profile_router = APIRouter()

#: The ``error`` of a read item whose asset does not exist, as the price read writes it.
ASSET_NOT_FOUND = "Asset not found"
#: A voice the catalogue does not list, asked in a read (422).
PROFILE_VOICE_UNKNOWN = "PROFILE_VOICE_UNKNOWN"
#: Rows asked to be forgotten that are not rows of that asset (404).
PROFILE_UPDATES_NOT_FOUND = "PROFILE_UPDATES_NOT_FOUND"
#: Rows asked to be forgotten that were written after the read the page shows (409: the page reloads).
PROFILE_UPDATES_NEWER = "PROFILE_UPDATES_NEWER"


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
async def ask_profile(request: FAProfileAskRequest, session: AsyncSession = Depends(get_session_generator), current_user: User = Depends(get_current_user)) -> FAProfileAskResponse:
    """What the enrichers give now, merged voice by voice, without saving (a read younger than 30 minutes is reused).

    Either ``asset_id`` (its bindings and type) or ``asset_type`` with ``enrichers`` (an asset not created yet); without
    ``keys`` every voice («Chiedi tutto»). 404 for an ``asset_id`` that does not exist. Counted on the probe's per-user
    limit (plan C0); «Aggiorna» (``refresh``) is not: it reads bindings already saved.
    """
    enforce_probe_limit(current_user.id)
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


# =============================================================================
# READ, CATALOGUE, FORGET (D1)
# =============================================================================


@profile_router.get("/profile/catalogue", response_model=FAProfileCatalogueResponse, tags=["FA Profile"])
def profile_catalogue(_current_user: User = Depends(get_current_user)) -> FAProfileCatalogueResponse:
    """Every voice of the profile with its shape, sign, unit, groups and choices, in the catalogue's order."""
    return FAProfileCatalogueResponse(voices=list(CATALOGUE.values()))


def _unknown_voice(items: List[FAProfileQueryItem]) -> str | None:
    """The first voice asked (in ``keys`` or in ``changes.key``) that the catalogue does not list."""
    for item in items:
        asked = list(item.keys or [])
        if item.changes is not None and item.changes.key is not None:
            asked.append(item.changes.key)
        for key in asked:
            if key not in CATALOGUE:
                return key
    return None


def _changes_page(page: ProfileChangesPage, number: int, size: int) -> FAProfileChangesPage:
    items = [
        FAProfileChange(
            id=change.row.id,
            key=change.row.key,
            value=change.row.value,
            previous=change.previous,
            has_previous=change.has_previous,
            source=change.row.source,
            user_id=change.row.user_id,
            read_on=change.row.read_on,
            source_date=change.row.source_date,
            created_at=change.row.created_at,
        )
        for change in page.items
    ]
    return FAProfileChangesPage(items=items, total=page.total, page=number, page_size=size)


@profile_router.post("/profile/query", response_model=FAProfileQueryResponse, tags=["FA Profile"])
async def query_profile(items: List[FAProfileQueryItem], session: AsyncSession = Depends(get_session_generator), _current_user: User = Depends(get_current_user)) -> FAProfileQueryResponse:
    """The voices of each asset as steps in its ``date_range`` (never carried back before the first row), and a page of
    changes when ``changes`` is given. An asset with no rows answers no voice; one that does not exist answers ``error``
    «Asset not found» in its item, and the other items are read (D1b).

    ``as_of`` is taken before the read: «Dimentica» sends it back, so a row written after it is never forgotten by a page
    that has not shown it. A voice the catalogue does not list is refused (422 ``PROFILE_VOICE_UNKNOWN``) before any read.
    """
    if len(items) > MAX_BULK_ITEMS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=bulk_too_many_items_detail(len(items), MAX_BULK_ITEMS))
    unknown = _unknown_voice(items)
    if unknown is not None:
        detail = {"error_code": PROFILE_VOICE_UNKNOWN, "message": f"'{unknown}' is not a voice of the profile catalogue", "voice": unknown}
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    # End the transaction the login check opened: the read below starts after as_of, so it sees every row written before
    await session.commit()
    as_of = utcnow()
    asked = list(dict.fromkeys(item.asset_id for item in items))
    existing = set((await session.execute(select(Asset.id).where(Asset.id.in_(asked)))).scalars().all()) if asked else set()
    results: List[FAProfileQueryResult] = []
    for item in items:
        if item.asset_id not in existing:
            results.append(FAProfileQueryResult(asset_id=item.asset_id, error=ASSET_NOT_FOUND))
            continue
        steps = (await read_steps(session, [item.asset_id], item.date_range, item.keys)).get(item.asset_id, {})
        voices = {key: [FAProfileStepPoint(date=step.date, through=step.through, value=step.value, source=step.source, update_id=step.update_id, opened_on=step.opened_on, source_date=step.source_date) for step in voice_steps] for key, voice_steps in steps.items()}
        changes = None
        if item.changes is not None:
            page = await recent_changes(session, item.asset_id, key=item.changes.key, page=item.changes.page)
            changes = _changes_page(page, item.changes.page, CHANGES_PAGE_SIZE)
        results.append(FAProfileQueryResult(asset_id=item.asset_id, voices=voices, changes=changes))
    return FAProfileQueryResponse(as_of=as_of, items=results)


@profile_router.delete("/profile", response_model=FAProfileForgetResponse, tags=["FA Profile"])
async def forget_profile(items: List[FAProfileForgetItem], session: AsyncSession = Depends(get_session_generator), _current_user: User = Depends(get_current_user)) -> FAProfileForgetResponse:
    """«Dimentica»: delete those rows, as if the changes had never been made; «now» follows from the rows left.

    All or nothing over the whole request: an id that is not a row of its asset (404 ``PROFILE_UPDATES_NOT_FOUND``) or a
    row written after the item's ``as_of`` (409 ``PROFILE_UPDATES_NEWER``: the page reloads) deletes nothing. At most
    ``MAX_BULK_WRITE_ITEMS`` ids (422 ``bulk_too_many_items``).
    """
    ids = sum(len(item.update_ids) for item in items)
    if ids > MAX_BULK_WRITE_ITEMS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=bulk_too_many_items_detail(ids, MAX_BULK_WRITE_ITEMS))
    await session.commit()  # the login check's read transaction: the write below must not upgrade a stale snapshot
    results: List[FAProfileForgetResult] = []
    try:
        for item in items:
            deleted = await forget_updates(session, item.asset_id, item.update_ids, as_of=item.as_of)
            results.append(FAProfileForgetResult(asset_id=item.asset_id, success=True, deleted_count=deleted))
    except (ProfileUpdatesNotFound, ProfileUpdatesNewer) as error:
        await session.rollback()
        newer = isinstance(error, ProfileUpdatesNewer)
        detail = {"error_code": PROFILE_UPDATES_NEWER if newer else PROFILE_UPDATES_NOT_FOUND, "message": str(error), "asset_id": error.asset_id, "update_ids": list(error.update_ids)}
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if newer else status.HTTP_404_NOT_FOUND, detail=detail) from error
    await session.commit()
    return FAProfileForgetResponse(results=results, success_count=len(results), total_deleted=sum(result.deleted_count for result in results))
