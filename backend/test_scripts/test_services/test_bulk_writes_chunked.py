"""MF-SEC9a (E's review of R13-SEC9) — the bulk writes of rates and prices run in chunks SQLite can parse, under a cap,
and a failure never echoes its error.

The defect, on HEAD 04955c498. SQLite parses ``a OR b OR c …`` as a chain one level deeper per term and refuses a chain
of a thousand («Expression tree is too large (maximum depth 1000)»). Four statements had one OR term per item:

- ``fx/storage.upsert_rates_bulk`` read the stored keys of every rate in ONE statement: from about 1 000 rates it raised
  ``OperationalError``;
- ``fx/storage.delete_rates_bulk`` read the rates matching every deletion in ONE statement: the same, and
  ``DELETE /fx/currencies/rate`` answered 500 — the FX page sends one deletion per run of consecutive days, so deleting
  more than 1 000 separate days failed, the 500 echoing the SQL;
- ``PriceStoreOperations.bulk_delete_prices`` deleted every range in ONE statement: ``DELETE /assets/prices`` the same;
- ``fx/sync.ensure_rates_multi_source`` read the stored rates of every pair in ONE statement: 46 currencies make 1 035
  pairs, the refusal was caught as «table may not exist» and every fetched rate was counted as a change.

None of these routes had a cap, and their failures echoed ``str(e)``: an SQL error names the schema.

The cure's contract, pinned here:

1. ``utils/sql_chunks.chunks(items, size=500)``: consecutive slices of at most ``size``, in order, the last one partial;
   nothing for an empty sequence; ``ValueError`` for a size under 1. ``fx/conversion.FX_PAIRS_PER_QUERY`` is the same 500.
2. ``upsert_rates_bulk`` with 1 500 rates over three pairs — one given in storage order, two inverted (the pair swapped,
   the rate inverted) — stores every rate at its value and answers ``inserted`` for each; called again with new values,
   ``updated`` for each and every value replaced.
3. ``delete_rates_bulk`` with 1 500 single days and four ranges answers each deletion its exact counts — a range counts
   its own pair's rates only, a pair without rates 0 — and every other rate stays stored.
4. ``bulk_delete_prices`` with 1 500 ranges over two assets: ``total_deleted`` and each asset's count exact, every other
   price kept, a third asset's untouched.
5. ``fx/sync._stored_rates`` reads every rate matching 1 500 conditions; ``ensure_rates_multi_source`` over 46 currencies
   (1 035 pairs) counts as changed only the fetched rates that are new or differ from the stored ones.
6. The routes, their coroutines called directly: ``DELETE /fx/currencies/rate`` with 1 500 separate days answers 200
   with exact counts; ``POST /fx/currencies/rate`` with 1 500 rates stores them all. More than 10 000 items — rates,
   deletions, or the date ranges of ``DELETE /assets/prices``, every asset's together — answer 422
   ``{"code": "bulk_too_many_items", "message", "max_items": 10000, "items": n}`` before the service is called or the
   session touched; exactly 10 000 pass.
7. A failure never echoes its error: the 500s of ``POST /assets/prices``, ``DELETE /assets/prices``,
   ``POST /assets/prices/sync`` and of the FX bulk deletion, and the per-item error texts of the FX upsert and of an FX
   «delete all» (in a 200, and in the 400 when every item failed) hold none of the SQL; the error is logged, with its
   exception. ``POST /assets/prices``' 400 for a ``ValueError`` keeps its domain message (guard).

The cases of 2-4 also run at 500 and 501 OR terms, the edge of one chunk. The barrier,
``test_barrier_this_sqlite_refuses_one_or_of_1500_terms``, proves the SQLite these tests run on answers one OR of 500
terms and refuses one of 1 500: without it a build with a higher limit would let the import-sized cases pass untested.

Red on HEAD 04955c498:

- ``test_chunks_*`` (every case): no ``utils/sql_chunks.py``;
- ``test_upsert_rates_bulk_stores_every_rate_of_an_import[1500-import-sized]``,
  ``test_delete_rates_bulk_counts_each_deletion_of_an_import[1504-import-sized]``,
  ``test_bulk_delete_prices_deletes_every_range_of_an_import[1500-import-sized]``: ``OperationalError``, «Expression
  tree is too large»;
- ``test_stored_rates_reads_every_rate_matching_1500_conditions``: no ``_stored_rates`` in ``fx/sync.py``;
- ``test_sync_change_detection_holds_over_1035_pairs``: ``total_changed`` 45, every fetched rate counted as new;
- ``test_fx_delete_route_answers_1500_separate_days``: 500;
- ``test_more_than_10000_items_refused_before_any_write`` (every case): no cap, the service called with every item;
- ``test_a_failure_never_echoes_its_error`` (every case): the SQL in the detail or the error text.

Green before and after (guards): the barrier; the cases of 2-4 at 500 and 501 OR terms (under SQLite's limit);
``test_guard_fx_upsert_route_stores_1500_rates`` (the route upserts one rate at a time, so an import of any size passed);
``test_guard_exactly_10000_items_pass``; ``test_guard_post_prices_value_error_keeps_its_domain_message``.

Isolation: PURE — no lane database, no server, no network. Each test that stores anything has its own in-memory SQLite
database (``SQLModel.metadata.create_all``), closed and disposed at teardown; the services, the provider lookup and the
route modules' loggers are replaced for the test only (``monkeypatch``); the sessions the cap and failure cases hand the
routes are stand-ins that store nothing.

Reference: backend/app/utils/sql_chunks.py, backend/app/services/fx/storage.py (upsert_rates_bulk, delete_rates_bulk),
backend/app/services/assets/price_store.py (bulk_delete_prices), backend/app/services/fx/sync.py (_stored_rates,
ensure_rates_multi_source), backend/app/api/v1/fx/currencies.py (upsert_rates_endpoint, delete_rates_endpoint),
backend/app/api/v1/assets/prices.py (upsert_prices_bulk, delete_prices_bulk, sync_prices_bulk).
"""

from __future__ import annotations

