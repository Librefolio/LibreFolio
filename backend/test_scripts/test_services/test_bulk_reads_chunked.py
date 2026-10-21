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

MF-SEC9g — the classification after the read. HEAD 633e30ca9 ran the five-step priority of every extraction over the
whole universe on the event loop, rebuilding a LIKE pattern at every test of every asset and dumping
``identifier_other`` at every check: E measured 104 s of stalled loop for 1 000 generic names over 5 000 assets. The cure
(``_candidate_view``, ``_classify_candidates`` in a worker thread, one matcher per needle, exact ISIN/ticker indexes),
pinned here:

3. the LIKE matching of the classification runs in a thread that is not the loop's, and the loop runs a coroutine sent
   from inside the classification (thread identity and a handshake, no clock);
4. at most one LIKE compile per needle and one ``identifier_other`` text per stored asset (counted, not timed).

Red on HEAD 633e30ca9: ``test_bulk_candidates_classify_off_the_event_loop`` (150 000 compiles, all on the loop's
thread) and ``test_bulk_candidates_compile_each_needle_once_and_dump_each_asset_once`` (150 000 compiles for 200
needles, 60 000 dumps for 300 assets). Green before and after (guards):
``test_guard_bulk_candidates_at_size_match_the_per_asset_search`` (300 extractions over 1 011 assets, wildcard bond
names, codes stored in either case, duplicate holders) and ``test_guard_bulk_exact_hits_keep_the_universe_order``.

X-R45, reverted — the planner's saved FX reads take the stored row as it is; ``convert_bulk`` and the period changes still
skip a rate outside ``usable_fx_rate_bounds()``. A 1.2 install could store rates outside X-R38's
``usable_fx_rate_bounds()``, 1E-10 <= rate < 1E+14: 0 (a manual ``1E-11`` truncated to 10 decimals), an infinite REAL
(``1E+400``), 1E+14 and above. X-R45 (629304ab3) added ``usable_fx_rate_clause()`` to three readers that read them as
stored — two here, the latest saved quote of a pair (``pac_allocator/source/fx_quotes._load_latest_planner_fx_rows``: a
``max(date)`` subquery, then a join) and the WAC evidence (``pac_allocator/source/wac._load_wac_fx_rows``: the exact
keys); the third is the history sync's lookup, ``test_scheduler_last_fx_dates.py`` — and routed through it the two
readers that already skipped them: ``convert_bulk`` (X-R38) and ``fx/period_changes._first_rate_days_inside`` (X-R59).

The decision that reverts it (developer, 19/10, relayed by the coordinator), verbatim: «non devi filtrare … sono sicuro al
99.9% che non è ancora mai successo, e se è successo, gli utenti possono … modificare … a mano, evitiamo di fare bonifiche
non necessarie che possono anzi rompere il sistema». Then: «si tengono i due lettori che filtravano già prima
(``convert_bulk`` di X-R38 e la variazione dei periodi di X-R59). Il rovescio toglie tutto il resto di X-R45: la
condizione nei tre lettori nuovi; la guardia strutturale e i suoi test; la doc, il runner e la riga del CHANGELOG. I due
lettori devono restare come prima di X-R45, quindi ancora filtrati.» X-R38's write refusal (``storable_fx_rate``) stays;
nothing cleans such a row up, at startup or from the scheduler (D-W63-1: no). Pinned in section 4 on ERN/STN, its rows
planted with raw SQL past the model, as an older release could leave them:

5. the planner's latest saved row on or before ``as_of`` is the latest stored one — D2's 0, inf or 1E+14 over D1's 2.5,
   or alone —, its rate as the column reads it back (a REAL inf is ``Decimal('Infinity')``);
6. the WAC evidence reads the stored row of each exact key, whatever its rate (0, inf, 1E+14, as read back), beside the
   usable key;
7. ``convert_bulk`` (its backward-fill anchor and its window) and ``_first_rate_days_inside`` still read only the rates
   within the bounds: the nine cases of the deleted gate's clause test (``test_utilities/test_usable_fx_rate_gate.py``),
   1E-10, 1.5 and 99999999999999 read, 0, 1E-11, -1.5, inf, 1E+14 and 1E+19 skipped.

X-R45b — the planner's quote skips a saved rate of 0 or not finite for the previous valid one, with a warning. The
decision (developer, 19/10), verbatim: «Sì: tasso valido precedente con l'avviso, e lo 0 trattato allo stesso modo». In
``build_planner_fx_quotes``, when the latest saved row of a pair (on or before ``as_of``, from the loader, which does not
change) has a rate of 0 or not finite — a negative one too, the cure's ``keys.usable_rate`` being finite and > 0; no case
pins it —, the quote is built from the pair's most recent earlier row whose rate is finite and above 0
(``_previous_usable_row``, as many rows back as it takes), with ONE warning ``allocation.saved_fx_skipped`` (kind
``invalid``) about that quote, its params the pair, ``skipped_date`` (the most recent row skipped) and ``used_date``,
and no ``allocation.saved_fx_invalid``. With no such row, today's error: the latest row's quote with no rate and
``allocation.saved_fx_invalid`` — for an infinite rate too, where today the builder raises (``rate > 0`` holds for an
infinity, and ``PortfolioPlannerSourceFxQuote`` refuses a Decimal that is not finite, pydantic ``finite_number``: a 500
on ``POST /portfolio/allocation-source``). A finite rate from 1E+14 up stays a value, quoted as read back. The code is
the allocation-source API's (``PortfolioPlannerSourceIssueCode``), not the tool contract's (``PlannerIssueCode``). Pinned
on ERN/STN, beside the valid rates of two neighbouring pairs (ERN/SZL, BBD/STN) on the day between D1 and D2, which a
look-back must not take:

8. 0 or inf on D2 over 2.5 on D1, as of D2 and later: D1's quote — 2.5, D1, its source, its age — and the warning
   (``skipped_date`` D2, ``used_date`` D1);
9. two skipped rows in a row, 0 then inf and inf then 0 on D2 and D3, over 2.5 on D1, as of D3 and later: D1's quote and
   ONE warning, ``skipped_date`` D3, the most recent;
10. no valid row before the latest (an inf alone, 0 then inf; a 0 alone, inf then 0): the latest row's quote with no
    rate, and the error ``allocation.saved_fx_invalid`` about it, no warning;
11. 1E+14 on D2, over 2.5 on D1 and alone: D2's quote, 1E+14 as read back, no issue;
12. ``allocation.saved_fx_skipped`` is one of ``PortfolioPlannerSourceIssueCode`` and not one of ``PlannerIssueCode``.

Red until the X-R45 revert (c720e25cb), green since, and unchanged by X-R45b, which touches neither the loader nor the
WAC read: ``test_xr45_reverted_the_latest_saved_planner_fx_row_is_the_latest_stored_one`` (0, inf and 1E+14, as of D2
and later), ``test_xr45_reverted_a_planner_fx_pair_whose_only_saved_rate_is_unusable_has_that_row`` (0, inf and 1E+14)
and ``test_xr45_reverted_wac_fx_evidence_reads_the_stored_row_of_its_exact_date`` (0, inf and 1E+14).

RED until X-R45b: ``test_xr45b_a_zero_or_infinite_latest_planner_fx_rate_falls_back_to_the_previous_valid_one`` (0 and
inf, as of D2 and later), ``test_xr45b_several_unusable_planner_fx_rates_in_a_row_fall_back_to_the_previous_valid_one``
(both runs, as of D3 and later), ``test_xr45b_a_planner_fx_pair_with_no_valid_rate_is_invalid_from_its_latest_row`` (an
inf alone, 0 then inf) and ``test_xr45b_saved_fx_skipped_is_a_source_issue_code_and_not_a_tool_issue_code``.

