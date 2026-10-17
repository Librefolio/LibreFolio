"""R13-SEC9-2 (security review by E; lands with X-R59) — a rate query never ORs more pairs than SQLite can parse.

The defect. ``convert_bulk`` (``services/fx/conversion.py``) read the rates of every pair a call needs in ONE statement,
``WHERE <pair 1> OR <pair 2> OR …``; X-R59's ``_first_rate_days_inside`` (``services/fx/period_changes.py``) did the
same. SQLite parses that chain as one expression tree as deep as the number of pairs and refuses it past its maximum
depth (1 000): «Expression tree is too large», from about 990 pairs. One ``POST /fx/currencies/convert`` holds up to
1 000 conversions (``MAX_BULK_ITEMS``), each of its own pair: the request answered 500 instead of its rates, and so did
the FX period changes of that many pairs.

The cure: the pairs are read ``FX_PAIRS_PER_QUERY`` (500) at a time, one statement per chunk, the answers merged. The
contract pinned here, for 1 000 distinct pairs (the most one conversion request names) and for 1 035 (every pair of 46
ISO codes):

- ``convert_bulk`` answers every conversion, without raising: the three seeded pairs — the first, the middle and the last
  of the request, so in different chunks whatever their size — converted in both directions at their rate
  (backward-filled from it), every other conversion ``None`` with its «no rate» error (``raise_on_error=False``);
- ``_first_rate_days_inside(session, pairs, after, until)`` answers without raising: the first usable rate day inside
  ``(after, until]`` of the three seeded pairs, and nothing for the others — a rate on ``after`` or after ``until`` is
  outside.

The barrier, ``test_barrier_this_sqlite_refuses_one_or_of_that_many_pairs``: on the same private database, ONE statement
ORing that many pairs is refused, «Expression tree is too large». Without it a SQLite built with a higher limit would
make the two tests above pass without testing anything; with it, «no raise» means the chunks.

Red on HEAD f252acb4a (``OperationalError``: Expression tree is too large): both cases of
``test_convert_bulk_answers_every_conversion_of_that_many_pairs`` and of
``test_first_rate_days_inside_answers_that_many_pairs``. Green before and after: the barrier.

Isolation: PURE — each test has its own in-memory SQLite database (``SQLModel.metadata.create_all``), closed and
disposed at teardown, and its own rates; no lane database, no server, no network. The rates are dated 2025, any day
would do.

Reference: backend/app/services/fx/conversion.py (convert_bulk), backend/app/services/fx/period_changes.py
(_first_rate_days_inside).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from datetime import date
from decimal import Decimal
from itertools import combinations

import pytest
import pytest_asyncio
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import FxRate
from backend.app.schemas.common import Currency
from backend.app.services.fx import period_changes as fx_period_changes
from backend.app.services.fx.conversion import convert_bulk
from backend.test_scripts.test_utils import print_section, print_success

#: 46 ISO 4217 codes ``Currency.validate_code`` accepts (BGN no longer does: the euro replaced it).
CODES = (
    "AED", "ARS", "AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "COP", "CZK", "DKK", "EGP", "EUR", "GBP", "HKD", "HUF",
    "IDR", "ILS", "INR", "ISK", "JPY", "KES", "KRW", "MAD", "MXN", "MYR", "NGN", "NOK", "NZD", "PEN", "PHP", "PKR",
    "PLN", "QAR", "RON", "RSD", "SAR", "SEK", "SGD", "THB", "TRY", "TWD", "UAH", "USD", "VND", "ZAR",
)  # fmt: skip
#: Every pair as ``fx_rates`` stores it (base < quote, so from the codes in alphabetical order): 1 035.
ALL_PAIRS = list(combinations(sorted(CODES), 2))
AS_OF = date(2025, 6, 18)
RATE_DAY = date(2025, 6, 16)  # the seeded rates' day: a conversion on AS_OF backward-fills from it
RATE = Decimal("2")  # 1 base = 2 quote: 2 one way, 0.5 the other, both exact
AFTER, UNTIL = date(2025, 1, 1), date(2025, 1, 31)  # the window of _first_rate_days_inside: (AFTER, UNTIL]
INSIDE = date(2025, 1, 10)

PAIR_COUNTS = [
    pytest.param(1_000, id="1000-pairs-the-most-one-conversion-request-names"),
    pytest.param(len(ALL_PAIRS), id="1035-pairs-every-pair-of-46-codes"),
]


def _pairs(count: int) -> list[tuple[str, str]]:
    assert len(ALL_PAIRS) >= count, f"only {len(ALL_PAIRS)} pairs of {len(CODES)} codes"
    return ALL_PAIRS[:count]


def _seeded(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """The pairs given a rate: the first, the middle and the last of the request, in different chunks whatever their size."""
    return [pairs[0], pairs[len(pairs) // 2], pairs[-1]]


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


async def _seed(session: AsyncSession, rows: Iterable[tuple[tuple[str, str], date]]) -> None:
    """A rate of ``RATE`` for each (pair, day)."""
    session.add_all(FxRate(base=base, quote=quote, date=day, rate=RATE, source="SEC9-2") for (base, quote), day in rows)
    await session.commit()


def _refused_by_sqlite(error: OperationalError, what: str, pairs: int) -> None:
    pytest.fail(f"{what} raised for {pairs} pairs, SQLite refusing the statement: {error.orig!r} — a 500 on the request (R13-SEC9-2)")


@pytest.mark.asyncio
@pytest.mark.parametrize("count", PAIR_COUNTS)
async def test_barrier_this_sqlite_refuses_one_or_of_that_many_pairs(session, count):
    """Barrier: ONE statement ORing ``count`` pairs, the shape before the cure, is refused by the SQLite these tests run on.

    Green before and after the cure: it tests SQLite, so that «no raise» below means the chunks, not a lenient build.
    """
    print_section(f"R13-SEC9-2 barrier: one OR of {count} pairs")
    statement = select(FxRate.base, FxRate.quote, func.min(FxRate.date)).where(or_(*(and_(FxRate.base == base, FxRate.quote == quote) for base, quote in _pairs(count)))).group_by(FxRate.base, FxRate.quote)

    with pytest.raises(OperationalError, match="Expression tree is too large"):
        await session.execute(statement)
    print_success(f"one OR of {count} pairs: refused, Expression tree is too large")


@pytest.mark.asyncio
@pytest.mark.parametrize("count", PAIR_COUNTS)
async def test_convert_bulk_answers_every_conversion_of_that_many_pairs(session, count):
    """``convert_bulk`` with ``count`` distinct pairs, each converted both ways on ``AS_OF``: every conversion answered,
    the seeded pairs at their rate, every other one ``None`` with its «no rate» error; nothing raised.

    Red on HEAD f252acb4a: ``OperationalError`` «Expression tree is too large» (one OR of every pair).
    """
    print_section(f"R13-SEC9-2: convert_bulk, {count} pairs both ways")
    pairs = _pairs(count)
    seeded = _seeded(pairs)
    await _seed(session, ((pair, RATE_DAY) for pair in seeded))
    conversions = [conversion for base, quote in pairs for conversion in ((Currency(code=base, amount=Decimal(1)), quote, AS_OF), (Currency(code=quote, amount=Decimal(1)), base, AS_OF))]

    try:
        results, errors = await convert_bulk(session, conversions, raise_on_error=False)
    except OperationalError as error:
        _refused_by_sqlite(error, "convert_bulk", count)

    assert len(results) == len(conversions), f"{len(results)} results for {len(conversions)} conversions"
    expected: dict[int, tuple[str, Decimal]] = {}
    for index, pair in enumerate(pairs):
        if pair in seeded:
            base, quote = pair
            expected[2 * index] = (quote, RATE)  # base → quote: × rate
            expected[2 * index + 1] = (base, Decimal(1) / RATE)  # quote → base: ÷ rate
    answered = {index: (result[0].code, result[0].amount, result[1], result[2]) for index, result in enumerate(results) if result is not None}
    assert answered == {index: (code, amount, RATE_DAY, True) for index, (code, amount) in expected.items()}, f"answered: {answered}"
    assert len(errors) == len(conversions) - len(expected), f"{len(errors)} errors for {len(conversions) - len(expected)} conversions without a rate"
    assert all("No FX rate found" in error for error in errors), [error for error in errors if "No FX rate found" not in error][:3]
    print_success(f"{len(conversions)} conversions answered: {len(expected)} at their rate, {len(errors)} without one")


@pytest.mark.asyncio
@pytest.mark.parametrize("count", PAIR_COUNTS)
async def test_first_rate_days_inside_answers_that_many_pairs(session, count):
    """``_first_rate_days_inside`` with ``count`` stored pairs: the first rate day inside ``(AFTER, UNTIL]`` of the three
    seeded pairs, nothing for the others; nothing raised. A rate on ``AFTER``, or after ``UNTIL``, is outside.

    Red on HEAD f252acb4a: ``OperationalError`` «Expression tree is too large» (one OR of every pair).
    """
    print_section(f"R13-SEC9-2: _first_rate_days_inside, {count} pairs")
    pairs = _pairs(count)
    seeded = _seeded(pairs)
    outside = pairs[1]  # a pair with rates only outside the window: on AFTER and after UNTIL
    await _seed(session, [*((pair, INSIDE) for pair in seeded), (seeded[0], UNTIL), (outside, AFTER), (outside, date(2025, 2, 1))])

    try:
        first_days = await fx_period_changes._first_rate_days_inside(session, set(pairs), AFTER, UNTIL)
    except OperationalError as error:
        _refused_by_sqlite(error, "_first_rate_days_inside", count)

    assert first_days == dict.fromkeys(seeded, INSIDE), f"first days: {first_days}"
    print_success(f"{count} pairs read: {len(first_days)} first days inside the window, as seeded")