import importlib
import sys
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import and_, insert, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.api.v1.assets import prices
from backend.app.api.v1.fx import currencies
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, FxRate, PriceHistory
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.fx import FXDeleteItem, FXUpsertItem
from backend.app.schemas.prices import FAAssetDelete, FABulkDeleteResponse, FAPriceDeleteResult, FAPricePoint, FAUpsert
from backend.app.schemas.refresh import FARefreshItem, SyncDateRangeModel
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.fx import conversion as fx_conversion
from backend.app.services.fx import sync as fx_sync
from backend.app.services.fx.storage import delete_rates_bulk, upsert_rates_bulk
from backend.test_scripts.test_utils import print_section, print_success

CHUNK = 500  # OR_TERMS_PER_QUERY: the contract's number, written here and not read from the module under test
MAX_WRITE_ITEMS = 10_000  # MAX_BULK_WRITE_ITEMS, written here as well
IMPORT_SIZED = 1_500  # items of one import-sized request: past SQLite's limit, past two chunk boundaries
#: The first day of every series: far enough back that 10 000 daily items end before today, inside the stored bounds
#: (X-R65: a rate dated after tomorrow is refused before the write).
DAY0 = date(1990, 1, 1)
FETCHED_AT = datetime(2025, 1, 1)
SOURCE = "SEC9a"
#: What a failing service raises in the failure cases: an SQL error names the schema.
LEAK = "SELECT secret_column FROM secret_table"
LEAK_WORDS = ("SELECT", "secret", "FROM")
#: 46 ISO 4217 codes ``Currency.validate_code`` accepts, in alphabetical order: 1 035 pairs.
CODES = (
    "AED", "ARS", "AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "COP", "CZK", "DKK", "EGP", "EUR", "GBP", "HKD", "HUF",
    "IDR", "ILS", "INR", "ISK", "JPY", "KES", "KRW", "MAD", "MXN", "MYR", "NGN", "NOK", "NZD", "PEN", "PHP", "PKR",
    "PLN", "QAR", "RON", "RSD", "SAR", "SEK", "SGD", "THB", "TRY", "TWD", "UAH", "USD", "VND", "ZAR",
)  # fmt: skip


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


async def _seed_fx(session: AsyncSession, rows: Iterable[tuple[date, str, str, Decimal]]) -> None:
    """Rates as stored (base < quote), one statement per row (``executemany``): no OR, no variable limit."""
    values = [{"date": day, "base": base, "quote": quote, "rate": rate, "source": SOURCE, "fetched_at": FETCHED_AT} for day, base, quote, rate in rows]
    await session.execute(insert(FxRate), values)
    await session.commit()


async def _stored_fx(session: AsyncSession) -> dict[tuple[date, str, str], Decimal]:
    """Every stored rate of this private database, by (date, base, quote)."""
    result = await session.execute(select(FxRate.date, FxRate.base, FxRate.quote, FxRate.rate))
    return {(row.date, row.base, row.quote): row.rate for row in result.all()}


def _differences(actual: dict, expected: dict, limit: int = 5) -> str:
    """What differs between two dicts, a few keys of each kind: a 1 500-entry diff says nothing."""
    missing = [key for key in expected if key not in actual]
    extra = [key for key in actual if key not in expected]
    wrong = [(key, actual[key], expected[key]) for key in expected if key in actual and actual[key] != expected[key]]
    return f"{len(missing)} missing {missing[:limit]}, {len(extra)} unexpected {extra[:limit]}, {len(wrong)} with another value (key, got, expected) {wrong[:limit]}"


def _refused_by_sqlite(error: OperationalError, what: str, terms: int) -> None:
    pytest.fail(f"{what} raised for {terms} OR terms, SQLite refusing the statement: {error.orig!r} — a 500 on the route (MF-SEC9a)")


#: The service cases: one chunk exactly, one term past it, and the size of an import.
OR_TERM_COUNTS = [
    pytest.param(CHUNK, id="500-one-chunk"),
    pytest.param(CHUNK + 1, id="501-two-chunks"),
    pytest.param(IMPORT_SIZED, id="1500-import-sized"),
]


# =============================================================================
# 1. chunks()
# =============================================================================


def _sql_chunks() -> ModuleType:
    """``backend.app.utils.sql_chunks``, imported here: on code without it only these cases fail, not the file."""
    try:
        return importlib.import_module("backend.app.utils.sql_chunks")
    except ModuleNotFoundError as error:
        pytest.fail(f"no backend/app/utils/sql_chunks.py: {error}")


@pytest.mark.parametrize(
    ("count", "size", "lengths"),
    [
        pytest.param(1_201, 500, [500, 500, 201], id="1201-by-500-last-partial"),
        pytest.param(1_500, 500, [500, 500, 500], id="1500-by-500-no-partial"),
        pytest.param(7, 3, [3, 3, 1], id="7-by-3"),
        pytest.param(4, 1, [1, 1, 1, 1], id="size-1"),
        pytest.param(3, 10, [3], id="fewer-than-size"),
    ],
)
def test_chunks_are_consecutive_slices_in_order(count, size, lengths):
    """``chunks(items, size)``: slices of ``size`` items, the last one partial; joined, they are ``items`` in order."""
    sql_chunks = _sql_chunks()
    items = [f"term-{index}" for index in range(count)]
    slices = [list(chunk) for chunk in sql_chunks.chunks(items, size)]
    assert [len(chunk) for chunk in slices] == lengths
    assert [item for chunk in slices for item in chunk] == items


def test_chunks_default_to_500_terms_shared_with_the_fx_queries():
    """Without a size, slices of 500 (``OR_TERMS_PER_QUERY``); ``FX_PAIRS_PER_QUERY`` is the same number."""
    sql_chunks = _sql_chunks()
    assert sql_chunks.OR_TERMS_PER_QUERY == CHUNK
    assert [len(chunk) for chunk in sql_chunks.chunks(list(range(2 * CHUNK + 1)))] == [CHUNK, CHUNK, 1]
    assert fx_conversion.FX_PAIRS_PER_QUERY == CHUNK


