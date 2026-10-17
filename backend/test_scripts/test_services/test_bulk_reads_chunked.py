"""MF-SEC9a (rest) — the bulk reads of the BRIM candidate search and of the WAC FX evidence run in statements SQLite can
parse, and answer exactly what the one-statement read answered.

The defect, on HEAD d63558abb. SQLite parses ``a OR b OR c …`` as a chain one level deeper per term and refuses a chain
of a thousand («Expression tree is too large (maximum depth 1000)»). Two more reads had one OR term per item:

- ``brim_provider.search_asset_candidates_bulk`` read the universe of every extracted asset in ONE statement: per
  distinct ``(symbol, isin, name)`` triple the ISIN's equality and ``identifier_other LIKE``, the ticker's equality, the
  name's ILIKE on each of the seven identifier columns and on ``display_name``: 11 OR terms per security with all three
  fields, so from 91 such securities (1 001 terms) the import's candidate step raised ``OperationalError``;
- ``pac_allocator/source/wac._load_wac_fx_rows`` read the saved FX row of every ``(base, quote, date)`` key the average
  cost used in ONE statement: weekly foreign buys over twenty years are a thousand keys.

SQLAlchemy renders a nested OR flat (``x OR (y OR z)`` is ``x OR y OR z``), so SQLite counts each of the name's seven
identifier ILIKEs as a term of the chain: chunked as one nested condition, a chunk of 500 conditions would still be up to
1 100 terms (isin+symbol+name) or 2 000 (names only). The cure gives each ILIKE its own condition, so a chunk counts
what SQLite counts; ``test_barrier_a_nested_or_counts_every_term`` pins why.

The cure's contract, pinned here:

1. ``search_asset_candidates_bulk`` over a report past SQLite's limit — 100 distinct triples with ISIN, symbol and name
   (1 100 OR terms, the first size past E's measured threshold of 91), 300 such triples (3 300 OR terms), and 150 with a
   name only (1 200 OR terms) — raises nothing, answers each distinct triple
   once (duplicates in the input collapse), and for every triple the very answer of the per-asset reference
   ``search_asset_candidates`` on the same session: candidate ids, confidences, their order, ``auto_selected_id``. The
   fixture reaches every priority (EXACT, HIGH by alternate ISIN, MEDIUM by ticker, LOW by name, by soft label),
   triples that match nothing, a primary ISIN that is another asset's alternate, and name hits spanning ASCII upper and
   lower case, Latin, Greek and CJK display names — ordered by code point by SQL and by Python alike; asset ids are
   assigned in shuffled order, so an order by id would show.
2. ``_load_wac_fx_rows`` with 1 500 stored keys over five pairs and 10 keys with no row answers exactly the stored keys,
   each with its own row (id, rate, source); the stored rows nobody asked for stay out.

The WAC case also runs at 500 and 501 keys, the edge of one chunk; the candidate search at 50 and 90 triples (550 and
990 OR terms), under SQLite's limit — 90 the last size HEAD answered. The barriers prove the SQLite these tests run on answers one OR of 500 terms and refuses one of
1 500: without them a build with a higher limit would let the import-sized cases pass untested.

Red on HEAD d63558abb:

- ``test_bulk_candidates_of_an_import_match_the_per_asset_search[100-triples-isin-symbol-name]``,
  ``[300-triples-isin-symbol-name]`` and ``[150-triples-name-only]``: ``OperationalError``, «Expression tree is too
  large»;
- ``test_wac_fx_rows_reads_every_key_of_a_long_history[1510-import-sized]``: the same.

Green before and after (guards): both barriers; ``test_guard_bulk_candidates_in_one_statement_match_the_per_asset_search``
(50 and 90 triples); the WAC case at 500 and 501 keys. «No key, no statement» is pinned by
``test_portfolio_allocation_source.py::test_wac_fx_rows_are_read_at_exactly_the_rate_date_the_cost_used``.

Isolation: PURE — no lane database, no server, no network. Each test has its own in-memory SQLite database
(``SQLModel.metadata.create_all``), closed and disposed at teardown.

Reference: backend/app/utils/sql_chunks.py, backend/app/services/brim/brim_provider.py (search_asset_candidates,
search_asset_candidates_bulk), backend/app/services/pac_allocator/source/wac.py (_load_wac_fx_rows),
backend/test_scripts/test_db/test_brim_bulk_candidates.py (the same parity on a small universe).
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import String, and_, cast, insert, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, FxRate
from backend.app.schemas.brim import BRIMMatchConfidence
from backend.app.services.brim import brim_provider
from backend.app.services.pac_allocator.source import wac as source_wac
from backend.test_scripts.test_utils import print_section, print_success

CHUNK = 500  # OR_TERMS_PER_QUERY: the contract's number, written here and not read from the module under test
IMPORT_SIZED = 1_500  # OR terms of one import-sized read: past SQLite's limit, past two chunk boundaries
SQLITE_MAX_DEPTH = 1_000  # SQLite's SQLITE_MAX_EXPR_DEPTH: an OR chain of this many terms is refused
DAY0 = date(2004, 1, 5)  # the first day of every FX series; any day would do
FETCHED_AT = datetime(2025, 1, 1)

Triple = tuple[Optional[str], Optional[str], Optional[str]]


def _day(offset: int) -> date:
    return DAY0 + timedelta(days=offset)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """This test's own in-memory database with the ORM schema: never the lane's database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as private_session:
            yield private_session
    finally:
        await engine.dispose()


