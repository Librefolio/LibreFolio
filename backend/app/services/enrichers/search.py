"""«Cerca online» (ENR-3): one text searched across several enrichers at once, their answers as they arrive.

The enrichers' window searches every enricher the asset does not have yet with what the user typed (a name, an ISIN,
a ticker). Each enricher answers on its own:

- one **with a search** (``supports_search``) runs it: its results, each a binding ready to add;
- one **without** (ESMA reads a register by ISIN, R12) is asked ``recognize`` only when the text has the form of an
  identifier type it accepts (``utils/asset/identifier_shape.py``: an ISIN or a LEI, check digits included): found, one
  result; otherwise it answers ``identifier_only``, with the types it accepts, and costs no call;
- a refusal for too many requests is ``rate_limited`` with the wait the enrichers' routes use (``refusal_wait``, the
  same as ``GET /enrichers/{code}/search``); any other failure is ``error`` with a code, its cause logged here, once,
  with the enricher's code (H-60); one enricher failing never stops the others;
- a code the instance does not serve is ``off``, one that does not cover the asset type ``not_covering``, one with a
  required setting empty ``not_configured``.

The plugin calls block: each runs in a worker thread (``asyncio.to_thread``), all at once, each behind its own pacer.
A reader that stops early (the client closed the stream) stops waiting for the calls still in flight: their tasks are
cancelled, nothing is left awaiting them.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from backend.app.db.models import AssetType
from backend.app.logging_config import get_logger
from backend.app.services.enrichers.base import EnricherBinding, EnricherPlugin, EnricherSearchResult
from backend.app.services.enrichers.bindings import default_order, installed_enrichers
from backend.app.services.enrichers.usable import configured_enricher
from backend.app.utils.asset.identifier_shape import IDENTIFIER_SHAPES
from backend.app.utils.runtime.cooldown import RateLimitedError

logger = get_logger(__name__)

#: The wait a source's refusal answers when the source named none: the per-user limit's window, a minute.
DEFAULT_REFUSAL_WAIT = 60
#: The code of an ``error`` answer: the client gets this, the cause goes to the log.
SOURCE_ERROR = "SOURCE_ERROR"


def refusal_wait(refused: RateLimitedError) -> int:
    """The wait, in whole seconds (at least 1), of a source's refusal: its own, rounded up, else a minute."""
    return max(1, math.ceil(refused.retry_after)) if refused.retry_after is not None else DEFAULT_REFUSAL_WAIT


class SearchStatus(StrEnum):
    OK = "ok"
    IDENTIFIER_ONLY = "identifier_only"
    RATE_LIMITED = "rate_limited"
    NOT_CONFIGURED = "not_configured"
    OFF = "off"
    NOT_COVERING = "not_covering"
    ERROR = "error"


class SearchVia(StrEnum):
    SEARCH = "search"
    RECOGNIZE = "recognize"


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    """One enricher's answer to a search."""

    code: str
    status: SearchStatus
    via: SearchVia | None = None
    results: list[EnricherSearchResult] = field(default_factory=list)
    accepted_identifier_types: tuple[str, ...] = ()
    retry_after: int | None = None
    error_code: str | None = None


def _shaped_type(plugin: EnricherPlugin, text: str) -> str | None:
    """The first type ``plugin`` accepts whose form ``text`` has (only the types whose form can be checked)."""
    for kind in plugin.accepted_identifier_types:
        check = IDENTIFIER_SHAPES.get(kind)
        if check is not None and check(text):
            return kind
    return None


def search_one(plugin: EnricherPlugin, text: str) -> SearchOutcome:
    """One enricher's answer to ``text`` (blocking: run it in a worker thread)."""
    accepted = tuple(plugin.accepted_identifier_types)
    try:
        if plugin.supports_search:
            return SearchOutcome(code=plugin.code, status=SearchStatus.OK, via=SearchVia.SEARCH, results=list(plugin.search(text)), accepted_identifier_types=accepted)
        kind = _shaped_type(plugin, text)
        if kind is None:
            return SearchOutcome(code=plugin.code, status=SearchStatus.IDENTIFIER_ONLY, accepted_identifier_types=accepted)
        binding = EnricherBinding(identifier_type=kind, identifier=text.strip().upper())
        answer = plugin.recognize(binding)
        results = [EnricherSearchResult(name=answer.name or binding.identifier, binding=binding, page_url=answer.page_url or plugin.page_url(binding))] if answer.found else []
        return SearchOutcome(code=plugin.code, status=SearchStatus.OK, via=SearchVia.RECOGNIZE, results=results, accepted_identifier_types=accepted)
    except RateLimitedError as refused:
        logger.warning("Enricher source refused the search for too many requests", enricher=plugin.code, retry_after=refused.retry_after, exc_info=refused)
        return SearchOutcome(code=plugin.code, status=SearchStatus.RATE_LIMITED, accepted_identifier_types=accepted, retry_after=refusal_wait(refused))
    except Exception as error:  # noqa: BLE001 — isolation boundary: one source failing is that source's answer
        logger.warning("Enricher search failed", enricher=plugin.code, exc_info=error)
        return SearchOutcome(code=plugin.code, status=SearchStatus.ERROR, accepted_identifier_types=accepted, error_code=SOURCE_ERROR)


def asked_codes(codes: Sequence[str] | None, asset_type: AssetType | None) -> list[str]:
    """The codes a search asks: the ones given (each once, in their order), else every enricher served (that covers
    ``asset_type``, when given), in the default order of that type."""
    if codes:
        return list(dict.fromkeys(codes))
    if asset_type is not None:
        return default_order(asset_type)
    return [plugin.code for plugin in installed_enrichers()]


async def search_enrichers(text: str, codes: Sequence[str], *, asset_type: AssetType | None = None) -> AsyncIterator[SearchOutcome]:
    """Search ``text`` on the enrichers of ``codes``: their answers as they arrive (see the module docstring)."""
    tasks: dict[asyncio.Task, str] = {}
    try:
        for code in codes:
            plugin, missing = await configured_enricher(code)
            if plugin is None:
                yield SearchOutcome(code=code, status=SearchStatus.OFF)
                continue
            accepted = tuple(plugin.accepted_identifier_types)
            if asset_type is not None and not plugin.covers(asset_type):
                yield SearchOutcome(code=code, status=SearchStatus.NOT_COVERING, accepted_identifier_types=accepted)
                continue
            if missing:
                yield SearchOutcome(code=code, status=SearchStatus.NOT_CONFIGURED, accepted_identifier_types=accepted)
                continue
            tasks[asyncio.create_task(asyncio.to_thread(search_one, plugin, text))] = code
        pending = set(tasks)
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                yield task.result()
    finally:
        # A reader that stops early: stop waiting for the calls in flight (their threads end on their own)
        for task in tasks:
            if not task.done():
                task.cancel()