@pytest.mark.parametrize("size", [None, 1, CHUNK], ids=["default-size", "size-1", "size-500"])
def test_chunks_of_nothing_is_nothing(size):
    """An empty sequence gives no slice at all: not one empty slice, which would run a statement with no condition."""
    sql_chunks = _sql_chunks()
    slices = list(sql_chunks.chunks([]) if size is None else sql_chunks.chunks([], size))
    assert slices == []


@pytest.mark.parametrize("size", [0, -1], ids=["size-0", "size-negative"])
def test_chunks_refuse_a_size_under_1(size):
    """A size under 1 raises ``ValueError``: it would never advance."""
    sql_chunks = _sql_chunks()
    with pytest.raises(ValueError):
        list(sql_chunks.chunks([1, 2, 3], size))


# =============================================================================
# THE BARRIER: THIS SQLITE ANSWERS ONE OR OF 500 TERMS AND REFUSES ONE OF 1 500
# =============================================================================


def _one_or_of_rate_keys(terms: int):
    return select(FxRate.id).where(or_(*(and_(FxRate.date == _day(offset), FxRate.base == "EUR", FxRate.quote == "USD") for offset in range(terms))))


@pytest.mark.asyncio
async def test_barrier_this_sqlite_refuses_one_or_of_1500_terms(session):
    """Barrier: one statement with an OR of 500 rate keys, a chunk, is answered; one of 1 500, the shape before the cure,
    is refused «Expression tree is too large».

    Green before and after: it tests SQLite, so that «no raise» in the import-sized cases means the chunks.
    """
    print_section("MF-SEC9a barrier: one OR of 500 terms, then of 1 500")
    result = await session.execute(_one_or_of_rate_keys(CHUNK))
    assert result.all() == []

    with pytest.raises(OperationalError, match="Expression tree is too large"):
        await session.execute(_one_or_of_rate_keys(IMPORT_SIZED))
    print_success("500 terms answered; 1 500 refused, Expression tree is too large")


# =============================================================================
# 2. upsert_rates_bulk()
# =============================================================================

#: (given base, given quote, stored base, stored quote, inverted): the pair as sent and as ``fx_rates`` keeps it.
UPSERT_PAIRS = (
    ("EUR", "USD", "EUR", "USD", False),
    ("USD", "CHF", "CHF", "USD", True),
    ("JPY", "GBP", "GBP", "JPY", True),
)