# =============================================================================
# THE BARRIERS: THIS SQLITE ANSWERS ONE OR OF 500 TERMS AND REFUSES ONE OF 1 500 — NESTED ORS COUNTED
# =============================================================================


def _one_or_of_fx_keys(terms: int):
    return select(FxRate.id).where(or_(*(and_(FxRate.base == "EUR", FxRate.quote == "USD", FxRate.date == _day(offset)) for offset in range(terms))))


def _candidate_conditions(triples: list[Triple]) -> list:
    """The conditions of the candidate search, one list entry per condition: written here, as the contract has them."""
    conditions = []
    for symbol, isin, name in triples:
        if isin:
            conditions.append(Asset.identifier_isin == isin.upper())
            conditions.append(cast(Asset.identifier_other, String).like(f"%{isin}%"))
        if symbol:
            conditions.append(Asset.identifier_ticker == symbol.upper())
        if name:
            pattern = f"%{name}%"
            identifier_columns = (Asset.identifier_isin, Asset.identifier_ticker, Asset.identifier_cusip, Asset.identifier_sedol, Asset.identifier_figi, Asset.identifier_uuid)
            conditions.append(or_(*(column.ilike(pattern) for column in identifier_columns), cast(Asset.identifier_other, String).like(pattern)))
            conditions.append(Asset.display_name.ilike(pattern))
    return conditions


@pytest.mark.asyncio
async def test_barrier_this_sqlite_refuses_one_or_of_1500_terms(session):
    """Barrier: one statement with an OR of 500 FX keys, a chunk, is answered; one of 1 500, the shape before the cure,
    is refused «Expression tree is too large».

    Green before and after: it tests SQLite, so that «no raise» in the import-sized cases means the chunks.
    """
    print_section("MF-SEC9a barrier: one OR of 500 terms, then of 1 500")
    result = await session.execute(_one_or_of_fx_keys(CHUNK))
    assert result.all() == []

    with pytest.raises(OperationalError, match="Expression tree is too large"):
        await session.execute(_one_or_of_fx_keys(IMPORT_SIZED))
    print_success("500 terms answered; 1 500 refused, Expression tree is too large")


