"""BRIM asset candidates: for the assets a report names, the assets of the database that may be the same one."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

import structlog
from sqlalchemy import String, cast, or_, select

from backend.app.db.models import Asset
from backend.app.schemas.assets.assets import FAAinfoFiltersRequest
from backend.app.schemas.brim import (
    BRIMAssetCandidate,
    BRIMMatchConfidence,
)
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.utils.sql_chunks import chunks

logger = structlog.get_logger(__name__)


async def search_asset_candidates(  # noqa: C901 — flat priority fallback chain, sequential guards only
    session,
    extracted_symbol: Optional[str],
    extracted_isin: Optional[str],
    extracted_name: Optional[str],
) -> Tuple[List, Optional[int]]:
    """
    Search for asset candidates in the database.

    Uses FAAinfoFiltersRequest to search directly on Asset identifier columns.
    Returns candidates with confidence levels and auto-selects if exactly 1 match.

    Priority:
    1. ISIN exact match on ``Asset.identifier_isin`` → EXACT confidence
    2. ISIN found in the ``Asset.identifier_other`` JSON list → HIGH confidence
    3. Symbol exact match on ``Asset.identifier_ticker`` → MEDIUM confidence
    4. Name partial match (identifier, then ``display_name``) → LOW confidence
    5. Name found in the ``Asset.identifier_other`` JSON list → LOW confidence

    Steps 1 and 2 run **together** and their results are merged (deduplicated by
    ``asset_id``, strongest confidence wins). An ISIN stored in ``identifier_other``
    is a deliberate user assertion — typically the non-tradeable "CUM" ISIN of an
    Italian BTP, kept alongside the quoted one — so it must outrank any name
    similarity. Previously it was evaluated last and only when nothing else had
    matched, meaning a vaguely plausible name hit silently shadowed it.

    Running both also surfaces duplicates: if the same ISIN is primary on one asset
    and alternate on another, the user sees **both** candidates and can merge them.

    Args:
        session: AsyncSession for database queries
        extracted_symbol: Symbol/ticker from import file
        extracted_isin: ISIN from import file
        extracted_name: Asset name from import file

    Returns:
        Tuple of (candidates list, auto_selected_id)
        - If exactly 1 candidate: auto_selected_id = that asset's ID
        - Otherwise: auto_selected_id = None
    """
    candidates: List[BRIMAssetCandidate] = []
    by_id: dict = {}

    def _add(asset, confidence: BRIMMatchConfidence) -> None:
        """Append a candidate, keeping the strongest confidence per asset."""
        _add_candidate(candidates, by_id, asset, confidence)

    # Priority 1: ISIN exact match on the primary column (EXACT confidence).
    if extracted_isin:
        results = await AssetCRUDService.list_assets(filters=FAAinfoFiltersRequest(isin=extracted_isin), session=session)
        for asset in results:
            _add(asset, BRIMMatchConfidence.EXACT)

    # Priority 2: ISIN stored among the alternate identifiers (HIGH confidence).
    # Deliberately NOT guarded by `if not candidates` — see the docstring.
    if extracted_isin:
        results = await AssetCRUDService.list_assets(filters=FAAinfoFiltersRequest(identifier_other=extracted_isin), session=session)
        for asset in results:
            _add(asset, BRIMMatchConfidence.HIGH)

    # Priority 3: Symbol exact match (MEDIUM confidence)
    if extracted_symbol and not candidates:
        results = await AssetCRUDService.list_assets(filters=FAAinfoFiltersRequest(ticker=extracted_symbol), session=session)
        for asset in results:
            _add(asset, BRIMMatchConfidence.MEDIUM)

    # Priority 4: Name partial match (LOW confidence)
    if extracted_name and not candidates:
        # Try identifier partial match first
        results = await AssetCRUDService.list_assets(filters=FAAinfoFiltersRequest(identifier_contains=extracted_name), session=session)
        if not results:
            # Fall back to display_name search
            results = await AssetCRUDService.list_assets(filters=FAAinfoFiltersRequest(search=extracted_name), session=session)
        for asset in results:
            _add(asset, BRIMMatchConfidence.LOW)

    # Priority 5: Soft broker label match against identifier_other (LOW confidence).
    # Catches assets whose soft label (e.g. "BTP 1/12/2026 1.25%") was saved on a
    # previous import. Still a last resort: a name is far weaker evidence than an ISIN.
    if extracted_name and not candidates:
        results = await AssetCRUDService.list_assets(filters=FAAinfoFiltersRequest(identifier_other=extracted_name), session=session)
        for asset in results:
            _add(asset, BRIMMatchConfidence.LOW)

    # Auto-select if exactly 1 candidate found
    auto_selected = candidates[0].asset_id if len(candidates) == 1 else None

    return candidates, auto_selected


# Strongest first — used to decide whether a later, weaker match may override.
_CONFIDENCE_RANK = {
    BRIMMatchConfidence.EXACT: 0,
    BRIMMatchConfidence.HIGH: 1,
    BRIMMatchConfidence.MEDIUM: 2,
    BRIMMatchConfidence.LOW: 3,
}


def _add_candidate(candidates: List, by_id: dict, asset, confidence: BRIMMatchConfidence) -> None:
    """Append a candidate, keeping the strongest confidence per asset."""
    existing = by_id.get(asset.id)
    if existing is not None:
        if _CONFIDENCE_RANK[confidence] < _CONFIDENCE_RANK[existing.match_confidence]:
            existing.match_confidence = confidence
        return
    candidate = BRIMAssetCandidate(
        asset_id=asset.id,
        symbol=asset.identifier_ticker,
        isin=asset.identifier_isin,
        name=asset.display_name,
        match_confidence=confidence,
    )
    by_id[asset.id] = candidate
    candidates.append(candidate)


def _like_to_regex(pattern: str) -> re.Pattern[str]:
    """
    Reproduce SQL ``LIKE`` semantics in Python, wildcards included.

    Needed because the bulk path fetches once and classifies in memory: if the two
    paths disagreed on what "matches" means, the same file would produce different
    candidates depending on which function ran. Bond names are exactly where this
    bites — ``BTP Valore 3,35%`` contains a ``%``, which SQL reads as *anything*.
    """
    out = ["^"]
    for ch in pattern:
        if ch == "%":
            out.append(".*")
        elif ch == "_":
            out.append(".")
        else:
            out.append(re.escape(ch))
    out.append("$")
    return re.compile("".join(out), re.IGNORECASE | re.DOTALL)


def _other_as_text(value: Optional[List[str]]) -> str:
    """
    Render ``identifier_other`` the way ``cast(col, String)`` sees it in SQL.

    The column is a JSON list, and the SQL filter substring-matches its serialised
    text. Codes and labels never straddle the separators, so reproducing the JSON
    dump is enough to keep the two paths in agreement.
    """
    if not value:
        return ""
    return json.dumps(value)


def _contains_matcher(needle: str) -> Callable[[Optional[str]], bool]:
    """SQL ``ilike('%needle%')`` as a test of one text — wildcards inside *needle* are honoured. Compiled once per needle
    (MF-SEC9g): the bulk classification tests it against every candidate of the universe."""
    pattern = _like_to_regex(f"%{needle}%")
    return lambda haystack: bool(haystack) and pattern.match(haystack) is not None


class _CandidateView(NamedTuple):
    """What the bulk classification reads of one stored asset, read once off the ORM object (MF-SEC9g): the thread that
    classifies never touches the session or a lazy attribute. ``_add_candidate`` reads ``id``, ``identifier_ticker``,
    ``identifier_isin`` and ``display_name``; ``name_fields`` are the identifier texts the name is matched against, in the
    per-asset path's order, ``identifier_other`` as SQL's cast sees it."""

    id: int
    display_name: str
    identifier_isin: Optional[str]
    identifier_ticker: Optional[str]
    other_text: str
    name_fields: Tuple[Optional[str], ...]


def _candidate_view(asset) -> _CandidateView:
    other_text = _other_as_text(asset.identifier_other)
    return _CandidateView(
        id=asset.id,
        display_name=asset.display_name,
        identifier_isin=asset.identifier_isin,
        identifier_ticker=asset.identifier_ticker,
        other_text=other_text,
        name_fields=(asset.identifier_isin, asset.identifier_ticker, asset.identifier_cusip, asset.identifier_sedol, asset.identifier_figi, asset.identifier_uuid, other_text),
    )


def _classify_candidates(  # noqa: C901 — flat priority chain over the universe; mirrors search_asset_candidates
    unique: List[Tuple[Optional[str], Optional[str], Optional[str]]],
    universe: List[_CandidateView],
) -> Dict[Tuple[Optional[str], Optional[str], Optional[str]], Tuple[List, Optional[int]]]:
    """The per-asset path's five-step priority, in memory, for every distinct extraction (``search_asset_candidates_bulk``).

    Pure CPU over plain views, run in a worker thread (MF-SEC9g): over a large universe with generic names it took
    seconds to minutes, on the event loop. The exact ISIN and ticker steps read an index that keeps the universe's order;
    each needle's LIKE pattern is compiled once, and each asset's ``identifier_other`` text is built once.
    """
    by_isin: Dict[str, List[_CandidateView]] = {}
    by_ticker: Dict[str, List[_CandidateView]] = {}
    for view in universe:
        by_isin.setdefault(view.identifier_isin or "", []).append(view)
        by_ticker.setdefault(view.identifier_ticker or "", []).append(view)

    out: Dict[Tuple[Optional[str], Optional[str], Optional[str]], Tuple[List, Optional[int]]] = {}
    for symbol, isin, name in unique:
        candidates: List[BRIMAssetCandidate] = []
        by_id: dict = {}

        def _add(view: _CandidateView, confidence: BRIMMatchConfidence, _c=candidates, _b=by_id) -> None:
            _add_candidate(_c, _b, view, confidence)

        # Priority 1 + 2: the ISIN, primary column then alternates. Run together and
        # merged, exactly as in the per-asset path — see its docstring for why.
        if isin:
            for view in by_isin.get(isin.upper(), ()):
                _add(view, BRIMMatchConfidence.EXACT)
            isin_in = _contains_matcher(isin)
            for view in universe:
                if isin_in(view.other_text):
                    _add(view, BRIMMatchConfidence.HIGH)

        # Priority 3: ticker.
        if symbol and not candidates:
            for view in by_ticker.get(symbol.upper(), ()):
                _add(view, BRIMMatchConfidence.MEDIUM)

        # Priority 4: the name, across identifiers first and display name second.
        name_in = _contains_matcher(name) if name else None
        if name_in is not None and not candidates:
            hits = [view for view in universe if any(name_in(field) for field in view.name_fields)]
            if not hits:
                hits = [view for view in universe if name_in(view.display_name)]
            for view in hits:
                _add(view, BRIMMatchConfidence.LOW)

        # Priority 5: the soft broker label saved on a previous import.
        if name_in is not None and not candidates:
            for view in universe:
                if name_in(view.other_text):
                    _add(view, BRIMMatchConfidence.LOW)

        out[(symbol, isin, name)] = (candidates, candidates[0].asset_id if len(candidates) == 1 else None)
    return out


async def search_asset_candidates_bulk(
    session,
    extractions: List[Tuple[Optional[str], Optional[str], Optional[str]]],
) -> Dict[Tuple[Optional[str], Optional[str], Optional[str]], Tuple[List, Optional[int]]]:
    """
    Candidate search for many extracted assets in **one** database round-trip (one per ``OR_TERMS_PER_QUERY``
    conditions, MF-SEC9a: a usual report needs one).

    ``search_asset_candidates`` issues up to five queries per extracted asset. A
    Crédit Agricole report with thirty instruments therefore spent a hundred-odd
    sequential round-trips inside a single request, one waiting for the previous —
    latency that is entirely structural, not work.

    Here the superset of possibly-relevant assets is fetched once with the union of
    every condition, and the *same* five-step priority is then applied in memory,
    per extraction (``_classify_candidates``), in a worker thread: over a large universe
    with generic names it ran for seconds to minutes on the event loop (MF-SEC9g). The
    classification logic is duplicated on purpose rather than approximated:
    ``test_brim_bulk_candidates.py`` and ``test_bulk_reads_chunked.py`` assert the two
    functions agree row by row, which is what makes the duplication safe to keep.

    Args:
        session: AsyncSession for the query (one per chunk of conditions).
        extractions: ``(symbol, isin, name)`` triples, duplicates allowed.

    Returns:
        Mapping from each distinct triple to ``(candidates, auto_selected_id)``.
    """
    unique: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []
    seen: set = set()
    for triple in extractions:
        if triple in seen:
            continue
        seen.add(triple)
        unique.append(triple)

    if not unique:
        return {}

    # One query, the union of every condition the per-asset path would have issued.
    conditions = []
    for symbol, isin, name in unique:
        if isin:
            conditions.append(Asset.identifier_isin == isin.upper())
            conditions.append(cast(Asset.identifier_other, String).like(f"%{isin}%"))
        if symbol:
            conditions.append(Asset.identifier_ticker == symbol.upper())
        if name:
            pattern = f"%{name}%"
            # One condition per column, not a nested or_(): SQLAlchemy writes a nested OR out flat, so SQLite counts each
            # of them, and the chunks below must count what SQLite counts
            conditions.extend(
                (
                    Asset.identifier_isin.ilike(pattern),
                    Asset.identifier_ticker.ilike(pattern),
                    Asset.identifier_cusip.ilike(pattern),
                    Asset.identifier_sedol.ilike(pattern),
                    Asset.identifier_figi.ilike(pattern),
                    Asset.identifier_uuid.ilike(pattern),
                    cast(Asset.identifier_other, String).like(pattern),
                )
            )
            conditions.append(Asset.display_name.ilike(pattern))

    # One query per chunk of conditions (MF-SEC9a): SQLite refuses an OR of a thousand terms, and a report with about
    # ninety distinct securities, each with ISIN, ticker and name (11 terms), has that many. Merged by id, then in the
    # per-asset path's order, so the candidate lists come out identical: display_name is unique and never null, and
    # SQLite orders text by code point, as Python does.
    universe_by_id: Dict[int, Asset] = {}
    for chunk in chunks(conditions):
        result = await session.execute(select(Asset).where(or_(*chunk)))
        for asset in result.scalars().unique().all():
            universe_by_id.setdefault(asset.id, asset)
    universe = sorted(universe_by_id.values(), key=lambda asset: asset.display_name)

    # The classification off the event loop (MF-SEC9g): plain views, read here from the loaded objects, go to a thread
    views = [_candidate_view(asset) for asset in universe]
    return await asyncio.to_thread(_classify_candidates, unique, views)
