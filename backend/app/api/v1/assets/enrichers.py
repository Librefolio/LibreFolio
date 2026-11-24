"""Enricher endpoints (``/assets/enrichers``, plan 68 B3): the installed enrichers and what they declare.

The bindings of an asset are written with the asset (``POST`` and ``PATCH /assets``, field ``enrichers``) and read with
it (``GET /assets``, field ``enrichers``): one door to write, as for the profile (plan §3.5).
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.app.api.plugin_errors import not_configured_error
from backend.app.api.v1.assets.providers import enforce_probe_limit
from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import AssetType, User
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.enrichers import ENRICHER_CODE, FAEnricherBinding, FAEnricherRecognition, FAEnricherRecognizeRequest, FAEnrichersCatalogue, FAEnricherSearchResult, FAEnricherTestRequest
from backend.app.services.enrichers.base import EnricherBinding, EnricherPlugin, EnricherSearchResult
from backend.app.services.enrichers.bindings import default_order, enrichers_catalogue, installed_enrichers
from backend.app.services.enrichers.recognize import IdentifierLearned, Recognized, RecognizeStatus, Seed, recognize_cascade
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.enrichers.search import SearchOutcome, asked_codes, refusal_wait, search_enrichers
from backend.app.services.enrichers.usable import bind_settings, configured_enricher
from backend.app.services.plugin_settings.readiness import plugins_readiness
from backend.app.utils.runtime.cooldown import RateLimitedError

logger = get_logger(__name__)

enricher_router = APIRouter()


@enricher_router.get("/enrichers", response_model=FAEnrichersCatalogue, tags=["FA Enrichers"])
async def list_enrichers(_current_user: User = Depends(get_current_user)) -> FAEnrichersCatalogue:
    """The installed enrichers with what each declares, and per asset type their default order (degree, then code).

    Each says whether it is configured, and what is missing, with the readiness the calls use (no user: an enricher's
    settings are the instance's), so the window and the call agree (plan 68, E7)."""
    catalogue = enrichers_catalogue()
    readiness = await plugins_readiness(EnricherRegistry.settings_family(), [info.code for info in catalogue.enrichers], user_id=None)
    for info in catalogue.enrichers:
        state = readiness.get(info.code)
        if state is not None:
            info.configured, info.missing_settings = state.configured, list(state.missing)
    return catalogue


async def _enricher(code: str) -> EnricherPlugin:
    """The enricher of ``code`` with its settings bound: 404 when it is not served (not installed, test-only outside
    test mode, turned off by ``LIBREFOLIO_ENRICHERS_ENABLED``), 422 ``NOT_CONFIGURED`` (``api/plugin_errors.py``) when a
    required setting is empty, naming the fields a caller may be told."""
    plugin, missing = await configured_enricher(code)
    if plugin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No enricher '{code}'")
    if missing:
        readiness = (await plugins_readiness(EnricherRegistry.settings_family(), [code], user_id=None)).get(code)
        raise not_configured_error(code, readiness.missing if readiness is not None and not readiness.configured else missing)
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
        params=dict(event.binding.params),
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
    seeds = [Seed(code=seed.code, binding=EnricherBinding(identifier_type=seed.identifier_type, identifier=seed.identifier, params=dict(seed.params))) for seed in request.seeds]
    for seed in request.seeds:
        # A seed's identifier is known too; it never replaces the asset's own (a different ISIN is a conflict, R7)
        known.setdefault(seed.identifier_type.strip().upper(), seed.identifier.strip())
    async for event in recognize_cascade(request.asset_type, request.identifiers, plugins=plugins, seeds=seeds):
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
      ``error``), with the binding it answered for and its ``params`` (a seed's, ENR-2);
    - ``identifier_learned``: a strong identifier (ISIN, LEI) the cascade learned, and from which enricher;
    - ``done``: ``found_order`` (the enrichers found, as they answered), ``default_order`` (the order the asset's
      bindings would take: degree, then the price provider's enricher, then ``found_order``, then code) and
      ``identifiers`` (every identifier known at the end).

    ``seeds`` (ENR-2): bindings to start from, the asset's price assignment. The enricher of a seed's code is asked
    first with it, with the parameters it declares; a seed's identifier joins the cascade, a strong one different from
    the asset's is a ``conflict`` of that enricher.

    Counted once on the probe's per-user limit (plan C0), however many enrichers it asks: past it, 429 before any event.
    """
    enforce_probe_limit(current_user.id)
    return StreamingResponse(_recognize_events(request), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


def source_refused(code: str, refused: RateLimitedError) -> HTTPException:
    """The 429 ``RATE_LIMITED`` of a source that refused an enricher's call for too many requests, with ``Retry-After``
    (the source's wait, else a minute): a refusal is never an empty result (ENR-3b). Logged once, here."""
    seconds = refusal_wait(refused)
    logger.warning("Enricher source refused for too many requests", enricher=code, retry_after=seconds, exc_info=refused)
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"error_code": "RATE_LIMITED", "retry_after": seconds, "message": "The source refused for too many requests: try again later"},
        headers={"Retry-After": str(seconds)},
    )


@enricher_router.get(
    "/enrichers/{code}/search",
    response_model=List[FAEnricherSearchResult],
    tags=["FA Enrichers"],
    responses={429: {"description": "Too many probes by this user (`PROBE_RATE_LIMITED`), or the source refused the search for too many requests (`RATE_LIMITED`); both with `retry_after` and the `Retry-After` header"}},
)
async def search_enricher(code: str, q: str = Query(..., min_length=1, max_length=200), current_user: User = Depends(get_current_user)) -> List[FAEnricherSearchResult]:
    """One enricher's search by a word (the E7 window's «search»); 400 for an enricher that does not search; counted on the
    probe's per-user limit (plan C0). A source that refuses for too many requests answers 429 ``RATE_LIMITED`` with
    ``Retry-After`` (ENR-3b)."""
    enforce_probe_limit(current_user.id)
    plugin = await _enricher(code)
    if not plugin.supports_search:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"The enricher '{code}' does not search")
    try:
        results = await asyncio.to_thread(plugin.search, q)
    except RateLimitedError as refused:
        raise source_refused(code, refused) from refused
    return [_search_result(result) for result in results]