@pytest.mark.asyncio
async def test_barrier_a_nested_or_counts_every_term(session):
    """Barrier: the name's seven identifier ILIKEs are one *condition* but seven *terms* — SQLAlchemy renders the nested
    OR flat. 50 isin+symbol+name triples (250 conditions, 550 terms) are answered in one statement; 100 (500 conditions,
    one chunk if conditions were counted, 1 100 terms) are refused.

    Green before and after: it tests SQLAlchemy and SQLite. It is why the import-sized candidate cases count terms.
    """
    print_section("MF-SEC9a barrier: 500 candidate conditions are 1 100 OR terms")
    triples: list[Triple] = [(f"SYM{index:04d}", f"QQ{index:010d}", f"Barrier name {index:04d}") for index in range(100)]

    assert (await session.execute(select(Asset.id).where(or_(*_candidate_conditions(triples[:50]))))).all() == []

    conditions = _candidate_conditions(triples)
    assert len(conditions) == CHUNK
    with pytest.raises(OperationalError, match="Expression tree is too large"):
        await session.execute(select(Asset.id).where(or_(*conditions)))
    print_success("550 terms answered; 500 conditions (1 100 terms) refused, Expression tree is too large")


# =============================================================================
# 1. search_asset_candidates_bulk() == search_asset_candidates(), past a chunk boundary
# =============================================================================

#: Display-name prefixes: ASCII upper and lower case, Latin with diacritics, a ``%`` (a LIKE wildcard), Greek, CJK.
#: A query changes only the ASCII letters' case: SQLite folds ASCII alone, Python's IGNORECASE folds every script, and
#: an asymmetry there would be an older divergence than the one under test.
PREFIXES = (
    "Alpha Fund",
    "alpha bond",
    "Zeta ETF",
    "zürich Re",
    "Ångström Tech",
    "Œuvre Capital",
    "BTP Valore 3,35%",
    "Ελληνικά Ομόλογα",
    "Société Générale",
    "東京 Equity",
)
N_ASSETS = 300
SHARED_ISIN_HOLDER = 299  # its alternate ISIN is asset 1's primary one: a duplicate the user must see as two candidates
#: Name fragments matching ten assets of every prefix: lists in code-point order across scripts and cases. No index of
#: their ranges is a multiple of 25, so no soft label (``SOFT LABEL 0nnn``) holds them and the display names decide.
CROSS_PREFIX_NAMES = (" 013", " 004", " 028")


def _display_name(index: int) -> str:
    return f"{PREFIXES[index % len(PREFIXES)]} {index:04d}"


def _isin(index: int) -> Optional[str]:
    return None if index % 11 == 5 else f"XS{index:010d}"


def _ticker(index: int) -> Optional[str]:
    return None if index % 7 == 3 else f"TK{index:04d}"


def _alternate_isin(index: int) -> str:
    return f"XA{index:010d}"


def _soft_label(index: int) -> str:
    return f"SOFT LABEL {index:04d}"


def _other(index: int) -> Optional[list[str]]:
    if index == SHARED_ISIN_HOLDER:
        return [_isin(1)]
    if index % 25 == 0:
        return [_alternate_isin(index), _soft_label(index)]
    return None


def _ascii_swapcase(text: str) -> str:
    return "".join(char.swapcase() if char.isascii() else char for char in text)


async def _seed_assets(session: AsyncSession) -> None:
    """300 assets, inserted in shuffled order: ids do not follow display names, so a list in id order would show."""
    order = list(range(N_ASSETS))
    random.Random(9).shuffle(order)
    session.add_all(
        Asset(
            display_name=_display_name(index),
            currency="EUR",
            asset_type=AssetType.STOCK,
            identifier_isin=_isin(index),
            identifier_ticker=_ticker(index),
            identifier_other=_other(index),
        )
        for index in order
    )
    await session.commit()


