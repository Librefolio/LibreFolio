"""MF-FA — ``fetched_at`` of today's price row is the time of its last change, not of the last poll.

``AssetSourceManager.get_current_prices_bulk`` writes a provider quote dated today back to today's ``PriceHistory`` row:
it creates the row (F.2) or extends its intra-day range (F.3). On the F.3 path the code overwrote ``close`` and stamped
``fetched_at = utcnow()`` at every poll, even when the quote equalled the stored close and no bound moved. ``fetched_at``
feeds the price fingerprint ``COUNT(id) + MAX(fetched_at)`` of the portfolio engine
(``PortfolioCalculationEngine._compute_price_fingerprint``) and of the report's L2 cache key (``portfolio_service``,
the same query): every poll with an unchanged price emptied both caches.

The contract, pinned here:

1. F.3: ``close`` is written only when it differs **numerically** from the stored close (``Decimal("102.50")`` after
   a stored 102.5 is no change; the column is a ``RealDecimal(24, 12)``, a double in SQLite, read back padded to six
   decimals), and ``fetched_at`` is stamped only when at least one of open, high, low or close actually changes.
2. F.2 (no row today): unchanged — the row is created with open = high = low = close = the quote, ``fetched_at`` stamped.
3. A ``db:last_known`` fallback writes nothing. The endpoint-level guard for a fallback on YESTERDAY's row is
   ``backend/test_scripts/test_api/test_current_price_persistence.py::test_current_price_fallback_source_does_not_persist``;
   the one here covers the case it does not: a fallback served from TODAY's row leaves that row's ``fetched_at`` alone.

The example of the lot: today's row created at 10:00 with close 102; polls at 10:01, 10:02, 10:03 answer 102 again →
``fetched_at`` stays 10:00 and the fingerprint does not move; at 10:04 the quote is 102.5 → close 102.5, high 102.5,
``fetched_at`` 10:04, a new fingerprint.

Red before the fix: the "same quote again" and "numeric equality" tests (``fetched_at`` advanced to the last poll).
Green before and after: the moving quote, the quote inside the bounds, F.2, a missing bound, the fallback.

How (PURE): a private SQLite file under ``tmp_path`` (``create_all``), never the lane's database; each poll runs in a
fresh session, as each request does, so the stored row is read back through the ``RealDecimal`` round trip. The live
quote is ``price_query._live_quote_item`` replaced by a double (no provider, no cache, no network); the service's today
(``price_query.date_type``) and clock (``price_query.utcnow``) are frozen and advanced by the test — no clock waits.

Source files: backend/app/services/assets/price_query.py (get_current_prices_bulk, _extend_ohlc_bounds),
backend/app/services/financial_math/portfolio/engine.py (_compute_price_fingerprint).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, PriceHistory, ProviderInputType
from backend.app.schemas.prices import FACurrentPriceItem
from backend.app.services.assets import price_query
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.test_scripts.test_utils import print_section, print_success

TODAY = date(2025, 6, 18)  # the service's today, frozen; any day would do
PROVIDER = f"mffa_{uuid.uuid4().hex[:10]}"  # a code of this module's own: no plugin answers it, the quote is the double's


def _at(hour: int, minute: int) -> datetime:
    """A moment of ``TODAY`` in UTC, as ``utcnow`` returns it (aware)."""
    return datetime(TODAY.year, TODAY.month, TODAY.day, hour, minute, tzinfo=UTC)


def _naive_utc(moment: datetime) -> datetime:
    """``moment`` as the ``DateTime`` column reads it back on SQLite: UTC, without a tzinfo."""
    return moment.astimezone(UTC).replace(tzinfo=None) if moment.tzinfo is not None else moment


# =============================================================================
# THE SERVICE: A PRIVATE DATABASE, A FROZEN TODAY AND CLOCK, A QUOTE DOUBLE
# =============================================================================


class _FrozenDate(date):
    """``date`` for the service's write-back, its today held at ``TODAY``."""

    @classmethod
    def today(cls) -> date:
        return TODAY


