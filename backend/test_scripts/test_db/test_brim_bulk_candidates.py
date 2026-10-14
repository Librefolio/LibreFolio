"""
Bulk candidate search — equivalence with the per-asset path (P3 / import performance).

``search_asset_candidates`` issues up to five queries per extracted asset, sequentially.
``search_asset_candidates_bulk`` fetches the superset once and classifies in memory, which
is the whole point: a thirty-instrument report went from a hundred-odd round-trips to one.

Classifying in memory means the matching predicates exist **twice** — once as SQL, once as
Python. That duplication is only safe if something proves the two agree, which is what
these tests are. Every case here is a shape the parser really produces:

- the dual-ISIN bond, with the placement ("CUM") code sitting in ``identifier_other``;
- a name carrying a ``%`` (``BTP Valore 3,35%``), where SQL ``LIKE`` reads the percent as a
  wildcard and a naive Python ``in`` would not — the single most likely way for the two
  paths to drift apart, and bond names are full of them;
- an extraction with no ISIN at all, which falls through to the name priorities;
- the same instrument extracted twice, which must collapse to one lookup.
"""

from __future__ import annotations

import uuid
from typing import List

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType
from backend.app.db.session import get_async_engine
from backend.app.schemas.brim import BRIMMatchConfidence
from backend.app.services.brim_provider import search_asset_candidates, search_asset_candidates_bulk


@pytest_asyncio.fixture
async def async_session():
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        yield session


@pytest_asyncio.fixture
async def candidate_assets(async_session: AsyncSession):
    """A small universe covering every priority the search can reach."""
    suffix = uuid.uuid4().hex[:6]
    assets = [
        Asset(
            display_name=f"BTP Piu Sc Fb33 {suffix}",
            asset_type=AssetType.BOND,
            currency="EUR",
            identifier_isin="IT0005634792",
            identifier_other=["IT0005634800", f"BTP FUT 16-11-33 CUM {suffix}"],
        ),
        Asset(
            display_name=f"BTP Valore 3,35% {suffix}",
            asset_type=AssetType.BOND,
            currency="EUR",
            identifier_isin="IT0005565515",
        ),
        Asset(
            display_name=f"Eurizon Azioni {suffix}",
            asset_type=AssetType.FUND,
            currency="EUR",
            identifier_ticker=f"EZA{suffix[:3].upper()}",
        ),
        Asset(
            display_name=f"Amundi MSCI World {suffix}",
            asset_type=AssetType.ETF,
            currency="EUR",
            identifier_isin="LU1681043599",
        ),
    ]
    async_session.add_all(assets)
    await async_session.commit()
    for a in assets:
        await async_session.refresh(a)
    ids = [a.id for a in assets]
    names = [a.display_name for a in assets]
    tickers = [a.identifier_ticker for a in assets]

    yield {"ids": ids, "names": names, "tickers": tickers, "suffix": suffix}

    for asset_id in ids:
        leftover = (await async_session.execute(select(Asset).where(Asset.id == asset_id))).scalars().first()
        if leftover:
            await async_session.delete(leftover)
    await async_session.commit()


def _shape(result):
    """Comparable projection: ids and confidences, order preserved."""
    candidates, auto = result
    return ([(c.asset_id, c.match_confidence) for c in candidates], auto)


@pytest.mark.asyncio
async def test_bulk_matches_per_asset_search(async_session: AsyncSession, candidate_assets):
    """The two paths must return the same candidates, in the same order, for every shape."""
    suffix = candidate_assets["suffix"]
    names = candidate_assets["names"]
    tickers = candidate_assets["tickers"]

    extractions = [
        # Priority 1: the quoted ISIN, straight on the primary column.
        (None, "IT0005634792", names[0]),
        # Priority 2: the placement ISIN, which lives among the alternates.
        (None, "IT0005634800", f"BTP FUT 16-11-33 CUM {suffix}"),
        # A percent sign in the name: SQL LIKE reads it as a wildcard.
        (None, None, f"BTP Valore 3,35% {suffix}"),
        # Priority 3: ticker only.
        (tickers[2], None, None),
        # Priority 4: name only, no code at all.
        (None, None, f"Amundi MSCI World {suffix}"),
        # Nothing should match.
        (None, "XX0000000000", f"Nonexistent {suffix}"),
        # The same instrument twice — must collapse, not duplicate.
        (None, "IT0005634792", names[0]),
    ]

    bulk = await search_asset_candidates_bulk(async_session, extractions)

    for symbol, isin, name in extractions:
        expected = await search_asset_candidates(
            session=async_session,
            extracted_symbol=symbol,
            extracted_isin=isin,
            extracted_name=name,
        )
        got = bulk[(symbol, isin, name)]
        assert _shape(got) == _shape(expected), f"divergence on {(symbol, isin, name)}"


@pytest.mark.asyncio
async def test_bulk_collapses_duplicate_extractions(async_session: AsyncSession, candidate_assets):
    """Distinct keys only: the same triple asked five times costs one classification."""
    triple = (None, "IT0005634792", candidate_assets["names"][0])
    bulk = await search_asset_candidates_bulk(async_session, [triple] * 5)
    assert len(bulk) == 1
    candidates, auto = bulk[triple]
    assert auto == candidate_assets["ids"][0]
    assert len(candidates) == 1


