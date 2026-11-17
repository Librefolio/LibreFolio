"""Enricher endpoints (``/assets/enrichers``, plan 68 B3): the installed enrichers and what they declare.

The bindings of an asset are written with the asset (``POST`` and ``PATCH /assets``, field ``enrichers``) and read with
it (``GET /assets``, field ``enrichers``): one door to write, as for the profile (plan §3.5).
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.app.api.v1.assets.providers import enforce_probe_limit
from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.enrichers import FAEnricherBinding, FAEnricherRecognition, FAEnricherRecognizeRequest, FAEnrichersCatalogue, FAEnricherSearchResult, FAEnricherTestRequest
from backend.app.services.enrichers.base import EnricherBinding, EnricherPlugin
from backend.app.services.enrichers.bindings import default_order, enrichers_catalogue, installed_enrichers
from backend.app.services.enrichers.recognize import IdentifierLearned, Recognized, RecognizeStatus, recognize_cascade
from backend.app.services.enrichers.usable import NOT_CONFIGURED, bind_settings, configured_enricher

logger = get_logger(__name__)

enricher_router = APIRouter()


@enricher_router.get("/enrichers", response_model=FAEnrichersCatalogue, tags=["FA Enrichers"])
def list_enrichers(_current_user: User = Depends(get_current_user)) -> FAEnrichersCatalogue:
    """The installed enrichers with what each declares, and per asset type their default order (degree, then code)."""
    return enrichers_catalogue()


async def _enricher(code: str) -> EnricherPlugin:
    """The enricher of ``code`` with its settings bound: 404 when it is not served (not installed, test-only outside
    test mode, turned off by ``LIBREFOLIO_ENRICHERS_ENABLED``), 400 ``NOT_CONFIGURED`` when a required setting is empty."""
    plugin, missing = await configured_enricher(code)
    if plugin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No enricher '{code}'")
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": NOT_CONFIGURED, "missing": list(missing)})
    return plugin


def _recognition(event: Recognized) -> FAEnricherRecognition:
    return FAEnricherRecognition(
        code=event.code,
        identifier_type=event.binding.identifier_type,
        identifier=event.binding.identifier,
        status=event.status.value,
        name=event.name,
        page_url=event.page_url,
        identifiers=dict(event.identifiers),
        conflicts=dict(event.conflicts),
        error=event.error,
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


async def _recognize_events(request: FAEnricherRecognizeRequest) -> AsyncIterator[str]:
    """The cascade as Server-Sent Events: ``enricher_result``, ``identifier_learned``, and last ``done``."""
    installed = installed_enrichers()
    if request.codes is not None:
        wanted = set(request.codes)
        installed = [plugin for plugin in installed if plugin.code in wanted]
    plugins: list[EnricherPlugin] = []
    for plugin in installed:
        if not await bind_settings(plugin):  # one with a required setting left empty is not asked
            plugins.append(plugin)
    found_order: list[str] = []
    known = dict(request.identifiers)
    async for event in recognize_cascade(request.asset_type, request.identifiers, plugins=plugins):
        if isinstance(event, IdentifierLearned):
            known[event.identifier_type] = event.identifier
            yield _sse({"event": "identifier_learned", "identifier_type": event.identifier_type, "identifier": event.identifier, "source": event.source})
            continue
        if event.status is RecognizeStatus.FOUND:
            found_order.append(event.code)
        yield _sse({"event": "enricher_result", **_recognition(event).model_dump()})
    codes = {plugin.code for plugin in plugins}
    order = [code for code in default_order(request.asset_type, price_provider_code=request.price_provider_code, found_order=found_order) if code in codes]
    yield _sse({"event": "done", "found_order": found_order, "default_order": order, "identifiers": known})


@enricher_router.post("/enrichers/recognize", tags=["FA Enrichers"])
async def recognize_enrichers(request: FAEnricherRecognizeRequest, current_user: User = Depends(get_current_user)) -> StreamingResponse:
    """«Recognize» in cascade from the identifiers known, as Server-Sent Events (plan B4); usable before the asset exists.

    Events, one ``data: {json}`` each, with an ``event`` key:

    - ``enricher_result``: one enricher's answer (``FAEnricherRecognition``: ``found``, ``not_found``, ``conflict`` or
      ``error``);
    - ``identifier_learned``: a strong identifier (ISIN, LEI) the cascade learned, and from which enricher;
    - ``done``: ``found_order`` (the enrichers found, as they answered), ``default_order`` (the order the asset's
      bindings would take: degree, then the price provider's enricher, then ``found_order``, then code) and
      ``identifiers`` (every identifier known at the end).

    Counted once on the probe's per-user limit (plan C0), however many enrichers it asks: past it, 429 before any event.
    """
    enforce_probe_limit(current_user.id)
    return StreamingResponse(_recognize_events(request), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


@enricher_router.get("/enrichers/{code}/search", response_model=List[FAEnricherSearchResult], tags=["FA Enrichers"])
async def search_enricher(code: str, q: str = Query(..., min_length=1, max_length=200), current_user: User = Depends(get_current_user)) -> List[FAEnricherSearchResult]:
    """One enricher's search by a word (the E7 window's «search»); 400 for an enricher that does not search; counted on the
    probe's per-user limit (plan C0)."""
    enforce_probe_limit(current_user.id)
    plugin = await _enricher(code)
    if not plugin.supports_search:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"The enricher '{code}' does not search")
    results = await asyncio.to_thread(plugin.search, q)
    return [FAEnricherSearchResult(name=result.name, binding=FAEnricherBinding(identifier_type=result.binding.identifier_type, identifier=result.binding.identifier, **dict(result.binding.params)), asset_type=result.asset_type, page_url=result.page_url) for result in results]


@enricher_router.post("/enrichers/{code}/test", response_model=FAEnricherRecognition, tags=["FA Enrichers"])
async def test_enricher(code: str, request: FAEnricherTestRequest, current_user: User = Depends(get_current_user)) -> FAEnricherRecognition:
    """«Recognize» one binding on one enricher (the E7 window's «test»): writes nothing; counted on the probe's per-user
    limit (plan C0)."""
    enforce_probe_limit(current_user.id)
    plugin = await _enricher(code)
    extra = {key: value for key, value in request.binding.model_dump().items() if key not in ("identifier_type", "identifier")}
    binding = EnricherBinding(identifier_type=request.binding.identifier_type, identifier=request.binding.identifier, params=extra)
    try:
        answer = await asyncio.to_thread(plugin.recognize, binding)
    except Exception as error:  # noqa: BLE001 — isolation boundary: a plugin that fails answers «error», logged
        logger.warning("Enricher test failed", enricher=code, exc_info=error)
        return FAEnricherRecognition(code=code, identifier_type=binding.identifier_type, identifier=binding.identifier, status=RecognizeStatus.ERROR.value, error=type(error).__name__)
    found = RecognizeStatus.FOUND if answer.found else RecognizeStatus.NOT_FOUND
    return FAEnricherRecognition(code=code, identifier_type=binding.identifier_type, identifier=binding.identifier, status=found.value, name=answer.name, page_url=answer.page_url, identifiers=dict(answer.identifiers or {}))