Green before and after (guards): ``test_xr45b_guard_a_pair_whose_latest_rate_is_zero_and_none_valid_before_is_invalid``
(a 0 alone, inf then 0), ``test_xr45b_guard_a_finite_planner_fx_rate_from_1e14_up_is_quoted_as_read_back``,
``test_xr45_guard_the_latest_usable_planner_fx_rate_wins`` and
``test_xr45_guard_wac_fx_evidence_reads_a_usable_saved_rate_on_its_exact_date`` (an ordinary rate and the two bounds,
1E-10 and 99999999999999); ``test_xr45_guard_convert_bulk_still_reads_only_rates_within_the_usable_bounds`` and
``test_xr45_guard_first_rate_days_inside_still_reads_only_rates_within_the_usable_bounds`` (the nine cases).

Isolation: PURE — no lane database, no server, no network. Each test has its own in-memory SQLite database
(``SQLModel.metadata.create_all``), closed and disposed at teardown.

Reference: backend/app/utils/sql_chunks.py, backend/app/services/brim/brim_provider.py (search_asset_candidates,
search_asset_candidates_bulk, _classify_candidates, _contains_matcher, _like_to_regex, _other_as_text),
backend/app/services/pac_allocator/source/wac.py (_load_wac_fx_rows),
backend/app/services/pac_allocator/source/fx_quotes.py (_load_latest_planner_fx_rows, build_planner_fx_quotes, and the
cure's _previous_usable_row),
backend/app/schemas/portfolio.py (PortfolioPlannerSourceIssueCode, PortfolioPlannerSourceFxQuote),
backend/app/schemas/pac_allocator/base.py (PlannerIssueCode),
backend/app/services/fx/conversion.py (convert_bulk), backend/app/services/fx/period_changes.py
(_first_rate_days_inside), backend/app/db/precision.py (usable_fx_rate_bounds),
backend/test_scripts/test_db/test_brim_bulk_candidates.py (the same parity on a small universe).
"""

from __future__ import annotations

import asyncio
import random
import threading
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, get_args

import pytest
import pytest_asyncio
from sqlalchemy import String, and_, cast, insert, or_, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, FxRate
from backend.app.schemas.brim import BRIMMatchConfidence
from backend.app.schemas.common import Currency
from backend.app.schemas.pac_allocator.base import PlannerIssueCode
from backend.app.schemas.portfolio import PortfolioPlannerSourceIssueCode
from backend.app.services.brim import brim_provider
from backend.app.services.fx import period_changes as fx_period_changes
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.pac_allocator.source import fx_quotes as source_fx_quotes
from backend.app.services.pac_allocator.source import wac as source_wac
from backend.app.services.pac_allocator.source.keys import fx_key
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


# =============================================================================
# 3. MF-SEC9g: the candidate classification off the event loop, its work bounded, its answers unchanged at size
# =============================================================================

#: Words of generic fund names: every asset's display name is two of them, so every extracted name below runs the whole
#: priority chain (unknown ISIN, unknown symbol, a name) over the whole universe, the shape E measured.
GENERIC_WORDS = ("Global", "Equity", "Bond", "Income", "World", "Euro", "Growth", "Value", "Index", "Dividend")
N_GENERIC_ASSETS = 300
#: Seconds the classification's thread waits for the event loop to run a coroutine: a deadline, met at once when the
#: loop is free, never a sleep.
LOOP_ANSWER_DEADLINE = 30.0


def _generic_display_name(index: int) -> str:
    return f"{GENERIC_WORDS[index % 10]} {GENERIC_WORDS[(index // 10) % 10]} Fund {index:04d}"


async def _seed_generic_assets(session: AsyncSession) -> None:
    """300 generic funds, each with an ISIN, a ticker and an alternate, so every identifier text is there to be tested."""
    order = list(range(N_GENERIC_ASSETS))
    random.Random(17).shuffle(order)
    session.add_all(
        Asset(
            display_name=_generic_display_name(index),
            currency="EUR",
            asset_type=AssetType.FUND,
            identifier_isin=f"GN{index:010d}",
            identifier_ticker=f"GT{index:04d}",
            identifier_other=[f"GA{index:010d}"],
        )
        for index in order
    )
    await session.commit()


def _generic_triples() -> list[Triple]:
    """100 distinct extractions, unknown symbol and ISIN, a generic name: the ten words alone, then 90 of their pairs."""
    names = list(GENERIC_WORDS) + [f"{first} {second}" for first in GENERIC_WORDS for second in GENERIC_WORDS if first != second]
    triples: list[Triple] = [(f"NOSYM{k:03d}", f"ZZ{k:010d}", name) for k, name in enumerate(names)]
    assert len(set(triples)) == len(triples) == 100, "the fixture's triples are distinct"
    return triples


@pytest.mark.asyncio
async def test_bulk_candidates_classify_off_the_event_loop(session, monkeypatch):
    """While ``search_asset_candidates_bulk`` classifies 100 generic names over 300 generic funds, its LIKE matching runs
    in a thread that is not the event loop's, and the loop runs a coroutine sent to it from inside the classification.

    Deterministic, no clock: ``_like_to_regex`` — what the classification calls for every LIKE it reproduces — is wrapped
    to record the thread it runs in. At the first call off the loop's thread the classification itself, mid-flight,
    sends a coroutine to the loop and waits for its answer (``LOOP_ANSWER_DEADLINE``, met at once by a free loop): the
    concurrent request the import must not starve. Red on HEAD 633e30ca9: every compile on the loop's thread — the
    classification ran on the event loop, stalling it (0.5 s for 1 000 realistic instruments, 104 s for 1 000 generic
    names over 5 000 assets, E's measures).
    """
    print_section("MF-SEC9g: the candidate classification runs off the event loop")
    await _seed_generic_assets(session)
    triples = _generic_triples()
    loop = asyncio.get_running_loop()
    loop_thread = threading.get_ident()
    compile_threads: list[int] = []
    loop_answers: list[Optional[int]] = []
    like_to_regex = brim_provider._like_to_regex

    async def _answer_from_the_loop() -> int:
        return threading.get_ident()

    def _recording_like_to_regex(pattern: str):
        thread = threading.get_ident()
        compile_threads.append(thread)
        if thread != loop_thread and not loop_answers:
            # Mid-classification, from its own thread: the loop must run a coroutine now. Not asked on the loop's
            # thread, where the answer cannot come by construction: the thread check there is the red.
            try:
                loop_answers.append(asyncio.run_coroutine_threadsafe(_answer_from_the_loop(), loop).result(timeout=LOOP_ANSWER_DEADLINE))
            except TimeoutError:
                loop_answers.append(None)
        return like_to_regex(pattern)

    monkeypatch.setattr(brim_provider, "_like_to_regex", _recording_like_to_regex)
    bulk = await brim_provider.search_asset_candidates_bulk(session, triples)

    assert set(bulk) == set(triples), f"one answer per distinct triple: {len(bulk)} for {len(triples)}"
    assert all(candidates for candidates, _ in bulk.values()), "every generic name matches funds: the classification did its work"
    assert compile_threads, "the probe saw the classification's LIKE matching (_like_to_regex): without it the thread check below proves nothing"
    on_loop = sum(thread == loop_thread for thread in compile_threads)
    assert on_loop == 0, f"{on_loop} of {len(compile_threads)} LIKE patterns of the classification compiled on the event loop's thread: the loop stalled for the whole classification (MF-SEC9g)"
    assert loop_answers == [loop_thread], f"the event loop did not run a coroutine within {LOOP_ANSWER_DEADLINE} s while the classification ran in its thread: {loop_answers}"
    print_success(f"{len(compile_threads)} LIKE compiles, none on the loop's thread; the loop answered mid-classification")


@pytest.mark.asyncio
async def test_bulk_candidates_compile_each_needle_once_and_dump_each_asset_once(session, monkeypatch):
    """The classification's work is bounded by its input, not by input × universe: at most one LIKE pattern compiled per
    needle (an extraction's ISIN, its name) and one ``identifier_other`` text built per stored asset, for 100 generic
    names (asked twice in part: duplicates collapse) over 300 funds.

    Counted, never timed: ``_like_to_regex`` and ``_other_as_text`` wrapped. Red on HEAD 633e30ca9: ``_contains`` rebuilt
    the pattern at every test of every asset, and ``identifier_other`` was dumped again at every check — about
    150 000 compiles and 60 000 dumps here, for 200 needles and 300 assets.
    """
    print_section("MF-SEC9g: one LIKE compile per needle, one identifier_other text per asset")
    await _seed_generic_assets(session)
    triples = _generic_triples()
    compiles: list[str] = []
    dumps: list[Optional[list[str]]] = []
    like_to_regex, other_as_text = brim_provider._like_to_regex, brim_provider._other_as_text

    def _counting_like_to_regex(pattern: str):
        compiles.append(pattern)
        return like_to_regex(pattern)

    def _counting_other_as_text(value: Optional[list[str]]) -> str:
        dumps.append(value)
        return other_as_text(value)

    monkeypatch.setattr(brim_provider, "_like_to_regex", _counting_like_to_regex)
    monkeypatch.setattr(brim_provider, "_other_as_text", _counting_other_as_text)
    bulk = await brim_provider.search_asset_candidates_bulk(session, triples + triples[::5])

    assert set(bulk) == set(triples), f"one answer per distinct triple: {len(bulk)} for {len(triples)}"
    needles = sum(bool(isin) + bool(name) for _, isin, name in triples)
    assert compiles and dumps, f"the probes saw the classification: {len(compiles)} compiles, {len(dumps)} dumps"
    assert len(compiles) <= needles and len(dumps) <= N_GENERIC_ASSETS, f"{len(compiles)} LIKE compiles for {needles} needles, {len(dumps)} identifier_other dumps for {N_GENERIC_ASSETS} stored assets: the classification's work grows with extractions × universe (MF-SEC9g)"
    print_success(f"{len(compiles)} compiles for {needles} needles, {len(dumps)} dumps for {N_GENERIC_ASSETS} assets")


#: The universe of the parity case at size: 1 000 generic funds, then the assets of the special cases below.
N_SIZED_ASSETS = 1_000
SIZED_SPECIAL_ASSETS: tuple[tuple[str, Optional[str], Optional[str], Optional[list[str]]], ...] = (
    # (display name, ISIN, ticker, identifier_other)
    ("BTP Valore 3,35% Mar27", "IT0005000001", "BTPV27", None),  # a «%» in the name: SQL LIKE reads it as «anything»
    ("BTP Valore 3,35 Giu28", "IT0005000002", "BTPV28", None),  # reached by «BTP Valore 3,35%» only through the wildcard
    ("BTP Valore 3,45% Ott29", "IT0005000003", None, None),
    ("BTP Italia 1,6% Nov30", "IT0005000004", None, ["IT0005000044"]),
    ("Isin Case Lower Holding", "lc0000000001", "lctk01", None),  # stored lower case, past the model's validators
    ("Isin Case Upper Holding", "LC0000000001", "LCTK01", None),  # the same codes, upper case: the index must not fold
    ("Isin Case Alternate Holding", "MX0000000001", None, ["Lc0000000001"]),  # the alternate's LIKE folds ASCII case
    ("Isin Lone Lower Holding", "lq0000000001", None, None),  # stored lower case, no upper twin: never an exact hit
    ("Twin Isin Zulu", "TW0000000001", "TWTK", None),  # duplicates: two primaries, an alternate, two tickers
    ("Twin Isin Alpha", "TW0000000001", "TWTK", None),
    ("Twin Isin Mike", None, None, ["TW0000000001"]),
)
#: Extractions of the special cases: the wildcard bond names, case-only differences, duplicates.
SIZED_SPECIAL_TRIPLES: tuple[Triple, ...] = (
    (None, None, "BTP Valore 3,35%"),
    (None, None, "btp valore 3,35%"),
    (None, None, "BTP_Valore"),
    (None, None, "3,_5%"),
    (None, "IT0005000044", "BTP Italia"),
    ("NOSYM-LCU", "LC0000000001", "Nothing case upper"),
    ("NOSYM-LCL", "lc0000000001", "Nothing case lower"),
    (None, None, "Isin Case Lower"),
    ("NOSYM-LQ", "LQ0000000001", "Isin Lone Lower"),
    ("LCTK01", None, None),
    ("lctk01", None, "lctk01"),
    ("NOSYM-TW", "TW0000000001", "Twin"),
    ("twtk", None, None),
)


def _sized_isin(index: int) -> Optional[str]:
    return None if index % 13 == 6 else f"SZ{index:010d}"


def _sized_ticker(index: int) -> Optional[str]:
    return None if index % 9 == 4 else f"ST{index:04d}"


def _sized_display_name(index: int) -> str:
    return f"{GENERIC_WORDS[index % 10]} {GENERIC_WORDS[(index // 10) % 10]} {index:04d}"


async def _seed_sized_assets(session: AsyncSession) -> None:
    """1 000 generic funds in shuffled order, then the special assets against their display names' order: no id order
    is a display-name order, the twins' least of all (raw rows: the lower-case codes stay lower)."""
    rows = [
        {
            "display_name": _sized_display_name(index),
            "identifier_isin": _sized_isin(index),
            "identifier_ticker": _sized_ticker(index),
            "identifier_other": [f"SA{index:010d}", f"Soft sized {index:04d}"] if index % 40 == 0 else None,
        }
        for index in range(N_SIZED_ASSETS)
    ]
    random.Random(23).shuffle(rows)
    specials = sorted(SIZED_SPECIAL_ASSETS, key=lambda special: special[0], reverse=True)
    rows += [{"display_name": name, "identifier_isin": isin, "identifier_ticker": ticker, "identifier_other": other} for name, isin, ticker, other in specials]
    now = datetime(2026, 1, 1)
    await session.execute(insert(Asset), [{**row, "currency": "EUR", "asset_type": AssetType.FUND, "created_at": now, "updated_at": now} for row in rows])
    await session.commit()


def _sized_triples(count: int) -> list[Triple]:
    """``count`` distinct extractions: exact ISINs and tickers (either case), alternates, generic words and pairs, whole
    names with their ASCII case swapped, nothing at all; the special cases on both ends."""
    triples: list[Triple] = []
    k = 0
    while len(triples) < count - len(SIZED_SPECIAL_TRIPLES):
        index = (k * 37) % N_SIZED_ASSETS
        unknown_symbol, unknown_isin, unknown_name = f"NO{k:04d}", f"ZZ{k:010d}", f"Nothing {k:04d}"
        kind = k % 7
        if kind == 0:  # by ISIN, either case; an asset without one falls through to its ticker, then its name
            isin = _sized_isin(index) or unknown_isin
            triples.append((_sized_ticker(index) or unknown_symbol, isin.lower() if k % 2 else isin, _sized_display_name(index)))
        elif kind == 1:  # by ticker, lower case
            triples.append(((_sized_ticker(index) or unknown_symbol).lower(), unknown_isin, unknown_name))
        elif kind == 2:  # by an alternate ISIN
            triples.append((unknown_symbol, f"SA{(k * 40) % N_SIZED_ASSETS:010d}", unknown_name))
        elif kind == 3:  # by a generic word (about 190 funds) or a pair of them (10 funds), sometimes swapped
            word = GENERIC_WORDS[k % 10] if k % 3 == 0 else f"{GENERIC_WORDS[k % 10]} {GENERIC_WORDS[(k // 10) % 10]}"
            triples.append((unknown_symbol, unknown_isin, _ascii_swapcase(word) if k % 2 else word))
        elif kind == 4:  # by the whole display name, its ASCII case swapped
            triples.append((unknown_symbol, unknown_isin, _ascii_swapcase(_sized_display_name(index))))
        elif kind == 5:  # by a soft label
            triples.append((None, None, f"soft sized {(k * 40) % N_SIZED_ASSETS:04d}"))
        else:  # by nothing at all
            triples.append((unknown_symbol, unknown_isin, unknown_name))
        if len(set(triples)) < len(triples):
            triples.pop()  # a generic word asked again: keep the triples distinct
        k += 1
    half = len(SIZED_SPECIAL_TRIPLES) // 2
    triples = list(SIZED_SPECIAL_TRIPLES[:half]) + triples + list(SIZED_SPECIAL_TRIPLES[half:])
    assert len(set(triples)) == len(triples) == count, "the fixture's triples are distinct"
    return triples


@pytest.mark.asyncio
async def test_guard_bulk_candidates_at_size_match_the_per_asset_search(session):
    """Guard: 300 distinct extractions (some asked twice) over 1 011 assets — exact ISINs and tickers in either case,
    alternates, generic words matching about 190 funds, soft labels, nothing, bond names with ``%`` and ``_``
    (``BTP Valore 3,35%`` reaches ``BTP Valore 3,35 Giu28`` only through the wildcard), codes stored lower case beside
    the same codes upper case and alone, two primaries and an alternate of one ISIN, two holders of one ticker — answer,
    triple by triple, what ``search_asset_candidates`` answers: candidate ids, confidences, order, auto-selection.

    The per-asset path compares the extraction upper-cased with the stored code, case-sensitively (SQLite's ``=``): a
    code stored lower case is never an exact hit, whatever the extraction's case — the lone one is found by its name,
    LOW — while an alternate's LIKE folds ASCII case. The exact indexes are keyed by the stored code and looked up
    upper-cased: the same answer, which a case-folding key would break. Green before and after: what MF-SEC9g moved off
    the loop must answer what the scan answered.
    """
    print_section("MF-SEC9g guard: 300 extractions over 1 011 assets == per-asset search")
    await _seed_sized_assets(session)
    ids_by_name = {name: asset_id for asset_id, name in (await session.execute(select(Asset.id, Asset.display_name))).tuples().all()}
    assert ids_by_name["Twin Isin Zulu"] < ids_by_name["Twin Isin Alpha"], "the twins' ids against their display names' order"
    triples = _sized_triples(300)

    expected = await _assert_bulk_matches_per_asset(session, triples)

    confidences = {confidence for candidates, _ in expected.values() for _, confidence in candidates}
    assert confidences == set(BRIMMatchConfidence), f"every confidence reached: {sorted(confidences)}"
    assert any(not candidates for candidates, _ in expected.values()), "a triple matching nothing"
    assert any(auto is not None for _, auto in expected.values()), "a triple auto-selected"
    assert max(len(candidates) for candidates, _ in expected.values()) >= 150, "a generic word answering most of a word's funds"
    wildcard = {asset_id for asset_id, _ in expected[(None, None, "BTP Valore 3,35%")][0]}
    assert ids_by_name["BTP Valore 3,35 Giu28"] in wildcard, "«BTP Valore 3,35%» reaches a name without «%»: the wildcard case is compared"
    reached = {asset_id for candidates, _ in expected.values() for asset_id, _ in candidates}
    case_holders = {ids_by_name[name] for name in ("Isin Case Lower Holding", "Isin Case Upper Holding", "Isin Lone Lower Holding")}
    assert case_holders <= reached, "the codes stored in either case are in the universe the exact indexes are built from"
    print_success(f"{len(triples)} extractions over {len(ids_by_name)} assets: every answer the per-asset one")


@pytest.mark.asyncio
async def test_guard_bulk_exact_hits_keep_the_universe_order(session):
    """Guard: three assets with one primary ISIN and two with one ticker, inserted against their display names' order,
    come out of the exact steps in display-name order — the order of the scan the index replaced, and of the per-asset
    search — with the alternate holder after them; ids in insertion order would show.

    Green before and after: the index's lists keep the universe's order.
    """
    print_section("MF-SEC9g guard: exact ISIN and ticker hits in display-name order")
    now = datetime(2026, 1, 1)
    rows = [
        ("Zulu twin isin", "TW0000000009", None, None),
        ("Kilo twin isin", "TW0000000009", None, None),
        ("Alpha twin isin", "TW0000000009", None, None),
        ("Mike alternate twin", None, None, ["TW0000000009"]),
        ("Yankee twin ticker", None, "TWTK9", None),
        ("Bravo twin ticker", None, "TWTK9", None),
    ]
    await session.execute(
        insert(Asset),
        [{"display_name": name, "identifier_isin": isin, "identifier_ticker": ticker, "identifier_other": other, "currency": "EUR", "asset_type": AssetType.BOND, "created_at": now, "updated_at": now} for name, isin, ticker, other in rows],
    )
    await session.commit()
    ids_by_name = {name: asset_id for asset_id, name in (await session.execute(select(Asset.id, Asset.display_name))).tuples().all()}
    assert ids_by_name["Zulu twin isin"] < ids_by_name["Alpha twin isin"], "ids against the display names' order"

    by_isin, by_ticker = ("NOSYM-TW9", "TW0000000009", None), ("twtk9", None, None)
    bulk = await brim_provider.search_asset_candidates_bulk(session, [by_isin, by_ticker])

    exact, high, medium = BRIMMatchConfidence.EXACT, BRIMMatchConfidence.HIGH, BRIMMatchConfidence.MEDIUM
    expected = {
        by_isin: ([(ids_by_name[name], confidence) for name, confidence in (("Alpha twin isin", exact), ("Kilo twin isin", exact), ("Zulu twin isin", exact), ("Mike alternate twin", high))], None),
        by_ticker: ([(ids_by_name["Bravo twin ticker"], medium), (ids_by_name["Yankee twin ticker"], medium)], None),
    }
    for triple, answer in expected.items():
        assert _shape(bulk[triple]) == answer, f"{triple}: bulk {_shape(bulk[triple])}, expected {answer}"
        assert _shape(await brim_provider.search_asset_candidates(session, *triple)) == answer, f"{triple}: the per-asset search agrees"
    print_success("three primaries, one alternate, two tickers: display-name order in both paths")


# =============================================================================
# 4. X-R45 REVERTED: THE PLANNER'S SAVED FX READS TAKE THE STORED ROW AS IT IS; convert_bulk AND
#    _first_rate_days_inside STILL SKIP A RATE OUTSIDE usable_fx_rate_bounds(). X-R45b: THE PLANNER'S QUOTE SKIPS A
#    SAVED RATE OF 0 OR NOT FINITE FOR THE PREVIOUS VALID ONE, WITH A WARNING
# =============================================================================

#: The pair of this section, as ``fx_rates`` keeps it (base < quote): real ISO 4217 codes, since a planner quote
#: validates its pair. No other test stores it — and each test has its own database anyway.
XR45_BASE, XR45_QUOTE = "ERN", "STN"
XR45_PAIR = f"{XR45_BASE}/{XR45_QUOTE}"
XR45_D1 = date(1987, 6, 8)  # a usable rate
XR45_D2 = date(1987, 6, 10)  # the pair's latest row: a rate outside usable_fx_rate_bounds(), in the reverted cases
XR45_D3 = date(1987, 6, 12)  # X-R45b: the second row of a run of skipped rates, after D2
XR45_LATER = date(1987, 6, 15)  # an as_of after D1, D2 and D3
XR45_D1_RATE = Decimal("2.5")
#: Rates a 1.2 install could store outside X-R38's ``usable_fx_rate_bounds()`` (1E-10 <= rate < 1E+14), as SQLite binds
#: them, with the Decimal the ORM reads back from ``fx_rates.rate`` (``Numeric(24, 10)`` on SQLite: ``"%.10f" % value``,
#: so a REAL inf is ``Decimal('Infinity')``).
XR45_UNUSABLE = [
    pytest.param(0.0, Decimal("0"), id="0"),  # a manual 1E-11, truncated to the column's 10 decimals
    pytest.param(float("inf"), Decimal("Infinity"), id="inf"),  # 1E+400, written as an SQLite REAL
    pytest.param(1e14, Decimal("1E+14"), id="1E+14"),  # the first rate refused
]
#: Rates a read may use, the two bounds among them, with the Decimal ``fx_rates.rate`` reads back.
XR45_USABLE = [
    pytest.param(4.0, Decimal("4"), id="ordinary-4"),
    pytest.param(1e-10, Decimal("1E-10"), id="smallest-1E-10"),
    pytest.param(99999999999999.0, Decimal("99999999999999"), id="largest-99999999999999"),
]
XR45_AS_OF = [pytest.param(XR45_D2, id="as-of-D2"), pytest.param(XR45_LATER, id="as-of-later")]
#: X-R45b: the saved rates the planner's quote skips — 0 and not finite —, as SQLite binds them.
XR45B_SKIPPED = [
    pytest.param(0.0, id="0"),  # a manual 1E-11, truncated to the column's 10 decimals
    pytest.param(float("inf"), id="inf"),  # 1E+400, written as an SQLite REAL
]
#: X-R45b: two skipped rates in a row, on D2 then on D3, in both orders.
XR45B_RUNS = [
    pytest.param(0.0, float("inf"), id="0-then-inf"),
    pytest.param(float("inf"), 0.0, id="inf-then-0"),
]
XR45B_RUN_AS_OF = [pytest.param(XR45_D3, id="as-of-D3"), pytest.param(XR45_LATER, id="as-of-later")]
#: X-R45b: valid rates of two neighbouring pairs — one shares ERN, the other STN —, on a day between D1 and D2. A look-back
#: that forgot the pair, or one side of it, takes one of them before D1's 2.5.
XR45B_DECOY_DAY = date(1987, 6, 9)
XR45B_DECOYS = {("ERN", "SZL"): 7.0, ("BBD", "STN"): 9.0}


def _xr45_source(day: date) -> str:
    """The source of the rate planted on ``day``: it tells the rows apart."""
    return f"XR45-{day.isoformat()}"


async def _xr45_plant(session: AsyncSession, rates: dict[date, float]) -> None:
    """ERN/STN rates written with raw SQL, past the model: what an older release could leave in ``fx_rates``.

    Barrier: raw SQL reads back the very rates planted — an inf stays inf, a 0 stays 0 — and no other ERN/STN row.
    """
    for day, rate in rates.items():
        await session.execute(
            text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, :source, CURRENT_TIMESTAMP)"),
            {"day": day.isoformat(), "base": XR45_BASE, "quote": XR45_QUOTE, "rate": rate, "source": _xr45_source(day)},
        )
    stored = (await session.execute(text("SELECT date, rate FROM fx_rates WHERE base = :base AND quote = :quote"), {"base": XR45_BASE, "quote": XR45_QUOTE})).all()
    found = {date.fromisoformat(day): rate for day, rate in stored}
    assert found == rates, f"the fixture itself is wrong: raw SQL reads back {found}, not the rates planted, {rates}"


async def _xr45b_plant_decoys(session: AsyncSession) -> None:
    """The neighbouring pairs' valid rates on ``XR45B_DECOY_DAY``, written as ``_xr45_plant`` writes ERN/STN's.

    Barrier: raw SQL reads back, on that day, these two rates and no ERN/STN row.
    """
    for (base, quote), rate in XR45B_DECOYS.items():
        await session.execute(
            text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, :source, CURRENT_TIMESTAMP)"),
            {"day": XR45B_DECOY_DAY.isoformat(), "base": base, "quote": quote, "rate": rate, "source": f"XR45B-DECOY-{base}-{quote}"},
        )
    stored = (await session.execute(text("SELECT base, quote, rate FROM fx_rates WHERE date = :day"), {"day": XR45B_DECOY_DAY.isoformat()})).all()
    found = {(base, quote): rate for base, quote, rate in stored}
    assert found == XR45B_DECOYS, f"the fixture itself is wrong: raw SQL reads back {found} on {XR45B_DECOY_DAY}, not the decoys planted, {XR45B_DECOYS}"


async def _xr45_quotes(session: AsyncSession, issues: list, story: str, as_of: date = XR45_LATER) -> list:
    """``build_planner_fx_quotes`` for ERN/STN as of ``as_of``. An exception fails the test, naming it.

    Before X-R45b an infinite latest rate raises here: ``rate > 0`` holds for an infinity, and the quote's schema refuses
    a Decimal that is not finite.
    """
    try:
        return await source_fx_quotes.build_planner_fx_quotes(session, request_pairs=[XR45_PAIR], as_of=as_of, issues=issues)
    except Exception as exc:  # any exception fails the test, named: no case here may raise
        pytest.fail(f"{story}: build_planner_fx_quotes raised {exc!r} (X-R45b: a saved rate of 0 or not finite is skipped, never quoted)")


def _xr45_assert_quote(quotes: list, as_of: date, day: date, rate: Optional[Decimal], story: str) -> str:
    """The one quote of ERN/STN is built from the row of ``day`` — its id, its reference date, its source, its age as of
    ``as_of`` —, with ``rate``. Returns the quote's id, which its issues name."""
    quote_id = fx_key(XR45_PAIR, day, _xr45_source(day))
    found = [(quote.fx_quote_id, quote.pair, quote.rate, quote.reference_date, quote.source, quote.days_before_requested) for quote in quotes]
    expected = [(quote_id, XR45_PAIR, rate, day, _xr45_source(day), (as_of - day).days)]
    assert found == expected, f"{story} is {found}: expected {expected}, the quote of the row of {day}"
    return quote_id


def _xr45_issue_shapes(issues: list) -> list[tuple]:
    """Each issue as (code, kind, severity, path, params), its path and its params as plain dicts, in order."""
    return [(issue.code, issue.kind, issue.severity, issue.path.model_dump(), [param.model_dump() for param in issue.params]) for issue in issues]


def _xr45_rate_issue(code: str, kind: str, severity: str, quote_id: str, *params: dict) -> tuple:
    """The shape of an issue about the rate of the ERN/STN quote ``quote_id``: its params the pair, then ``params``."""
    path = {"kind": "field", "section": "fx_quotes", "entity_kind": "fx_quote", "entity_id": quote_id, "field": "rate"}
    return (code, kind, severity, path, [{"kind": "text", "name": "pair", "value": XR45_PAIR}, *params])


def _xr45b_skipped_warning(quote_id: str, skipped: date, used: date) -> tuple:
    """X-R45b's warning: ``allocation.saved_fx_skipped`` about the used row's quote, with the pair, the most recent date
    skipped and the date used."""
    skipped_param = {"kind": "date", "name": "skipped_date", "value": skipped}
    used_param = {"kind": "date", "name": "used_date", "value": used}
    return _xr45_rate_issue("allocation.saved_fx_skipped", "invalid", "warning", quote_id, skipped_param, used_param)


def _xr45_invalid_error(quote_id: str) -> tuple:
    """The error of a quote with no rate: ``allocation.saved_fx_invalid`` about it, with the pair."""
    return _xr45_rate_issue("allocation.saved_fx_invalid", "invalid", "error", quote_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of", XR45_AS_OF)
@pytest.mark.parametrize(("unusable", "read_back"), XR45_UNUSABLE)
async def test_xr45_reverted_the_latest_saved_planner_fx_row_is_the_latest_stored_one(session, unusable, read_back, as_of):
    """RED until the X-R45 revert: ``usable_fx_rate_clause()`` in the ``max(date)`` subquery of
    ``_load_latest_planner_fx_rows`` skips D2's 0, inf or 1E+14, so D1's row (2.5) comes back instead of D2's.

    Contract (the revert, developer 19/10: «non devi filtrare … gli utenti possono … modificare … a mano»): the subquery
    counts every stored row again, so the latest row on or before ``as_of`` — D2's — is the pair's saved row: its date,
    its rate as the column reads it back (a REAL inf is ``Decimal('Infinity')``), its source.
    """
    story = f"{XR45_PAIR} 2.5 on {XR45_D1} and a legacy {unusable!r} on {XR45_D2}, as of {as_of}"
    print_section(f"X-R45 reverted: the planner's latest saved row, {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_D1_RATE), XR45_D2: unusable})

    rows = await source_fx_quotes._load_latest_planner_fx_rows(session, directed_pairs=[(XR45_BASE, XR45_QUOTE)], as_of=as_of)

    found = {pair: (row.date, row.rate, row.source) for pair, row in rows.items()}
    expected = {(XR45_BASE, XR45_QUOTE): (XR45_D2, read_back, _xr45_source(XR45_D2))}
    assert found == expected, f"{story}: the latest saved row is {found}, expected {expected} — the latest stored one, as stored (X-R45 reverted)"
    print_success(f"{story}: D2's row, {read_back}")


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of", XR45_AS_OF)
@pytest.mark.parametrize("skipped", XR45B_SKIPPED)
async def test_xr45b_a_zero_or_infinite_latest_planner_fx_rate_falls_back_to_the_previous_valid_one(session, skipped, as_of):
    """RED until X-R45b: ``build_planner_fx_quotes`` quotes the latest row as it is. A 0 on D2 takes the ``rate > 0 else
    None`` branch — no rate and the error ``allocation.saved_fx_invalid``, though D1 holds 2.5 —; an inf passes
    ``rate > 0`` and the quote's schema refuses it (pydantic ``finite_number``), so the builder raises: a 500.

    Contract (X-R45b, developer 19/10: «Sì: tasso valido precedente con l'avviso, e lo 0 trattato allo stesso modo»): the
    latest row on or before ``as_of`` is skipped when its rate is 0 or not finite, and the quote is the previous valid
    row's (finite and > 0), D1's — its id, 2.5 as read back, reference date D1, its source, its age from D1 —, with
    exactly one issue: the warning ``allocation.saved_fx_skipped`` (kind ``invalid``) about that quote, its params the
    pair, ``skipped_date`` D2 and ``used_date`` D1. No ``allocation.saved_fx_invalid``. The neighbouring pairs' valid
    rates on the day between D1 and D2 are not ERN/STN's.
    """
    story = f"the planner quote of {XR45_PAIR} as of {as_of}, 2.5 on {XR45_D1} and a legacy {skipped!r} on {XR45_D2}"
    print_section(f"X-R45b: {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_D1_RATE), XR45_D2: skipped})
    await _xr45b_plant_decoys(session)
    issues: list = []

    quotes = await _xr45_quotes(session, issues, story, as_of=as_of)

    quote_id = _xr45_assert_quote(quotes, as_of, XR45_D1, XR45_D1_RATE, story)
    found = _xr45_issue_shapes(issues)
    expected = [_xr45b_skipped_warning(quote_id, skipped=XR45_D2, used=XR45_D1)]
    assert found == expected, f"{story} reports {found}: expected {expected}, one warning, D2 skipped for D1 (X-R45b)"
    print_success(f"{story}: D1's 2.5, one saved_fx_skipped warning")


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of", XR45B_RUN_AS_OF)
@pytest.mark.parametrize(("on_d2", "on_d3"), XR45B_RUNS)
async def test_xr45b_several_unusable_planner_fx_rates_in_a_row_fall_back_to_the_previous_valid_one(session, on_d2, on_d3, as_of):
    """RED until X-R45b: the quote is D3's row as it is — an inf on D3 makes the builder raise; a 0 on D3 gives no rate
    and the error ``allocation.saved_fx_invalid``.

    Contract (X-R45b, «Sì: tasso valido precedente con l'avviso, e lo 0 trattato allo stesso modo»): the look-back goes
    as many rows as it takes. D3 and D2 skipped, whichever holds the 0 and whichever the inf, the quote is D1's 2.5, and
    there is ONE warning ``allocation.saved_fx_skipped`` about it, ``skipped_date`` D3 — the most recent row skipped —
    and ``used_date`` D1. No ``allocation.saved_fx_invalid``.
    """
    story = f"the planner quote of {XR45_PAIR} as of {as_of}, 2.5 on {XR45_D1}, a legacy {on_d2!r} on {XR45_D2} and {on_d3!r} on {XR45_D3}"
    print_section(f"X-R45b: {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_D1_RATE), XR45_D2: on_d2, XR45_D3: on_d3})
    await _xr45b_plant_decoys(session)
    issues: list = []

    quotes = await _xr45_quotes(session, issues, story, as_of=as_of)

    quote_id = _xr45_assert_quote(quotes, as_of, XR45_D1, XR45_D1_RATE, story)
    found = _xr45_issue_shapes(issues)
    expected = [_xr45b_skipped_warning(quote_id, skipped=XR45_D3, used=XR45_D1)]
    assert found == expected, f"{story} reports {found}: expected {expected}, one warning, D3 the most recent skipped, D1 used (X-R45b)"
    print_success(f"{story}: D1's 2.5, one warning naming {XR45_D3}")


@pytest.mark.asyncio
@pytest.mark.parametrize(("unusable", "read_back"), XR45_UNUSABLE)
async def test_xr45_reverted_a_planner_fx_pair_whose_only_saved_rate_is_unusable_has_that_row(session, unusable, read_back):
    """RED until the X-R45 revert: the clause leaves the ``max(date)`` subquery without a row for the pair, so it has no
    saved row at all.

    Contract (the revert): the pair's only stored row is its latest saved row, whatever its rate — D2, its rate as read
    back (0, ``Decimal('Infinity')``, 1E+14), its source.
    """
    story = f"{XR45_PAIR} whose only rate is a legacy {unusable!r} on {XR45_D2}, as of {XR45_LATER}"
    print_section(f"X-R45 reverted: the planner's latest saved row, {story}")
    await _xr45_plant(session, {XR45_D2: unusable})

    rows = await source_fx_quotes._load_latest_planner_fx_rows(session, directed_pairs=[(XR45_BASE, XR45_QUOTE)], as_of=XR45_LATER)

    found = {pair: (row.date, row.rate, row.source) for pair, row in rows.items()}
    expected = {(XR45_BASE, XR45_QUOTE): (XR45_D2, read_back, _xr45_source(XR45_D2))}
    assert found == expected, f"{story}: the saved rows are {found}, expected {expected} — the only stored row, as stored (X-R45 reverted)"
    print_success(f"{story}: D2's row, {read_back}")


async def _xr45b_assert_invalid_from_the_latest_row(session: AsyncSession, rates: dict[date, float], story: str) -> None:
    """``rates`` planted for ERN/STN, none valid, beside the decoys: the quote as of ``XR45_LATER`` is the latest row's,
    with no rate, and its one issue the error ``allocation.saved_fx_invalid`` about it — no warning."""
    await _xr45_plant(session, rates)
    await _xr45b_plant_decoys(session)
    issues: list = []

    quotes = await _xr45_quotes(session, issues, story)

    latest = max(rates)
    quote_id = _xr45_assert_quote(quotes, XR45_LATER, latest, None, story)
    found = _xr45_issue_shapes(issues)
    expected = [_xr45_invalid_error(quote_id)]
    assert found == expected, f"{story} reports {found}: expected {expected}, the error of the latest row's quote, no warning"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rates",
    [
        pytest.param({XR45_D2: float("inf")}, id="inf-alone"),
        pytest.param({XR45_D1: 0.0, XR45_D2: float("inf")}, id="0-then-inf"),
    ],
)
async def test_xr45b_a_planner_fx_pair_with_no_valid_rate_is_invalid_from_its_latest_row(session, rates):
    """RED until X-R45b: the latest row, D2, holds an inf: it passes ``rate > 0``, the quote's schema refuses it, and the
    builder raises — a 500.

    Contract (X-R45b, «Sì: tasso valido precedente con l'avviso, e lo 0 trattato allo stesso modo»): no row before D2 is
    valid (none, or a 0), so the look-back finds nothing and today's error stands, for an infinite rate too: the quote of
    the latest row, D2 — its id, reference date, source and age —, with no rate, and the one issue
    ``allocation.saved_fx_invalid`` about it. No ``allocation.saved_fx_skipped``.
    """
    story = f"the planner quote of {XR45_PAIR} as of {XR45_LATER}, its saved rates {rates}"
    print_section(f"X-R45b: {story}")

    await _xr45b_assert_invalid_from_the_latest_row(session, rates, story)
    print_success(f"{story}: D2's quote, no rate, saved_fx_invalid")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rates",
    [
        pytest.param({XR45_D2: 0.0}, id="0-alone"),
        pytest.param({XR45_D1: float("inf"), XR45_D2: 0.0}, id="inf-then-0"),
    ],
)
async def test_xr45b_guard_a_pair_whose_latest_rate_is_zero_and_none_valid_before_is_invalid(session, rates):
    """Guard: green before and after X-R45b. The latest row, D2, holds a 0, and no row before it is valid (none, or an
    inf): before X-R45b the ``rate > 0 else None`` branch; after it, a look-back that finds nothing. Either way the quote
    of the latest row, D2, with no rate, and the one issue ``allocation.saved_fx_invalid`` about it — never the inf of
    D1, never a decoy's rate, no warning."""
    story = f"the planner quote of {XR45_PAIR} as of {XR45_LATER}, its saved rates {rates}"
    print_section(f"X-R45b guard: {story}")

    await _xr45b_assert_invalid_from_the_latest_row(session, rates, story)
    print_success(f"{story}: D2's quote, no rate, saved_fx_invalid")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rates",
    [
        pytest.param({XR45_D1: float(XR45_D1_RATE), XR45_D2: 1e14}, id="over-2.5"),
        pytest.param({XR45_D2: 1e14}, id="alone"),
    ],
)
async def test_xr45b_guard_a_finite_planner_fx_rate_from_1e14_up_is_quoted_as_read_back(session, rates):
    """Guard: green before and after X-R45b. A finite rate from 1E+14 up, past X-R38's bounds, is a value to the planner's
    quote: 1E+14 on D2, over D1's 2.5 or alone, gives D2's quote with 1E+14 as read back, and no issue — X-R45b skips 0
    and what is not finite, nothing else."""
    story = f"the planner quote of {XR45_PAIR} as of {XR45_LATER}, its saved rates {rates}"
    print_section(f"X-R45b guard: {story}")
    await _xr45_plant(session, rates)
    issues: list = []

    quotes = await _xr45_quotes(session, issues, story)

    _xr45_assert_quote(quotes, XR45_LATER, XR45_D2, Decimal("1E+14"), story)
    assert _xr45_issue_shapes(issues) == [], f"{story} reports {_xr45_issue_shapes(issues)}: expected none"
    print_success(f"{story}: D2's 1E+14, no issue")


def test_xr45b_saved_fx_skipped_is_a_source_issue_code_and_not_a_tool_issue_code():
    """RED until X-R45b: ``PortfolioPlannerSourceIssueCode`` (``schemas/portfolio.py``) has no
    ``allocation.saved_fx_skipped``, so no issue can carry it.

    Contract (X-R45b): the allocation-source API's codes gain it; the tool's ``PlannerIssueCode``
    (``schemas/pac_allocator/base.py``, the versioned contract of the ``pac_allocator`` tool) does not: a source-only code,
    as ``allocation.saved_fx_missing`` is (``test_pac_planner_schemas.py`` keeps those out of the tool on purpose).
    """
    print_section("X-R45b: allocation.saved_fx_skipped among the source issue codes, not the tool's")
    source_codes, tool_codes = get_args(PortfolioPlannerSourceIssueCode), get_args(PlannerIssueCode)

    assert "allocation.saved_fx_skipped" in source_codes, f"PortfolioPlannerSourceIssueCode is {source_codes}: expected allocation.saved_fx_skipped among them (X-R45b)"
    assert "allocation.saved_fx_skipped" not in tool_codes, "PlannerIssueCode has allocation.saved_fx_skipped: the tool contract stays unchanged, the code is the source's alone (X-R45b)"
    print_success("allocation.saved_fx_skipped: a source issue code, not a tool one")


@pytest.mark.asyncio
@pytest.mark.parametrize(("latest", "read_back"), XR45_USABLE)
async def test_xr45_guard_the_latest_usable_planner_fx_rate_wins(session, latest, read_back):
    """Guard: green before and after the X-R45 revert. With 2.5 on D1 and a usable ``latest`` on D2 — an ordinary 4, and
    the two bounds 1E-10 and 99999999999999 — the latest row is D2's and the quote is its rate, with no issue: with
    X-R45's clause or without it, nothing a read may use is skipped."""
    story = f"{XR45_PAIR} 2.5 on {XR45_D1} and {latest!r} on {XR45_D2}, as of {XR45_LATER}"
    print_section(f"X-R45 guard: the latest usable rate wins, {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_D1_RATE), XR45_D2: latest})
    issues: list = []

    rows = await source_fx_quotes._load_latest_planner_fx_rows(session, directed_pairs=[(XR45_BASE, XR45_QUOTE)], as_of=XR45_LATER)
    quotes = await _xr45_quotes(session, issues, story)

    found_rows = {pair: (row.date, row.rate) for pair, row in rows.items()}
    assert found_rows == {(XR45_BASE, XR45_QUOTE): (XR45_D2, read_back)}, f"{story}: the latest saved row is {found_rows}, expected D2's {read_back}"
    found = [(quote.rate, quote.reference_date, quote.source) for quote in quotes]
    assert found == [(read_back, XR45_D2, _xr45_source(XR45_D2))], f"{story}: the quote is {found}, expected D2's {read_back}"
    assert issues == [], f"{story} reports {[issue.code for issue in issues]}: expected none"
    print_success(f"{story}: D2's {read_back}")


XR45_WAC_RATE = Decimal("1.25")


@pytest.mark.asyncio
@pytest.mark.parametrize(("unusable", "read_back"), XR45_UNUSABLE)
async def test_xr45_reverted_wac_fx_evidence_reads_the_stored_row_of_its_exact_date(session, unusable, read_back):
    """RED until the X-R45 revert: ``usable_fx_rate_clause()`` in the select of ``_load_wac_fx_rows`` drops D2's row, so
    the key of D2 has none.

    Contract (the revert): each exact (base, quote, date) key gets its stored row, whatever the rate — D2's 0, inf or
    1E+14 as the column reads it back, with its source —, and D1's usable 1.25 beside it. The read only: what the WAC
    makes of such a row next is not pinned here (MF's review of X-R45: the keys are the days ``convert_bulk`` chose among
    the usable rates, so the clause there was defensive; a 0 is still turned away by ``saved_row.rate > 0``).
    """
    story = f"the WAC evidence of {XR45_PAIR} on {XR45_D1} (1.25) and {XR45_D2} (a legacy {unusable!r})"
    print_section(f"X-R45 reverted: {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_WAC_RATE), XR45_D2: unusable})
    keys = {(XR45_BASE, XR45_QUOTE, XR45_D1), (XR45_BASE, XR45_QUOTE, XR45_D2)}

    rows = await source_wac._load_wac_fx_rows(session, keys=keys)

    found = {key: (row.date, row.rate, row.source) for key, row in rows.items()}
    expected = {
        (XR45_BASE, XR45_QUOTE, XR45_D1): (XR45_D1, XR45_WAC_RATE, _xr45_source(XR45_D1)),
        (XR45_BASE, XR45_QUOTE, XR45_D2): (XR45_D2, read_back, _xr45_source(XR45_D2)),
    }
    assert found == expected, f"{story} reads {found}: expected {expected}, each key's stored row as stored (X-R45 reverted)"
    print_success(f"{story}: both rows, D2's {read_back}")


@pytest.mark.asyncio
@pytest.mark.parametrize(("usable", "read_back"), XR45_USABLE)
async def test_xr45_guard_wac_fx_evidence_reads_a_usable_saved_rate_on_its_exact_date(session, usable, read_back):
    """Guard: green before and after. A usable rate on the key's exact date — an ordinary 4, and the two bounds 1E-10 and
    99999999999999 — comes back as the key's row; D1's row, not asked for, stays out."""
    story = f"the WAC evidence of {XR45_PAIR} on {XR45_D2} ({usable!r})"
    print_section(f"X-R45 guard: {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_WAC_RATE), XR45_D2: usable})

    rows = await source_wac._load_wac_fx_rows(session, keys={(XR45_BASE, XR45_QUOTE, XR45_D2)})

    found = {key: (row.rate, row.source) for key, row in rows.items()}
    assert found == {(XR45_BASE, XR45_QUOTE, XR45_D2): (read_back, _xr45_source(XR45_D2))}, f"{story} reads {found}: expected D2's {read_back}"
    print_success(f"{story}: {read_back}")


#: The two readers the revert keeps filtered (``convert_bulk``, X-R38; ``fx/period_changes._first_rate_days_inside``,
#: X-R59), on the nine cases of the clause test the revert deletes
#: (``test_usable_fx_rate_gate.py::test_usable_fx_rate_clause_keeps_what_a_read_may_use_and_drops_the_rest``), so no
#: case loses its only test: (the rate planted on D2, as SQLite binds it; the Decimal ``fx_rates.rate`` reads back when the
#: bounds let it through, None when they skip it).
XR45_BOUNDS = [
    pytest.param(1e-10, Decimal("1E-10"), id="smallest-1E-10"),
    pytest.param(1.5, Decimal("1.5"), id="ordinary-1.5"),
    pytest.param(99999999999999.0, Decimal("99999999999999"), id="largest-99999999999999"),
    pytest.param(0.0, None, id="0"),  # a manual 1E-11, truncated to the column's 10 decimals
    pytest.param(1e-11, None, id="1E-11"),  # a REAL another tool wrote: it reads back 0
    pytest.param(-1.5, None, id="negative-1.5"),
    pytest.param(float("inf"), None, id="inf"),  # 1E+400, written as an SQLite REAL
    pytest.param(1e14, None, id="first-refused-1E+14"),
    pytest.param(1e19, None, id="1E+19"),  # X-R38's rate of 20 digits before the decimal point
]
XR45_LATER_RATE = Decimal("4")


@pytest.mark.asyncio
@pytest.mark.parametrize(("planted", "read_back"), XR45_BOUNDS)
async def test_xr45_guard_convert_bulk_still_reads_only_rates_within_the_usable_bounds(session, planted, read_back):
    """Guard: green before and after the X-R45 revert. ``convert_bulk`` keeps X-R38's ``usable_fx_rate_bounds()`` — through
    ``usable_fx_rate_clause()`` today, inline after the revert («I due lettori devono restare come prima di X-R45, quindi
    ancora filtrati») —, in its backward-fill anchor and in its window.

    ERN/STN 2.5 on D1, ``planted`` on D2, 4 on LATER; 1 ERN converted to STN on D2 and on LATER. Within the bounds D2
    converts at its own rate, on its own day. Outside them D2 is a missing rate, backward-filled from D1's 2.5: an anchor
    that counted D2 would start the window on D2 and leave D2 with no rate; a window that kept D2 would convert at it.
    LATER converts at its 4 either way.
    """
    story = f"1 {XR45_BASE} to {XR45_QUOTE} on {XR45_D2} and {XR45_LATER}, 2.5 on {XR45_D1}, {planted!r} on {XR45_D2}, 4 on {XR45_LATER}"
    print_section(f"X-R45 guard: convert_bulk, {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_D1_RATE), XR45_D2: planted, XR45_LATER: float(XR45_LATER_RATE)})
    one = Currency(code=XR45_BASE, amount=Decimal(1))

    results, errors = await convert_bulk(session, [(one, XR45_QUOTE, XR45_D2), (one, XR45_QUOTE, XR45_LATER)], raise_on_error=False)

    found = [None if result is None else (result[0].code, result[0].amount, result[1], result[2]) for result in results]
    on_d2 = (XR45_QUOTE, read_back, XR45_D2, False) if read_back is not None else (XR45_QUOTE, XR45_D1_RATE, XR45_D1, True)
    expected = [on_d2, (XR45_QUOTE, XR45_LATER_RATE, XR45_LATER, False)]
    assert (found, errors) == (expected, []), f"{story} converted as {found}, errors {errors}: expected {expected}, X-R38's bounds in the anchor and the window"
    print_success(f"{story}: {on_d2[1]} of {on_d2[2]} on {XR45_D2}")


@pytest.mark.asyncio
@pytest.mark.parametrize(("planted", "read_back"), XR45_BOUNDS)
async def test_xr45_guard_first_rate_days_inside_still_reads_only_rates_within_the_usable_bounds(session, planted, read_back):
    """Guard: green before and after the X-R45 revert. ``_first_rate_days_inside`` (the period changes' range reference,
    X-R59) keeps X-R38's ``usable_fx_rate_bounds()`` — through ``usable_fx_rate_clause()`` today, inline after the revert.

    ERN/STN 2.5 on D1, ``planted`` on D2, 4 on LATER; the pair's first rate day inside (D1, LATER]. Within the bounds it
    is D2; outside them D2 is skipped, and it is LATER, the first usable one.
    """
    story = f"the first {XR45_PAIR} rate day inside ({XR45_D1}, {XR45_LATER}], {planted!r} on {XR45_D2} and 4 on {XR45_LATER}"
    print_section(f"X-R45 guard: _first_rate_days_inside, {story}")
    await _xr45_plant(session, {XR45_D1: float(XR45_D1_RATE), XR45_D2: planted, XR45_LATER: float(XR45_LATER_RATE)})

    first_days = await fx_period_changes._first_rate_days_inside(session, {(XR45_BASE, XR45_QUOTE)}, XR45_D1, XR45_LATER)

    expected = {(XR45_BASE, XR45_QUOTE): XR45_D2 if read_back is not None else XR45_LATER}
    assert first_days == expected, f"{story} is {first_days}: expected {expected}, X-R38's bounds"
    print_success(f"{story}: {expected[(XR45_BASE, XR45_QUOTE)]}")