class _Clock:
    """``price_query.utcnow``: answers ``now``, which the test sets before each poll."""

    def __init__(self) -> None:
        self.now = _at(9, 0)

    def __call__(self) -> datetime:
        return self.now


class _Quote:
    """``price_query._live_quote_item``: every assigned asset's live quote is ``value``, in EUR, as of ``TODAY``, from
    ``provider:<PROVIDER>``; with ``value`` None there is no live quote, and the service falls back to the database."""

    def __init__(self) -> None:
        self.value: Optional[Decimal] = None

    async def __call__(self, asset_id, assignment, semaphore):
        if self.value is None:
            return None, None
        return FACurrentPriceItem(asset_id=asset_id, value=self.value, currency="EUR", as_of_date=TODAY, source=f"provider:{PROVIDER}"), None


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """This test's own SQLite file with the ORM schema: never the lane's database. Disposed at teardown."""
    private_engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'mf_fa.db'}")
    try:
        async with private_engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield private_engine
    finally:
        await private_engine.dispose()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    """The service's clock and today, frozen for this test (undone at teardown)."""
    frozen = _Clock()
    monkeypatch.setattr(price_query, "utcnow", frozen)
    monkeypatch.setattr(price_query, "date_type", _FrozenDate)
    return frozen


@pytest.fixture
def quote(monkeypatch: pytest.MonkeyPatch) -> _Quote:
    """The live quote double behind ``price_query._live_quote_item`` (undone at teardown)."""
    double = _Quote()
    monkeypatch.setattr(price_query, "_live_quote_item", double)
    return double


async def _assigned_asset(engine: AsyncEngine) -> int:
    """An asset of the private database, assigned to ``PROVIDER`` (the assignment only has to exist: the quote is the
    double's)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"MF-FA {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=PROVIDER, identifier="MFFA", identifier_type=ProviderInputType.TICKER))
        await session.commit()
        return asset.id


async def _seed_today(engine: AsyncEngine, asset_id: int, *, open_: Optional[str], high: Optional[str], low: Optional[str], close: str, fetched_at: datetime) -> None:
    """Today's row as a previous poll left it, its ``fetched_at`` set here (the model's default reads the real clock)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(
            PriceHistory(
                asset_id=asset_id,
                date=TODAY,
                open=Decimal(open_) if open_ is not None else None,
                high=Decimal(high) if high is not None else None,
                low=Decimal(low) if low is not None else None,
                close=Decimal(close),
                volume=None,
                currency="EUR",
                source_plugin_key=f"provider:{PROVIDER}",
                fetched_at=fetched_at,
            )
        )
        await session.commit()


async def _poll(engine: AsyncEngine, clock: _Clock, quote: _Quote, asset_id: int, at: datetime, value: Optional[str]) -> FACurrentPriceItem:
    """One poll of the current price at ``at``, quoting ``value`` (None: no live quote), in a fresh session as a request
    has: the stored row is read back from the database, not from a session that wrote it."""
    clock.now = at
    quote.value = Decimal(value) if value is not None else None
    async with AsyncSession(engine, expire_on_commit=False) as session:
        (item,) = await AssetSourceManager.get_current_prices_bulk([asset_id], session)
    return item


async def _today_row(engine: AsyncEngine, asset_id: int) -> dict:
    """Today's row of ``asset_id`` as the database holds it (a fresh session, columns read, not ORM state)."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(PriceHistory.open, PriceHistory.high, PriceHistory.low, PriceHistory.close, PriceHistory.fetched_at).where(PriceHistory.asset_id == asset_id, PriceHistory.date == TODAY))).all()
    assert len(rows) == 1, f"expected one row of today for asset {asset_id}, found {len(rows)}"
    open_, high, low, close, fetched_at = rows[0]
    return {"open": open_, "high": high, "low": low, "close": close, "fetched_at": _naive_utc(fetched_at)}


async def _fingerprint(engine: AsyncEngine, asset_id: int) -> str:
    """The portfolio engine's price fingerprint of ``asset_id`` up to ``TODAY`` (COUNT + MAX(fetched_at))."""
    async with AsyncSession(engine) as session:
        return await PortfolioCalculationEngine(session)._compute_price_fingerprint({asset_id}, TODAY)