def _upsert_rows(count: int, *, again: bool) -> tuple[list[tuple[date, str, str, Decimal, str]], dict[tuple[date, str, str], Decimal]]:
    """``count`` rates, one per (day, pair) over the three ``UPSERT_PAIRS`` in turn, and the value each must be stored at.

    A value of its own per rate where the pair is sent in storage order ((i + 1) / 100, plus 1 000 ``again``); a power of
    2 (5 ``again``) stored where the pair is inverted, sent as its inverse: both ways exact, so the stored value is known
    without the code under test.
    """
    rows: list[tuple[date, str, str, Decimal, str]] = []
    expected: dict[tuple[date, str, str], Decimal] = {}
    for index in range(count):
        given_base, given_quote, base, quote, inverted = UPSERT_PAIRS[index % len(UPSERT_PAIRS)]
        day = _day(index // len(UPSERT_PAIRS))
        if inverted:
            stored = Decimal(5 ** (index % 10)) if again else Decimal(2 ** (index % 16))
            given = Decimal(1) / stored
        else:
            stored = Decimal(index + 1) / 100 + (1_000 if again else 0)
            given = stored
        rows.append((day, given_base, given_quote, given, SOURCE))
        expected[(day, base, quote)] = stored
    assert len(expected) == count, "one rate per (day, pair)"
    return rows, expected


@pytest.mark.asyncio
@pytest.mark.parametrize("count", OR_TERM_COUNTS)
async def test_upsert_rates_bulk_stores_every_rate_of_an_import(session, count):
    """``upsert_rates_bulk`` with ``count`` rates, two pairs of three inverted: every rate stored at its value, each
    answered ``inserted``; called again with new values, each answered ``updated`` and every value replaced.

    Red on HEAD 04955c498 at 1 500: ``OperationalError`` «Expression tree is too large» (one OR of every rate's key).
    """
    print_section(f"MF-SEC9a: upsert_rates_bulk, {count} rates")
    rows, expected = _upsert_rows(count, again=False)
    try:
        results = await upsert_rates_bulk(session, rows)
    except OperationalError as error:
        _refused_by_sqlite(error, "upsert_rates_bulk", count)

    assert Counter(results) == {(True, "inserted"): count}, f"answers: {Counter(results)}"
    stored = await _stored_fx(session)
    assert stored == expected, _differences(stored, expected)

    rows, expected = _upsert_rows(count, again=True)
    results = await upsert_rates_bulk(session, rows)

    assert Counter(results) == {(True, "updated"): count}, f"answers the second time: {Counter(results)}"
    stored = await _stored_fx(session)
    assert stored == expected, _differences(stored, expected)
    print_success(f"{count} rates inserted, then updated, at their values")


# =============================================================================
# 3. delete_rates_bulk()
# =============================================================================

#: Single-day deletions per case: with the four ranges, 500, 501 and 1 504 OR terms.
DELETION_SINGLES = [
    pytest.param(CHUNK - 4, id="500-one-chunk"),
    pytest.param(CHUNK - 3, id="501-two-chunks"),
    pytest.param(IMPORT_SIZED, id="1504-import-sized"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("singles", DELETION_SINGLES)
async def test_delete_rates_bulk_counts_each_deletion_of_an_import(session, singles):
    """``delete_rates_bulk`` with ``singles`` single days — every other day of EUR/USD, half of them sent as USD/EUR — and
    four ranges: two inside a block of EUR/USD (10 and 5 days, the second sent inverted), one over days where only
    GBP/USD has rates, one of a pair without any rate. Each deletion answers its exact counts — 1, 10, 5, 0, 0 —, a
    message only where it found nothing; every other rate stays stored, GBP/USD whole.

    Red on HEAD 04955c498 at 1 504: ``OperationalError`` «Expression tree is too large» (one OR of every deletion).
    """
    terms = singles + 4
    print_section(f"MF-SEC9a: delete_rates_bulk, {terms} deletions")
    span = 2 * singles  # EUR/USD on every day of [0, span): the singles take the even ones
    block = span  # then a block of 40 more EUR/USD days, GBP/USD running 10 days further
    await _seed_fx(session, [*((_day(offset), "EUR", "USD", Decimal("1.1")) for offset in range(block + 40)), *((_day(offset), "GBP", "USD", Decimal("1.3")) for offset in range(block + 50))])
    deletions: list[tuple[str, str, date, date | None]] = [("EUR", "USD", _day(offset), None) if offset % 4 == 0 else ("USD", "EUR", _day(offset), None) for offset in range(0, span, 2)]
    deletions += [
        ("EUR", "USD", _day(block), _day(block + 9)),
        ("USD", "EUR", _day(block + 20), _day(block + 24)),
        ("EUR", "USD", _day(block + 40), _day(block + 49)),
        ("CHF", "JPY", _day(0), _day(block + 49)),
    ]
    assert len(deletions) == terms

    try:
        results = await delete_rates_bulk(session, deletions)
    except OperationalError as error:
        _refused_by_sqlite(error, "delete_rates_bulk", terms)

    counts = [(success, existing, deleted, message is None) for success, existing, deleted, message in results]
    expected_counts = [(True, 1, 1, True)] * singles + [(True, 10, 10, True), (True, 5, 5, True), (True, 0, 0, False), (True, 0, 0, False)]
    wrong = [(index, got, want) for index, (got, want) in enumerate(zip(counts, expected_counts, strict=False)) if got != want]
    assert len(counts) == terms and not wrong, f"{len(counts)} answers for {terms} deletions; (index, (success, existing, deleted, no message), expected): {wrong[:5]}"

    deleted_days = {*range(0, span, 2), *range(block, block + 10), *range(block + 20, block + 25)}
    expected = {(_day(offset), "EUR", "USD"): Decimal("1.1") for offset in range(block + 40) if offset not in deleted_days}
    expected.update({(_day(offset), "GBP", "USD"): Decimal("1.3") for offset in range(block + 50)})
    stored = await _stored_fx(session)
    assert stored == expected, _differences(stored, expected)
    print_success(f"{terms} deletions counted exactly, {singles + 15} rates deleted, {len(expected)} kept")


# =============================================================================
# 4. bulk_delete_prices()
# =============================================================================


async def _assets(session: AsyncSession, count: int) -> list[int]:
    assets = [Asset(display_name=f"SEC9a asset {index}", currency="EUR") for index in range(count)]
    session.add_all(assets)
    await session.commit()
    return [asset.id for asset in assets]


async def _stored_price_days(session: AsyncSession) -> set[tuple[int, date]]:
    result = await session.execute(select(PriceHistory.asset_id, PriceHistory.date))
    return {(row.asset_id, row.date) for row in result.all()}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("singles", "triples"),
    [
        pytest.param(333, 167, id="500-ranges-one-chunk"),
        pytest.param(334, 167, id="501-ranges-two-chunks"),
        pytest.param(1_000, 500, id="1500-ranges-import-sized"),
    ],
)
async def test_bulk_delete_prices_deletes_every_range_of_an_import(session, singles, triples):
    """``bulk_delete_prices`` with ``singles`` single days of asset A (every other day) and ``triples`` three-day ranges
    of asset B (days 4k to 4k + 2): ``total_deleted`` is ``singles + 3 × triples``, A's count ``singles``, B's
    ``3 × triples``; every other price stays stored, those of a third asset C all of them.

    Red on HEAD 04955c498 at 1 500 ranges: ``OperationalError`` «Expression tree is too large» (one DELETE ORing every
    range).
    """
    terms = singles + triples
    print_section(f"MF-SEC9a: bulk_delete_prices, {terms} ranges over two assets")
    days = max(2 * singles, 4 * triples)
    asset_a, asset_b, asset_c = await _assets(session, 3)
    values = [{"asset_id": asset_id, "date": _day(offset), "close": Decimal(offset + 1), "currency": "EUR", "source_plugin_key": SOURCE, "fetched_at": FETCHED_AT} for asset_id in (asset_a, asset_b, asset_c) for offset in range(days)]
    await session.execute(insert(PriceHistory), values)
    await session.commit()
    request = [
        FAAssetDelete(asset_id=asset_a, date_ranges=[DateRangeModel(start=_day(2 * k)) for k in range(singles)]),
        FAAssetDelete(asset_id=asset_b, date_ranges=[DateRangeModel(start=_day(4 * k), end=_day(4 * k + 2)) for k in range(triples)]),
    ]

    try:
        response = await AssetSourceManager.bulk_delete_prices(request, session)
    except OperationalError as error:
        _refused_by_sqlite(error, "bulk_delete_prices", terms)

    assert response.total_deleted == singles + 3 * triples, f"total_deleted {response.total_deleted}"
    assert sorted((result.asset_id, result.success, result.deleted_count) for result in response.results) == sorted([(asset_a, True, singles), (asset_b, True, 3 * triples)])
    expected = {(asset_a, _day(offset)) for offset in range(days) if not (offset % 2 == 0 and offset < 2 * singles)}
    expected |= {(asset_b, _day(offset)) for offset in range(days) if not (offset % 4 != 3 and offset < 4 * triples)}
    expected |= {(asset_c, _day(offset)) for offset in range(days)}
    stored = await _stored_price_days(session)
    assert stored == expected, f"{len(expected - stored)} prices deleted that should stay, e.g. {sorted(expected - stored)[:5]}; {len(stored - expected)} kept that should go, e.g. {sorted(stored - expected)[:5]}"
    print_success(f"{response.total_deleted} prices deleted over {terms} ranges, {len(expected)} kept")


# =============================================================================
# 5. fx/sync: _stored_rates() and the change detection of ensure_rates_multi_source()
# =============================================================================


@pytest.mark.asyncio
async def test_stored_rates_reads_every_rate_matching_1500_conditions(session):
    """``_stored_rates(session, conditions)`` with 1 500 single-day conditions on EUR/USD — every other day of 3 000 —
    answers exactly those 1 500 rates: none of the other days, none of GBP/USD's on the same days.

    Red on HEAD 04955c498: no ``_stored_rates`` in ``fx/sync.py`` (the read was one OR inside
    ``ensure_rates_multi_source``: the case below shows what that cost).
    """
    print_section("MF-SEC9a: fx/sync._stored_rates, 1 500 conditions")
    stored_rates = getattr(fx_sync, "_stored_rates", None)
    if stored_rates is None:
        pytest.fail("fx/sync.py has no _stored_rates: the stored rates are read in one OR of every pair")
    await _seed_fx(session, [(_day(offset), base, "USD", Decimal("1.2")) for base in ("EUR", "GBP") for offset in range(2 * IMPORT_SIZED)])
    conditions = [and_(FxRate.base == "EUR", FxRate.quote == "USD", FxRate.date >= _day(offset), FxRate.date <= _day(offset)) for offset in range(0, 2 * IMPORT_SIZED, 2)]

    try:
        rates = await stored_rates(session, conditions)
    except OperationalError as error:
        _refused_by_sqlite(error, "_stored_rates", len(conditions))

    read = Counter((rate.date, rate.base, rate.quote) for rate in rates)
    expected = Counter((_day(offset), "EUR", "USD") for offset in range(0, 2 * IMPORT_SIZED, 2))
    assert read == expected, f"{len(rates)} rates read; missing {sorted(expected - read)[:5]}, unexpected {sorted(read - expected)[:5]}"
    print_success(f"{len(rates)} rates read for {len(conditions)} conditions")


class _StubFxProvider:
    """An FX provider of the test's own, not a plugin: ``call_fx_provider`` calls it as it is. Its base is EUR, and it
    answers the observations it was given, whatever it is asked."""

    code = "SEC9A"
    name = "SEC9a stub"
    base_currency = "EUR"
    base_currencies = ["EUR"]

    def __init__(self, observations: dict[str, list[tuple[date, str, str, Decimal]]]) -> None:
        self.observations = observations
        self.asked: list[list[str]] = []

    async def fetch_rates(self, date_range, currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        self.asked.append(list(currencies))
        return self.observations


def _as_stored(base: str, quote: str, rate: Decimal) -> tuple[str, str, Decimal]:
    """The pair in storage order and its rate: inverted when ``base > quote`` (exact for the rates used here)."""
    return (base, quote, rate) if base < quote else (quote, base, Decimal(1) / rate)


@pytest.mark.asyncio
async def test_sync_change_detection_holds_over_1035_pairs(session, monkeypatch):
    """``ensure_rates_multi_source`` over the 46 ``CODES`` — 1 035 pairs to compare — with a provider answering one rate
    of 2 per currency against EUR on ``DAY0``: 45 fetched. Stored before: 43 of them at the same value, USD/EUR at
    another, AED/EUR not at all. ``total_changed`` is 2 (the new one and the different one), and afterwards every pair
    holds the fetched rate.

    Red on HEAD 04955c498: the one OR of 1 035 pairs is refused, caught as «table may not exist», and every fetched rate
    counted as a change: ``total_changed`` 45.
    """
    print_section("MF-SEC9a: ensure_rates_multi_source, 46 currencies (1 035 pairs)")
    rate, other = Decimal(2), Decimal(4)
    quoted = [code for code in CODES if code != "EUR"]
    observations = {code: [(DAY0, "EUR", code, rate)] for code in quoted}
    await _seed_fx(session, [(DAY0, *_as_stored("EUR", code, other if code == "USD" else rate)) for code in quoted if code != "AED"])
    provider = _StubFxProvider(observations)

    async def configured(_code: str) -> _StubFxProvider:
        return provider

    monkeypatch.setattr(fx_sync, "configured_fx_provider", configured)

    stats = await fx_sync.ensure_rates_multi_source(session, (DAY0, DAY0), list(CODES), provider.code)

    assert provider.asked == [list(CODES)]
    assert (stats["total_fetched"], stats["total_changed"]) == (len(quoted), 2), f"fetched {stats['total_fetched']}, changed {stats['total_changed']}: expected {len(quoted)} and 2"
    assert sorted(stats["currencies_synced"]) == sorted(quoted)
    expected = {(DAY0, base, quote): stored for base, quote, stored in (_as_stored("EUR", code, rate) for code in quoted)}
    stored = await _stored_fx(session)
    assert stored == expected, _differences(stored, expected)
    print_success(f"{stats['total_fetched']} fetched, {stats['total_changed']} changed: the new and the different one")


# =============================================================================
# 6. THE ROUTES: IMPORT-SIZED REQUESTS ON A PRIVATE DATABASE
# =============================================================================


@pytest.mark.asyncio
async def test_fx_delete_route_answers_1500_separate_days(session):
    """``DELETE /fx/currencies/rate`` with 1 500 single days — every other day of 3 000 stored, every other deletion sent
    as USD/EUR — the way the FX page sends separate days: 200, each deletion EUR/USD on its day with 1 existing and 1
    deleted, ``total_deleted`` 1 500, no error; the 1 500 other days stay stored.

    Red on HEAD 04955c498: 500 (``delete_rates_bulk`` refused by SQLite, the SQL echoed in the detail).
    """
    print_section("MF-SEC9a: DELETE /fx/currencies/rate, 1 500 separate days")
    await _seed_fx(session, [(_day(offset), "EUR", "USD", Decimal("1.1")) for offset in range(2 * IMPORT_SIZED)])
    days = [_day(offset) for offset in range(0, 2 * IMPORT_SIZED, 2)]
    deletions = [FXDeleteItem(**({"from": "EUR", "to": "USD"} if index % 2 == 0 else {"from": "USD", "to": "EUR"}), date_range=DateRangeModel(start=day)) for index, day in enumerate(days)]

    try:
        response = await currencies.delete_rates_endpoint(deletions=deletions, session=session, _current_user=None)
    except HTTPException as refused:
        pytest.fail(f"{refused.status_code} for {len(deletions)} separate days: {str(refused.detail)[:200]}")

    assert (response.total_deleted, response.success_count, response.errors) == (IMPORT_SIZED, IMPORT_SIZED, [])
    answered = [(result.success, result.base, result.quote, result.date_range.start, result.existing_count, result.deleted_count) for result in response.results]
    expected_answers = [(True, "EUR", "USD", day, 1, 1) for day in days]
    wrong = [(got, want) for got, want in zip(answered, expected_answers, strict=False) if got != want]
    assert len(answered) == len(days) and not wrong, f"{len(answered)} results; (got, expected): {wrong[:5]}"
    stored = await _stored_fx(session)
    expected = {(_day(offset), "EUR", "USD"): Decimal("1.1") for offset in range(1, 2 * IMPORT_SIZED, 2)}
    assert stored == expected, _differences(stored, expected)
    print_success(f"200: {response.total_deleted} rates deleted, {len(stored)} kept")


@pytest.mark.asyncio
async def test_guard_fx_upsert_route_stores_1500_rates(session):
    """``POST /fx/currencies/rate`` with 1 500 rates, two pairs of three inverted: 200, each answered ``inserted`` with
    its pair in storage order and its day, and every rate stored at its value.

    Green on HEAD 04955c498 too: the route upserts one rate at a time, so an import of any size passed (slowly).
    """
    print_section("MF-SEC9a guard: POST /fx/currencies/rate, 1 500 rates")
    rows, expected = _upsert_rows(IMPORT_SIZED, again=False)
    items = [FXUpsertItem(**{"date": day}, base=base, quote=quote, rate=rate, source=source) for day, base, quote, rate, source in rows]

    response = await currencies.upsert_rates_endpoint(rates=items, session=session, _current_user=None)

    assert (response.success_count, response.errors) == (IMPORT_SIZED, [])
    answered = [(result.success, result.action, result.date, result.base, result.quote) for result in response.results]
    assert answered == [(True, "inserted", day, base, quote) for day, base, quote in expected], "every rate answered inserted, in order, its pair in storage order"
    stored = await _stored_fx(session)
    assert stored == expected, _differences(stored, expected)
    print_success(f"200: {response.success_count} rates stored")


# =============================================================================
# 6. THE ROUTES: MORE THAN 10 000 ITEMS REFUSED BEFORE ANY WRITE
# =============================================================================


class _UntouchedSession:
    """Stands in for the route's session where nothing may use it: every use is recorded, and raises."""

    def __init__(self) -> None:
        self.touched: list[str] = []

    def __getattr__(self, name: str) -> Any:
        self.touched.append(name)
        raise AssertionError(f"the session was used ({name})")


class _Service:
    """Stands in for a route's service: records each call's arguments and answers ``answer(*args)``."""

    def __init__(self, answer: Callable[..., Any]) -> None:
        self.answer = answer
        self.calls: list[tuple] = []

    async def __call__(self, *args: Any, **_kwargs: Any) -> Any:
        self.calls.append(args)
        return self.answer(*args)


def _fx_rates(count: int) -> list[FXUpsertItem]:
    return [FXUpsertItem(**{"date": _day(index)}, base="EUR", quote="USD", rate=Decimal("1.1")) for index in range(count)]


def _fx_deletions(count: int) -> list[FXDeleteItem]:
    return [FXDeleteItem(**{"from": "EUR", "to": "USD"}, date_range=DateRangeModel(start=_day(index))) for index in range(count)]


def _price_deletions(ranges_per_asset: list[int]) -> list[FAAssetDelete]:
    return [FAAssetDelete(asset_id=asset_id, date_ranges=[DateRangeModel(start=_day(index)) for index in range(ranges)]) for asset_id, ranges in enumerate(ranges_per_asset, start=1)]


def _price_deletion_answer(data: list[FAAssetDelete], _session: Any) -> FABulkDeleteResponse:
    results = [FAPriceDeleteResult(asset_id=item.asset_id, success=True, deleted_count=0) for item in data]
    return FABulkDeleteResponse(results=results, success_count=len(results), total_deleted=0, errors=[])


class _CapRoute:
    """A bulk write route arranged with its items, its service a recorder: ``call(session)`` runs the route, ``reached()``
    counts the items that reached the service."""

    def __init__(self, service: _Service, call: Callable[[Any], Awaitable[Any]], items: int, reached: Callable[[], int]) -> None:
        self.service = service
        self.call = call
        self.items = items
        self.reached = reached


def _fx_upsert_route(count: int) -> Callable[[pytest.MonkeyPatch], _CapRoute]:
    """``POST /fx/currencies/rate`` with ``count`` rates; its service (called once per rate) a recorder."""

    def arrange(monkeypatch: pytest.MonkeyPatch) -> _CapRoute:
        service = _Service(lambda _session, rates: [(True, "inserted")] * len(rates))
        monkeypatch.setattr(currencies, "upsert_rates_bulk", service)
        rates = _fx_rates(count)
        return _CapRoute(service, lambda session: currencies.upsert_rates_endpoint(rates=rates, session=session, _current_user=None), count, lambda: sum(len(args[1]) for args in service.calls))

    return arrange


def _fx_delete_route(count: int) -> Callable[[pytest.MonkeyPatch], _CapRoute]:
    """``DELETE /fx/currencies/rate`` with ``count`` single-day deletions; its service a recorder."""

    def arrange(monkeypatch: pytest.MonkeyPatch) -> _CapRoute:
        service = _Service(lambda _session, deletions: [(True, 0, 0, None)] * len(deletions))
        monkeypatch.setattr(currencies, "delete_rates_bulk", service)
        deletions = _fx_deletions(count)
        return _CapRoute(service, lambda session: currencies.delete_rates_endpoint(deletions=deletions, session=session, _current_user=None), count, lambda: sum(len(args[1]) for args in service.calls))

    return arrange


def _price_delete_route(ranges_per_asset: list[int]) -> Callable[[pytest.MonkeyPatch], _CapRoute]:
    """``DELETE /assets/prices`` with one item per entry of ``ranges_per_asset``, that many single-day ranges each; its
    service a recorder. The items counted are the ranges, every asset's together."""

    def arrange(monkeypatch: pytest.MonkeyPatch) -> _CapRoute:
        service = _Service(_price_deletion_answer)
        monkeypatch.setattr(AssetSourceManager, "bulk_delete_prices", staticmethod(service))
        assets = _price_deletions(ranges_per_asset)
        return _CapRoute(
            service,
            lambda session: prices.delete_prices_bulk(assets=assets, session=session, _current_user=None),
            sum(ranges_per_asset),
            lambda: sum(len(item.date_ranges) for args in service.calls for item in args[0]),
        )

    return arrange


CAP_REFUSED = [
    pytest.param(_fx_upsert_route(MAX_WRITE_ITEMS + 1), id="POST-fx-rate-10001-rates"),
    pytest.param(_fx_delete_route(MAX_WRITE_ITEMS + 1), id="DELETE-fx-rate-10001-deletions"),
    pytest.param(_price_delete_route([MAX_WRITE_ITEMS + 1]), id="DELETE-prices-1-asset-10001-ranges"),
    pytest.param(_price_delete_route([5_001, 5_001]), id="DELETE-prices-2-assets-5001-ranges-each"),
]
CAP_PASSED = [
    pytest.param(_fx_upsert_route(MAX_WRITE_ITEMS), id="POST-fx-rate-10000-rates"),
    pytest.param(_fx_delete_route(MAX_WRITE_ITEMS), id="DELETE-fx-rate-10000-deletions"),
    pytest.param(_price_delete_route([MAX_WRITE_ITEMS]), id="DELETE-prices-1-asset-10000-ranges"),
    pytest.param(_price_delete_route([5_000, 5_000]), id="DELETE-prices-2-assets-5000-ranges-each"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("arrange", CAP_REFUSED)
async def test_more_than_10000_items_refused_before_any_write(monkeypatch, arrange):
    """More than 10 000 items — 10 001 rates, 10 001 deletions, or date ranges of ``DELETE /assets/prices`` counted over
    every asset (two assets of 5 001, each under the cap alone) — answer 422 ``bulk_too_many_items``, ``max_items``
    10 000, ``items`` the count; the service is never called and the session never touched.

    Red on HEAD 04955c498: no cap; the service was called with every item.
    """
    route = arrange(monkeypatch)
    print_section(f"MF-SEC9a: {route.items} items refused")
    session = _UntouchedSession()

    try:
        answer = await route.call(session)
    except HTTPException as refused:
        assert refused.status_code == 422, f"{refused.status_code}: {str(refused.detail)[:200]}"
        detail = refused.detail
    else:
        pytest.fail(f"no refusal for {route.items} items: answered {type(answer).__name__}, {route.reached()} item(s) reached the service")

    assert isinstance(detail, dict) and detail.get("code") == "bulk_too_many_items", f"the 422 is not coded: {detail!r}"
    assert isinstance(detail.get("message"), str) and detail["message"].strip(), f"no message: {detail!r}"
    assert {key: value for key, value in detail.items() if key not in ("code", "message")} == {"max_items": MAX_WRITE_ITEMS, "items": route.items}
    assert (route.service.calls, session.touched) == ([], []), f"{len(route.service.calls)} service call(s), the session used for {session.touched[:5]} before the refusal"
    print_success(f"422 bulk_too_many_items for {route.items} items, nothing called")


@pytest.mark.asyncio
@pytest.mark.parametrize("arrange", CAP_PASSED)
async def test_guard_exactly_10000_items_pass(monkeypatch, arrange):
    """Exactly 10 000 items pass the cap: every item reaches the service — once per rate for the FX upsert, in one call
    otherwise — and the route answers each.

    Green on HEAD 04955c498 too: the edge the cap must keep open.
    """
    route = arrange(monkeypatch)
    print_section(f"MF-SEC9a guard: {route.items} items pass")

    answer = await route.call(_UntouchedSession())

    assert route.reached() == route.items, f"{route.reached()} items reached the service, in {len(route.service.calls)} call(s)"
    assert answer.success_count == len(answer.results) > 0, f"answered {type(answer).__name__}: {answer.success_count} successes, {len(answer.results)} results"
    print_success(f"{route.items} items reached the service")


# =============================================================================
# 7. A FAILURE NEVER ECHOES ITS ERROR
# =============================================================================


class _RecordingLogger:
    """Stands in for a route module's logger: records every line at any level, with the exception being handled."""

    def __init__(self) -> None:
        self.lines: list[tuple[str, str, BaseException | None]] = []

    def __getattr__(self, level: str) -> Callable[..., None]:
        def log(message: object = "", *_args: Any, **_kwargs: Any) -> None:
            self.lines.append((level, str(message), sys.exc_info()[1]))

        return log


class _FailingSession:
    """Stands in for the route's session where every statement fails with ``LEAK``."""

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise Exception(LEAK)

    async def commit(self) -> None:
        raise Exception(LEAK)

    async def rollback(self) -> None:
        return None


async def _raise_leak(*_args: Any, **_kwargs: Any) -> Any:
    raise Exception(LEAK)


async def _fx_upsert_fails_for_gbp(_session: Any, rates: list[tuple]) -> list[tuple[bool, str]]:
    """The FX upsert service, failing with ``LEAK`` for a GBP rate: one rate a call, as the route calls it."""
    if any("GBP" in (base, quote) for _rate_day, base, quote, _rate, _source in rates):
        raise Exception(LEAK)
    return [(True, "inserted")] * len(rates)


def _gbp_usd_delete_all() -> FXDeleteItem:
    return FXDeleteItem(**{"from": "GBP", "to": "USD"}, delete_all=True)


def _post_prices(monkeypatch):
    monkeypatch.setattr(AssetSourceManager, "bulk_upsert_prices", staticmethod(_raise_leak))
    assets = [FAUpsert(asset_id=1, prices=[FAPricePoint(date=DAY0, close=Decimal(1))])]
    return lambda: prices.upsert_prices_bulk(assets=assets, session=_UntouchedSession(), _current_user=None), 500, None


def _delete_prices(monkeypatch):
    monkeypatch.setattr(AssetSourceManager, "bulk_delete_prices", staticmethod(_raise_leak))
    assets = [FAAssetDelete(asset_id=1, date_ranges=[DateRangeModel(start=DAY0)])]
    return lambda: prices.delete_prices_bulk(assets=assets, session=_UntouchedSession(), _current_user=None), 500, None


def _sync_prices(monkeypatch):
    monkeypatch.setattr(AssetSourceManager, "bulk_refresh_prices", staticmethod(_raise_leak))
    requests = [FARefreshItem(asset_id=1, date_range=SyncDateRangeModel(start=DAY0, end=DAY0))]
    return lambda: prices.sync_prices_bulk(requests=requests, session=_UntouchedSession(), _current_user=None), 500, None


def _fx_bulk_delete(monkeypatch):
    monkeypatch.setattr(currencies, "delete_rates_bulk", _raise_leak)
    deletions = _fx_deletions(1)
    return lambda: currencies.delete_rates_endpoint(deletions=deletions, session=_UntouchedSession(), _current_user=None), 500, None


def _fx_delete_all_among_others(monkeypatch):
    monkeypatch.setattr(currencies, "delete_rates_bulk", _Service(lambda _session, deletions: [(True, 0, 0, None)] * len(deletions)))
    deletions = [_gbp_usd_delete_all(), *_fx_deletions(1)]
    return lambda: currencies.delete_rates_endpoint(deletions=deletions, session=_FailingSession(), _current_user=None), 200, "GBP/USD"


def _fx_delete_all_alone(monkeypatch):
    deletions = [_gbp_usd_delete_all()]
    return lambda: currencies.delete_rates_endpoint(deletions=deletions, session=_FailingSession(), _current_user=None), 400, "GBP/USD"


def _fx_upsert_one_fails(monkeypatch):
    monkeypatch.setattr(currencies, "upsert_rates_bulk", _fx_upsert_fails_for_gbp)
    rates = [FXUpsertItem(**{"date": DAY0}, base="EUR", quote="USD", rate=Decimal("1.1")), FXUpsertItem(**{"date": DAY0}, base="GBP", quote="USD", rate=Decimal("1.3"))]
    return lambda: currencies.upsert_rates_endpoint(rates=rates, session=_UntouchedSession(), _current_user=None), 200, "Rate 1"


def _fx_upsert_every_rate_fails(monkeypatch):
    monkeypatch.setattr(currencies, "upsert_rates_bulk", _fx_upsert_fails_for_gbp)
    rates = [FXUpsertItem(**{"date": DAY0}, base="GBP", quote="USD", rate=Decimal("1.3"))]
    return lambda: currencies.upsert_rates_endpoint(rates=rates, session=_UntouchedSession(), _current_user=None), 400, "Rate 0"


#: (arrange, logger's module): ``arrange(monkeypatch)`` answers the call, the status it must answer, and what the error
#: text must name (the item: a pair or an index), None for a 500 that names nothing.
FAILURE_SITES = [
    pytest.param(_post_prices, prices, id="POST-prices-500"),
    pytest.param(_delete_prices, prices, id="DELETE-prices-500"),
    pytest.param(_sync_prices, prices, id="POST-prices-sync-500"),
    pytest.param(_fx_bulk_delete, currencies, id="DELETE-fx-rate-bulk-500"),
    pytest.param(_fx_delete_all_among_others, currencies, id="DELETE-fx-rate-delete-all-error-in-200"),
    pytest.param(_fx_delete_all_alone, currencies, id="DELETE-fx-rate-delete-all-error-in-400"),
    pytest.param(_fx_upsert_one_fails, currencies, id="POST-fx-rate-item-error-in-200"),
    pytest.param(_fx_upsert_every_rate_fails, currencies, id="POST-fx-rate-item-error-in-400"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("arrange", "module"), FAILURE_SITES)
async def test_a_failure_never_echoes_its_error(monkeypatch, arrange, module):
    """The service, or the session, fails with an error naming the schema (``LEAK``): the route answers its status — a
    500, or 200 / 400 with the item's error text naming the item — and nothing it gives the caller holds the SQL; the
    error itself is logged, with its exception.

    Red on HEAD 04955c498: the detail or the error text was ``str(e)``, the SQL echoed to the caller.
    """
    call, status, names = arrange(monkeypatch)
    log = _RecordingLogger()
    monkeypatch.setattr(module, "logger", log, raising=False)  # fx/currencies.py had no logger before MF-SEC9a
    print_section(f"MF-SEC9a: a failure answering {status}")

    try:
        answer = await call()
    except HTTPException as refused:
        answered, texts = refused.status_code, [str(refused.detail)]
    else:
        answered, texts = 200, list(answer.errors)

    leaked = [word for text in texts for word in LEAK_WORDS if word in text]
    assert not leaked, f"the answer echoes the error ({sorted(set(leaked))}): {texts}"
    assert answered == status, f"{answered}: {texts}"
    assert texts and all(text.strip() for text in texts), f"an empty answer: {texts}"
    if names is not None:
        assert len(texts) == 1 and names in texts[0], f"the error text must name {names!r}: {texts}"
    logged = [error for level, _message, error in log.lines if level in ("exception", "error", "critical") and error is not None]
    assert logged and all(str(error) == LEAK for error in logged), f"the error is not logged with its exception: {log.lines}"
    print_success(f"{answered} {texts}; the error logged")


@pytest.mark.asyncio
async def test_guard_post_prices_value_error_keeps_its_domain_message(monkeypatch):
    """``POST /assets/prices``: a ``ValueError`` of the service (a currency mismatch) answers 400 with its own message.

    Green on HEAD 04955c498 too: only the 500 lost its echo.
    """
    print_section("MF-SEC9a guard: POST /assets/prices, a domain error")
    message = "Currency mismatch for asset 1: the price is in USD, the asset in EUR"

    async def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise ValueError(message)

    monkeypatch.setattr(AssetSourceManager, "bulk_upsert_prices", staticmethod(refuse))
    monkeypatch.setattr(prices, "logger", _RecordingLogger())
    assets = [FAUpsert(asset_id=1, prices=[FAPricePoint(date=DAY0, close=Decimal(1))])]

    with pytest.raises(HTTPException) as excinfo:
        await prices.upsert_prices_bulk(assets=assets, session=_UntouchedSession(), _current_user=None)

    assert (excinfo.value.status_code, excinfo.value.detail) == (400, message)
    print_success("400 with the domain message")