def _full_triples(count: int) -> list[Triple]:
    """``count`` distinct (symbol, isin, name) triples, every field set: five conditions each, eleven OR terms."""
    specials: list[Triple] = [(f"NOSYM{index:04d}", _alternate_isin(index), f"Nothing alt {index:04d}") for index in range(0, N_ASSETS, 25)]  # HIGH
    specials.append(("NOSYM-SHARED", _isin(1), "Nothing shared"))  # EXACT on asset 1 and HIGH on the holder: two candidates
    specials.append(("NOSYM-SOFT", "ZZSOFT000050", _soft_label(50).lower()))  # LOW by soft label
    triples: list[Triple] = []
    for k in range(count - len(specials)):
        index = (k * 37) % N_ASSETS
        unknown_symbol, unknown_isin, unknown_name = f"NO{k:04d}", f"ZZ{k:010d}", f"Nothing {k:04d}"
        kind = k % 6
        if kind == 0:  # by ISIN, sometimes lower case; an asset without one falls through to its ticker, then its name
            isin = _isin(index) or unknown_isin
            triples.append((_ticker(index) or unknown_symbol, isin.lower() if k % 4 == 0 else isin, _display_name(index)))
        elif kind == 1:  # by ticker, lower case
            triples.append(((_ticker(index) or unknown_symbol).lower(), unknown_isin, unknown_name))
        elif kind == 2:  # by a name fragment ten assets share, across every prefix
            triples.append((unknown_symbol, unknown_isin, CROSS_PREFIX_NAMES[k % len(CROSS_PREFIX_NAMES)]))
        elif kind == 3:  # by one prefix's group, its ASCII case swapped
            triples.append((unknown_symbol, unknown_isin, _ascii_swapcase(f"{PREFIXES[k % len(PREFIXES)]} 0{k % 3}")))
        elif kind == 4:  # by the whole display name, its ASCII case swapped
            triples.append((unknown_symbol, unknown_isin, _ascii_swapcase(_display_name(index))))
        else:  # by nothing at all
            triples.append((unknown_symbol, unknown_isin, unknown_name))
    triples = specials[:1] + triples + specials[1:]  # specials on both sides of every chunk boundary
    assert len(set(triples)) == count, "the fixture's triples are distinct"
    return triples


def _name_only_triples(count: int) -> list[Triple]:
    """``count`` distinct name-only triples: two conditions each, eight OR terms."""
    triples: list[Triple] = [(None, None, name) for name in CROSS_PREFIX_NAMES]
    triples += [(None, None, _soft_label(index).lower()) for index in range(0, N_ASSETS, 25)]
    k = 0
    while len(triples) < count:
        index = (k * 41) % N_ASSETS
        triples.append((None, None, _ascii_swapcase(_display_name(index)) if k % 3 else f"Nothing only {k:04d}"))
        k += 1
    assert len(set(triples)) == count, "the fixture's triples are distinct"
    return triples


def _or_terms(triples: list[Triple]) -> int:
    """OR terms of one statement holding every condition: 2 per ISIN, 1 per symbol, 8 per name (7 identifiers + display)."""
    return sum(2 * bool(isin) + bool(symbol) + 8 * bool(name) for symbol, isin, name in triples)


def _shape(answer) -> tuple[list[tuple[int, BRIMMatchConfidence]], Optional[int]]:
    """Comparable projection: candidate ids and confidences, order preserved, and the auto-selected id."""
    candidates, auto_selected = answer
    return [(candidate.asset_id, candidate.match_confidence) for candidate in candidates], auto_selected


async def _assert_bulk_matches_per_asset(session: AsyncSession, triples: list[Triple]) -> dict[Triple, tuple]:
    """Duplicates in the input, then the bulk search compared triple by triple with the per-asset reference.

    Returns the reference's answers, by triple, for the coverage checks.
    """
    extractions = triples + triples[::7]  # every seventh triple asked twice, at the end
    try:
        bulk = await brim_provider.search_asset_candidates_bulk(session, extractions)
    except OperationalError as error:
        pytest.fail(f"search_asset_candidates_bulk raised for {len(triples)} triples ({_or_terms(triples)} OR terms), SQLite refusing the statement: {error.orig!r} (MF-SEC9a)")

    assert set(bulk) == set(triples), f"one answer per distinct triple: {len(bulk)} for {len(triples)}"

    expected: dict[Triple, tuple] = {}
    divergences = []
    for symbol, isin, name in triples:
        reference = _shape(await brim_provider.search_asset_candidates(session, symbol, isin, name))
        expected[(symbol, isin, name)] = reference
        got = _shape(bulk[(symbol, isin, name)])
        if got != reference:
            divergences.append(((symbol, isin, name), got, reference))
    assert not divergences, f"{len(divergences)} of {len(triples)} triples diverge from search_asset_candidates (triple, bulk, per-asset): {divergences[:3]}"
    return expected