# =============================================================================
# THE SAME QUOTE AGAIN: NOTHING CHANGES, NOTHING IS STAMPED (red before the fix)
# =============================================================================


@pytest.mark.asyncio
async def test_the_same_quote_again_keeps_fetched_at_and_close(engine, clock, quote):
    """Created at 10:00 with 102; 10:01, 10:02, 10:03 answer 102 again → close 102, ``fetched_at`` still 10:00."""
    print_section("MF-FA: the same quote again keeps fetched_at")
    asset_id = await _assigned_asset(engine)
    await _poll(engine, clock, quote, asset_id, _at(10, 0), "102")
    created = await _today_row(engine, asset_id)
    assert created["fetched_at"] == _naive_utc(_at(10, 0)), f"precondition: F.2 stamps the creation, got {created['fetched_at']}"

    for minute in (1, 2, 3):
        item = await _poll(engine, clock, quote, asset_id, _at(10, minute), "102")
        assert item.source == f"provider:{PROVIDER}", f"precondition: the poll at 10:0{minute} served the live quote, got {item.source}"
        row = await _today_row(engine, asset_id)
        assert row["close"] == Decimal("102"), f"close must stay 102 after the poll at 10:0{minute}, got {row['close']}"
        assert row["fetched_at"] == _naive_utc(_at(10, 0)), f"fetched_at must stay 10:00 after an unchanged quote at 10:0{minute}, got {row['fetched_at']}"
    print_success("three unchanged quotes: close 102, fetched_at 10:00")


@pytest.mark.asyncio
async def test_the_same_quote_again_keeps_the_price_fingerprint(engine, clock, quote):
    """The engine's fingerprint after the 10:00 creation is the one after the unchanged polls of 10:01..10:03."""
    print_section("MF-FA: the same quote again keeps the price fingerprint")
    asset_id = await _assigned_asset(engine)
    await _poll(engine, clock, quote, asset_id, _at(10, 0), "102")
    before = await _fingerprint(engine, asset_id)

    for minute in (1, 2, 3):
        await _poll(engine, clock, quote, asset_id, _at(10, minute), "102")
        after = await _fingerprint(engine, asset_id)
        assert after == before, f"the price fingerprint must not move on an unchanged quote at 10:0{minute}: {before} -> {after}"
    print_success(f"fingerprint unchanged: {before}")


@pytest.mark.parametrize(
    ("first", "again"),
    [
        pytest.param("102.5", "102.50", id="trailing-zero"),
        pytest.param("102.50", "102.5", id="trailing-zero-stored"),
        pytest.param("65432.123456789", "65432.123456789", id="14-significant-digits"),
        pytest.param("65432.1234567891", "65432.1234567891", id="15-significant-digits"),
        pytest.param("65432.1234567890999", "65432.1234567890999", id="truncated-to-the-column"),
    ],
)
@pytest.mark.asyncio
async def test_a_numerically_equal_quote_is_no_change(engine, clock, quote, first, again):
    """Equality is numeric, across the ``RealDecimal`` round trip (a double in SQLite, read back padded to six decimals,
    a quote truncated like the column on the way in): the same number written another way stamps nothing."""
    print_section(f"MF-FA: {again} after {first} is no change")
    asset_id = await _assigned_asset(engine)
    await _poll(engine, clock, quote, asset_id, _at(10, 0), first)
    created = await _today_row(engine, asset_id)

    await _poll(engine, clock, quote, asset_id, _at(10, 1), again)
    row = await _today_row(engine, asset_id)
    assert row["close"] == created["close"], f"close must stay {created['close']}, got {row['close']}"
    assert row["fetched_at"] == _naive_utc(_at(10, 0)), f"{again} after a stored {created['close']} is no change: fetched_at must stay 10:00, got {row['fetched_at']}"
    print_success(f"{again} after {first}: no stamp")


# =============================================================================
# A QUOTE THAT CHANGES THE ROW IS WRITTEN AND STAMPED (green before and after)
# =============================================================================