def _search_result(result: EnricherSearchResult) -> FAEnricherSearchResult:
    binding = FAEnricherBinding(identifier_type=result.binding.identifier_type, identifier=result.binding.identifier, **dict(result.binding.params))
    return FAEnricherSearchResult(name=result.name, binding=binding, asset_type=result.asset_type, page_url=result.page_url, market=result.market)


#: The most codes one search may name.
_MAX_SEARCH_CODES = 16


def _outcome_event(outcome: SearchOutcome) -> dict:
    return {
        "event": "enricher_results",
        "code": outcome.code,
        "status": outcome.status.value,
        "via": outcome.via.value if outcome.via is not None else None,
        "results": [_search_result(result).model_dump(mode="json") for result in outcome.results],
        "accepted_identifier_types": list(outcome.accepted_identifier_types),
        "retry_after": outcome.retry_after,
        "error_code": outcome.error_code,
    }


async def _search_events(text: str, codes: list[str], asset_type: Optional[AssetType]) -> AsyncIterator[str]:
    """The search across enrichers as Server-Sent Events: one ``enricher_results`` per code, then ``done``."""
    # Closed with the stream: a client that leaves stops the waiting for the calls in flight (ENR-3)
    async with aclosing(search_enrichers(text, codes, asset_type=asset_type)) as outcomes:
        async for outcome in outcomes:
            yield _sse(_outcome_event(outcome))
    yield _sse({"event": "done", "codes": codes})


@enricher_router.get(
    "/enrichers/search",
    tags=["FA Enrichers"],
    responses={
        200: {"description": "Server-Sent Events: `enricher_results` per enricher asked, then `done`", "content": {"text/event-stream": {}}},
        429: {"description": "Too many probes by this user (`PROBE_RATE_LIMITED`), before any event, with `retry_after` and the `Retry-After` header"},
    },
)
async def search_across_enrichers(
    q: str = Query(..., min_length=2, max_length=200, description="A name, an ISIN or a ticker"),
    codes: Optional[List[str]] = Query(None, description="Only these enrichers (repeat the key); every one served when absent"),
    asset_type: Optional[AssetType] = Query(None, description="The asset's type: only the enrichers that cover it; absent codes default to its default order"),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """«Cerca online» (ENR-3): ``q`` searched on several enrichers at once, as Server-Sent Events.

    Events, one ``data: {json}`` each, with an ``event`` key:

    - ``enricher_results``, one per enricher asked, as each answers: ``code``, ``status`` (``ok``, ``identifier_only``,
      ``rate_limited``, ``not_configured``, ``off``, ``not_covering``, ``error``), ``via`` (``search``, or
      ``recognize`` for an enricher without a search asked with an identifier of its type, R12), ``results``
      (``FAEnricherSearchResult``), ``accepted_identifier_types``, ``retry_after`` (seconds, on ``rate_limited``: the
      same wait as ``GET /enrichers/{code}/search``), ``error_code`` (on ``error``; the cause is in the server log);
    - ``done``: ``codes``, the enrichers asked, in order.

    Counted once on the probe's per-user limit (plan C0), however many enrichers it asks: past it, 429 before any event.
    422 for a text shorter than 2 characters once trimmed, more than 16 codes, or a code that is not an enricher code.
    """
    text = q.strip()
    if len(text) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The text to search needs at least 2 characters")
    if codes is not None and (len(codes) > _MAX_SEARCH_CODES or not all(ENRICHER_CODE.fullmatch(code) for code in codes)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"At most {_MAX_SEARCH_CODES} enricher codes")
    enforce_probe_limit(current_user.id)
    asked = asked_codes(codes, asset_type)
    return StreamingResponse(_search_events(text, asked, asset_type), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


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
    return FAEnricherRecognition(code=code, identifier_type=binding.identifier_type, identifier=binding.identifier, status=found.value, name=answer.name, page_url=answer.page_url, identifiers=dict(answer.identifiers or {}), params=dict(extra))