def _assert_every_priority_reached(expected: dict[Triple, tuple], names_by_id: dict[int, str]) -> None:
    """The parity is not vacuous: the reference's answers reach every priority, empties, and multi-script lists."""
    confidences = {confidence for candidates, _ in expected.values() for _, confidence in candidates}
    assert confidences == set(BRIMMatchConfidence), f"every confidence reached: {sorted(confidences)}"
    assert any(not candidates for candidates, _ in expected.values()), "a triple matching nothing"
    assert any(auto is not None for _, auto in expected.values()), "a triple auto-selected"
    first_letters = [{names_by_id[asset_id][0] for asset_id, _ in candidates} for candidates, _ in expected.values()]
    assert any({"A", "a", "Å", "Ε", "東"} <= letters for letters in first_letters), "a list spanning ASCII cases, Latin, Greek and CJK"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("shape", "count"),
    [
        pytest.param("isin-symbol-name", 100, id="100-triples-isin-symbol-name"),
        pytest.param("isin-symbol-name", 300, id="300-triples-isin-symbol-name"),
        pytest.param("name-only", 150, id="150-triples-name-only"),
    ],
)
async def test_bulk_candidates_of_an_import_match_the_per_asset_search(session, shape, count):
    """A report past SQLite's limit: no «Expression tree is too large», and for every distinct triple the per-asset
    answer — candidate ids, confidences, order, auto-selection — past every chunk boundary.

    11 OR terms per triple with every field: 100 triples are 1 100, just past the 91 at which HEAD failed; 300 are 3 300.
    150 name-only triples are 1 200 (8 each), though only 300 conditions were they chunked as one nested OR per name.
    Red on HEAD d63558abb: ``OperationalError``.
    """
    print_section(f"MF-SEC9a: bulk candidates of {count} {shape} triples == per-asset search")
    await _seed_assets(session)
    names_by_id = dict((await session.execute(select(Asset.id, Asset.display_name))).tuples().all())
    triples = _full_triples(count) if shape == "isin-symbol-name" else _name_only_triples(count)
    assert _or_terms(triples) > SQLITE_MAX_DEPTH, "past SQLite's limit, the case this test exists for"

    expected = await _assert_bulk_matches_per_asset(session, triples)
    if shape == "isin-symbol-name":
        _assert_every_priority_reached(expected, names_by_id)
    print_success(f"{count} triples ({_or_terms(triples)} OR terms): no refusal, every answer the per-asset one")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count",
    [
        pytest.param(50, id="50-triples-550-terms"),
        pytest.param(90, id="90-triples-990-terms"),
    ],
)
async def test_guard_bulk_candidates_in_one_statement_match_the_per_asset_search(session, count):
    """Guard: triples with every field under SQLite's limit — 50 (550 OR terms) and 90 (990, the last size HEAD
    answered) — which HEAD read in one statement, with the same per-asset parity. Green before and after.
    """
    print_section(f"MF-SEC9a guard: bulk candidates of {count} triples == per-asset search")
    await _seed_assets(session)
    triples = _full_triples(count)
    assert _or_terms(triples) < SQLITE_MAX_DEPTH, "under SQLite's limit, one statement on HEAD too"

    expected = await _assert_bulk_matches_per_asset(session, triples)
    assert any(candidates for candidates, _ in expected.values()), "some triple matches"
    print_success(f"{count} triples ({_or_terms(triples)} OR terms): every answer the per-asset one")


# =============================================================================
# 2. _load_wac_fx_rows()
# =============================================================================

#: Five pairs as ``fx_rates`` keeps them (base < quote).
WAC_PAIRS = (("AUD", "JPY"), ("CHF", "EUR"), ("EUR", "GBP"), ("EUR", "USD"), ("GBP", "USD"))
WAC_DAYS = 310  # stored days per pair: 1 550 rows, of which at most 300 days per pair are asked for
WAC_MISSING_KEYS = (
    *(("CAD", "USD", _day(offset)) for offset in range(4)),  # a pair with no rate at all
    *(("EUR", "USD", _day(WAC_DAYS + offset)) for offset in range(3)),  # after the stored days
    *(("AUD", "JPY", _day(-1 - offset)) for offset in range(3)),  # before them
)