@pytest.mark.asyncio
async def test_a_quote_above_the_high_moves_close_high_and_fetched_at(engine, clock, quote):
    """The lot's example to its end: unchanged at 10:01..10:03, then 102.5 at 10:04 → close and high 102.5, low and open
    102, ``fetched_at`` 10:04, a new fingerprint."""
    print_section("MF-FA: a quote above the high moves the row")
    asset_id = await _assigned_asset(engine)
    await _poll(engine, clock, quote, asset_id, _at(10, 0), "102")
    for minute in (1, 2, 3):
        await _poll(engine, clock, quote, asset_id, _at(10, minute), "102")
    before = await _fingerprint(engine, asset_id)

    await _poll(engine, clock, quote, asset_id, _at(10, 4), "102.5")
    row = await _today_row(engine, asset_id)
    assert row["close"] == Decimal("102.5"), f"close must be the new quote 102.5, got {row['close']}"
    assert row["high"] == Decimal("102.5"), f"high must widen to 102.5, got {row['high']}"
    assert row["low"] == Decimal("102"), f"low must stay 102, got {row['low']}"
    assert row["open"] == Decimal("102"), f"open must stay 102, got {row['open']}"
    assert row["fetched_at"] == _naive_utc(_at(10, 4)), f"fetched_at must be 10:04, the time of the change, got {row['fetched_at']}"
    after = await _fingerprint(engine, asset_id)
    assert after != before, f"the price fingerprint must change with the row: {before} -> {after}"
    print_success("102.5 at 10:04: close/high 102.5, fetched_at 10:04, new fingerprint")


@pytest.mark.asyncio
async def test_a_quote_below_the_low_moves_close_low_and_fetched_at(engine, clock, quote):
    """The other bound: 101.5 after a row of 102 → close and low 101.5, high and open 102, ``fetched_at`` stamped."""
    print_section("MF-FA: a quote below the low moves the row")
    asset_id = await _assigned_asset(engine)
    await _poll(engine, clock, quote, asset_id, _at(10, 0), "102")

    await _poll(engine, clock, quote, asset_id, _at(10, 1), "101.5")
    row = await _today_row(engine, asset_id)
    assert row["close"] == Decimal("101.5"), f"close must be the new quote 101.5, got {row['close']}"
    assert row["low"] == Decimal("101.5"), f"low must widen to 101.5, got {row['low']}"
    assert row["high"] == Decimal("102"), f"high must stay 102, got {row['high']}"
    assert row["open"] == Decimal("102"), f"open must stay 102, got {row['open']}"
    assert row["fetched_at"] == _naive_utc(_at(10, 1)), f"fetched_at must be 10:01, got {row['fetched_at']}"
    print_success("101.5 at 10:01: close/low 101.5, fetched_at 10:01")


@pytest.mark.asyncio
async def test_a_quote_inside_the_bounds_moves_close_and_fetched_at_only(engine, clock, quote):
    """Row open 100 / high 103 / low 99 / close 102 (stamped 09:00), quote 101 at 10:00 → close 101, ``fetched_at``
    10:00, the bounds untouched: the close changed, which is a change of the row."""
    print_section("MF-FA: a quote inside the bounds moves close only")
    asset_id = await _assigned_asset(engine)
    await _seed_today(engine, asset_id, open_="100", high="103", low="99", close="102", fetched_at=_at(9, 0))
    before = await _fingerprint(engine, asset_id)

    await _poll(engine, clock, quote, asset_id, _at(10, 0), "101")
    row = await _today_row(engine, asset_id)
    assert row["close"] == Decimal("101"), f"close must be the new quote 101, got {row['close']}"
    assert (row["open"], row["high"], row["low"]) == (Decimal("100"), Decimal("103"), Decimal("99")), f"open/high/low must stay 100/103/99, got {row['open']}/{row['high']}/{row['low']}"
    assert row["fetched_at"] == _naive_utc(_at(10, 0)), f"fetched_at must be 10:00, the close changed, got {row['fetched_at']}"
    assert await _fingerprint(engine, asset_id) != before, "the price fingerprint must change with the close"
    print_success("101 inside 99..103: close 101, bounds kept, fetched_at 10:00")