@pytest.mark.asyncio
async def test_bulk_finds_the_placement_isin_among_alternates(async_session: AsyncSession, candidate_assets):
    """The CUM code must resolve to the same asset as the quoted one — the P3 promise."""
    quoted = await search_asset_candidates_bulk(async_session, [(None, "IT0005634792", None)])
    placement = await search_asset_candidates_bulk(async_session, [(None, "IT0005634800", None)])
    assert quoted[(None, "IT0005634792", None)][1] == candidate_assets["ids"][0]
    assert placement[(None, "IT0005634800", None)][1] == candidate_assets["ids"][0]


@pytest.mark.asyncio
async def test_bulk_on_empty_input_is_a_no_op(async_session: AsyncSession):
    """No extractions, no query."""
    assert await search_asset_candidates_bulk(async_session, []) == {}


# =============================================================================
# Explicit invariants — one asset per test, not the shared `candidate_assets` universe.
#
# The frontend fix (`uniqueCandidateId` in importMerge.ts, formerly the buggy
# `uniqueExactCandidateId`) only makes sense if the backend it mirrors really does select
# on "one distinct candidate, any confidence" and reject "more than one distinct id" — and
# really does search inactive assets and alternates the same as primary/active ones. These
# three are exactly that, kept off the shared fixture above so as not to widen a universe
# every other case in this file also queries against.
# =============================================================================


@pytest_asyncio.fixture
async def solo_assets(async_session: AsyncSession):
    """Assets scoped to a single test — a factory, so each case creates only what it needs."""
    created: List[Asset] = []

    async def make(**kwargs) -> Asset:
        suffix = uuid.uuid4().hex[:6]
        kwargs.setdefault("display_name", f"Solo invariant asset {suffix}")
        kwargs.setdefault("currency", "EUR")
        kwargs.setdefault("asset_type", AssetType.BOND)
        asset = Asset(**kwargs)
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        created.append(asset)
        return asset

    yield make

    for asset in created:
        leftover = (await async_session.execute(select(Asset).where(Asset.id == asset.id))).scalars().first()
        if leftover:
            await async_session.delete(leftover)
    await async_session.commit()


@pytest.mark.asyncio
async def test_inactive_asset_is_still_a_candidate_and_still_auto_selects(async_session: AsyncSession, solo_assets):
    """Imports are retroactive by nature (final coupons, redemptions land on matured
    securities): the active filter must default to "both", not "active only"."""
    isin = f"IT{uuid.uuid4().hex[:10].upper()}"
    asset = await solo_assets(identifier_isin=isin, active=False)

    candidates, auto = await search_asset_candidates(session=async_session, extracted_symbol=None, extracted_isin=isin, extracted_name=None)
    assert [c.asset_id for c in candidates] == [asset.id]
    assert auto == asset.id

    bulk = await search_asset_candidates_bulk(async_session, [(None, isin, None)])
    bulk_candidates, bulk_auto = bulk[(None, isin, None)]
    assert [c.asset_id for c in bulk_candidates] == [asset.id]
    assert bulk_auto == asset.id


@pytest.mark.asyncio
async def test_primary_and_alternate_hit_on_the_same_asset_collapse_to_one_candidate(async_session: AsyncSession, solo_assets):
    """The same ISIN, primary column AND repeated in identifier_other on the SAME asset —
    e.g. a re-saved alternate that duplicates the quoted code. Deduplication is by asset id,
    so this must stay one candidate (EXACT, the stronger of the two hits), not two, and it
    must still auto-select: dedup, not ambiguity."""
    isin = f"IT{uuid.uuid4().hex[:10].upper()}"
    asset = await solo_assets(identifier_isin=isin, identifier_other=[isin])

    candidates, auto = await search_asset_candidates(session=async_session, extracted_symbol=None, extracted_isin=isin, extracted_name=None)
    assert len(candidates) == 1
    assert candidates[0].asset_id == asset.id
    assert candidates[0].match_confidence == BRIMMatchConfidence.EXACT
    assert auto == asset.id

    bulk = await search_asset_candidates_bulk(async_session, [(None, isin, None)])
    bulk_candidates, bulk_auto = bulk[(None, isin, None)]
    assert len(bulk_candidates) == 1
    assert bulk_candidates[0].match_confidence == BRIMMatchConfidence.EXACT
    assert bulk_auto == asset.id


@pytest.mark.asyncio
async def test_two_different_assets_sharing_one_isin_have_no_auto_select(async_session: AsyncSession, solo_assets):
    """The genuine ambiguity: the code is primary on one asset and an alternate on a
    DIFFERENT one. Candidates stay plural (both must be offered) and neither search path
    may auto-select — this is the "multiple -> null" half of the policy the frontend now
    mirrors regardless of the tier either candidate matched at."""
    isin = f"IT{uuid.uuid4().hex[:10].upper()}"
    primary = await solo_assets(identifier_isin=isin)
    alias = await solo_assets(identifier_other=[isin])

    candidates, auto = await search_asset_candidates(session=async_session, extracted_symbol=None, extracted_isin=isin, extracted_name=None)
    assert {c.asset_id for c in candidates} == {primary.id, alias.id}
    assert auto is None

    bulk = await search_asset_candidates_bulk(async_session, [(None, isin, None)])
    bulk_candidates, bulk_auto = bulk[(None, isin, None)]
    assert {c.asset_id for c in bulk_candidates} == {primary.id, alias.id}
    assert bulk_auto is None