def _wac_rate(pair_index: int, offset: int) -> Decimal:
    return Decimal(f"{pair_index + 1}.{offset:04d}")


def _wac_source(pair_index: int, offset: int) -> str:
    return f"WAC-{pair_index}-{offset}"


async def _seed_wac_fx(session: AsyncSession) -> dict[tuple[str, str, date], int]:
    """1 550 stored rates, one statement per row (``executemany``); their ids by (base, quote, date)."""
    values = [{"date": _day(offset), "base": base, "quote": quote, "rate": _wac_rate(pair_index, offset), "source": _wac_source(pair_index, offset), "fetched_at": FETCHED_AT} for pair_index, (base, quote) in enumerate(WAC_PAIRS) for offset in range(WAC_DAYS)]
    await session.execute(insert(FxRate), values)
    await session.commit()
    result = await session.execute(select(FxRate.id, FxRate.base, FxRate.quote, FxRate.date))
    return {(row.base, row.quote, row.date): row.id for row in result.all()}


#: (stored keys asked for, keys without a row): one chunk exactly, one key past it, a long history.
WAC_KEY_COUNTS = [
    pytest.param(CHUNK - len(WAC_MISSING_KEYS), id="500-one-chunk"),
    pytest.param(CHUNK + 1 - len(WAC_MISSING_KEYS), id="501-two-chunks"),
    pytest.param(IMPORT_SIZED, id="1510-import-sized"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_keys", WAC_KEY_COUNTS)
async def test_wac_fx_rows_reads_every_key_of_a_long_history(session, stored_keys):
    """Every stored key asked for comes back with its own row (id, rate, source); keys without a row and stored rows
    nobody asked for stay out.

    The keys run day by day across the five pairs, so every chunk holds several pairs. Red on HEAD d63558abb at 1 510
    keys: ``OperationalError``; 500 and 501 are under SQLite's limit (guards).
    """
    print_section(f"MF-SEC9a: _load_wac_fx_rows with {stored_keys} stored keys and {len(WAC_MISSING_KEYS)} without a row")
    ids = await _seed_wac_fx(session)
    asked = [(base, quote, _day(offset)) for offset in range(IMPORT_SIZED // len(WAC_PAIRS)) for base, quote in WAC_PAIRS][:stored_keys]
    keys = set(asked) | set(WAC_MISSING_KEYS)
    assert len(keys) == stored_keys + len(WAC_MISSING_KEYS)
    assert not set(WAC_MISSING_KEYS) & set(ids), "the missing keys have no row"
    assert len(ids) > stored_keys, "stored rows nobody asks for exist"

    try:
        rows = await source_wac._load_wac_fx_rows(session, keys=keys)
    except OperationalError as error:
        pytest.fail(f"_load_wac_fx_rows raised for {len(keys)} keys, SQLite refusing the statement: {error.orig!r} (MF-SEC9a)")

    missing = [key for key in asked if key not in rows]
    unexpected = [key for key in rows if key not in set(asked)]
    assert not missing and not unexpected, f"{len(missing)} stored keys missing {missing[:5]}, {len(unexpected)} unexpected {unexpected[:5]}"
    pair_index = {pair: index for index, pair in enumerate(WAC_PAIRS)}
    wrong = []
    for base, quote, rate_date in asked:
        row = rows[(base, quote, rate_date)]
        offset = (rate_date - DAY0).days
        expected = (ids[(base, quote, rate_date)], _wac_rate(pair_index[(base, quote)], offset), _wac_source(pair_index[(base, quote)], offset))
        if (row.id, row.rate, row.source) != expected:
            wrong.append(((base, quote, rate_date), (row.id, row.rate, row.source), expected))
    assert not wrong, f"{len(wrong)} keys with another row (key, got, expected): {wrong[:3]}"
    print_success(f"{len(keys)} keys: the {stored_keys} stored ones answered, each with its own row; none of the others")