@pytest.mark.asyncio
async def test_f2_a_new_row_is_created_and_stamped(engine, clock, quote):
    """No row today: the quote creates it, open = high = low = close = 102, ``fetched_at`` the poll's time."""
    print_section("MF-FA: F.2 creates and stamps today's row")
    asset_id = await _assigned_asset(engine)
    assert await _fingerprint(engine, asset_id) == "0:none", "precondition: no price row for the new asset"

    await _poll(engine, clock, quote, asset_id, _at(10, 0), "102")
    row = await _today_row(engine, asset_id)
    assert (row["open"], row["high"], row["low"], row["close"]) == (Decimal("102"),) * 4, f"F.2 must set open=high=low=close=102, got {row}"
    assert row["fetched_at"] == _naive_utc(_at(10, 0)), f"F.2 must stamp fetched_at 10:00, got {row['fetched_at']}"
    print_success("F.2: open=high=low=close=102, fetched_at 10:00")


@pytest.mark.parametrize("missing", ["open", "high", "low"])
@pytest.mark.asyncio
async def test_a_missing_bound_is_filled_and_stamped_even_with_an_equal_close(engine, clock, quote, missing):
    """Row open 100 / high 103 / low 99 / close 102 with one of open, high, low missing; quote 102 (the stored close) →
    the missing column becomes 102 and ``fetched_at`` is stamped: a column changed, though the close did not."""
    print_section(f"MF-FA: a missing {missing} is filled and stamped")
    asset_id = await _assigned_asset(engine)
    seeded = {"open_": "100", "high": "103", "low": "99"}
    seeded["open_" if missing == "open" else missing] = None
    await _seed_today(engine, asset_id, close="102", fetched_at=_at(9, 0), **seeded)

    await _poll(engine, clock, quote, asset_id, _at(10, 0), "102")
    row = await _today_row(engine, asset_id)
    assert row[missing] == Decimal("102"), f"the missing {missing} must be filled with the quote 102, got {row[missing]}"
    assert row["close"] == Decimal("102"), f"close must stay 102, got {row['close']}"
    assert row["fetched_at"] == _naive_utc(_at(10, 0)), f"fetched_at must be 10:00, {missing} changed, got {row['fetched_at']}"
    print_success(f"{missing} filled with 102, fetched_at 10:00")


# =============================================================================
# A FALLBACK WRITES NOTHING (green before and after)
# =============================================================================


@pytest.mark.asyncio
async def test_a_fallback_on_todays_row_leaves_it_alone(engine, clock, quote):
    """No live quote: the service serves today's own row as ``db:last_known`` and writes nothing — its ``fetched_at``
    and the fingerprint stay. (Yesterday's row, at the endpoint: ``test_current_price_fallback_source_does_not_persist``.)"""
    print_section("MF-FA: a db:last_known fallback writes nothing")
    asset_id = await _assigned_asset(engine)
    await _seed_today(engine, asset_id, open_="100", high="103", low="99", close="102", fetched_at=_at(9, 0))
    before = await _fingerprint(engine, asset_id)

    item = await _poll(engine, clock, quote, asset_id, _at(10, 0), None)
    assert item.source == "db:last_known", f"precondition: without a live quote the stored row is served, got {item.source}"
    assert item.as_of_date == TODAY, f"precondition: the fallback is today's row, got {item.as_of_date}"
    row = await _today_row(engine, asset_id)
    assert row["fetched_at"] == _naive_utc(_at(9, 0)), f"a fallback must not stamp fetched_at, got {row['fetched_at']}"
    assert (row["open"], row["high"], row["low"], row["close"]) == (Decimal("100"), Decimal("103"), Decimal("99"), Decimal("102")), f"a fallback must not touch the row, got {row}"
    assert await _fingerprint(engine, asset_id) == before, "a fallback must not move the price fingerprint"
    print_success("db:last_known on today's row: nothing written")
