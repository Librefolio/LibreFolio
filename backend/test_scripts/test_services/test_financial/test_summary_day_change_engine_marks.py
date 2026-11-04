"""MF6-1 (workstream MF, wave 6, T-U5) — a Dashboard holding's one-day columns read the engine's marks.

What changed. ``PortfolioService.get_summary`` (``backend/app/services/portfolio_service.py``) no longer has
``_get_price_at_date`` (a query of the last ``PriceHistory`` close on or before a day) nor ``_convert_to_base`` (one
``convert_bulk`` per price). A holding's ``current_price`` is ``engine_result.marks.in_target(effective unit price,
currency, valuation day)``; for a holding valued at its market price (``MARKET_PRICE``) the day before is
``marks.last_market_price_at(asset, D − 1)`` — the last market quote on or before D − 1 — converted **at D − 1's rate**
(``marks.in_target(..., D − 1)``), and only on a day the engine replayed (``AssetMarks`` answers on
``first_day`` … ``last_day``). At HEAD ``33b66ba1c`` the day before's close was converted at **the quote's own
date**'s rate, and read on any day, even before the portfolio existed.

- ``test_the_day_before_is_converted_at_its_own_rate`` (red on HEAD): a USD stock read in EUR. Closes 187.45 USD on
  03-03 and 191.03 on 03-05, none on 03-04; EUR/USD stored 1.25 on 03-03, 1.28 on 03-04, 1.25 on 03-05 (rows base EUR,
  quote USD: 1 EUR = rate USD; every inverse exact). Today's price 191.03 × (1 / 1.25) = 152.824 EUR on both. The day
  before is the 03-03 close at 03-04's rate: 187.45 × (1 / 1.28) = 146.4453125, ``price_change_1d`` 0.0436. HEAD
  converted it at 03-03's: 187.45 / 1.25 = 149.96, 0.0191;
- ``test_a_trade_the_day_before_is_not_the_day_before_s_price`` (guard, green on both): an EUR stock closing 100 on
  03-03 and 103 on 03-05, with a second BUY on 03-04 at 120 and no quote that day. The day before is still the 03-03
  close (0.0300), not the trade the engine's mark of 03-04 is;
- ``test_no_day_change_on_the_portfolio_s_first_day`` (red on HEAD): DEPOSIT and BUY on 03-05, an EUR stock closing 100
  on 03-04 and 105 on 03-05, valued on 03-05. 03-04 is before the engine's first day, so there is no one-day change:
  ``price_change_1d``, ``gain_loss_change_1d`` and ``gain_loss_change_1d_percent`` all None. HEAD read the 03-04 close
  of an asset not yet owned: 0.0500, 5, 5.00;
- ``test_the_service_has_no_price_reader_of_its_own`` (red on HEAD): structural — no ``_get_price_at_date`` and no
  ``_convert_to_base`` on ``PortfolioService``.

Red on HEAD ``33b66ba1c`` (the backend of that commit extracted with ``git archive``, this file copied into it), the
exact messages:

- ``test_the_day_before_is_converted_at_its_own_rate``: «price_change_1d 0.0191: the 03-03 close at 03-04's rate gives
  0.0436 (at 03-03's own rate, HEAD's conversion: 0.0191)»;
- ``test_no_day_change_on_the_portfolio_s_first_day``: «price_change_1d 0.0500 on the portfolio's first day: the day
  before is outside the engine's days»;
- ``test_the_service_has_no_price_reader_of_its_own``: «PortfolioService still has ['_get_price_at_date',
  '_convert_to_base']».

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): one user owning one broker at 100 %, one stock. The
summary is read in EUR as of the valuation day.

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The report (L2),
WAC and engine blob caches (process-global) are emptied around each test: a private file's ids start at 1 in every
test. No sleep.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_summary_day_change_engine_marks``.

Reference: backend/app/services/portfolio_service.py (get_summary, the MARKET_PRICE branch),
backend/app/services/financial_math/portfolio/daily_state.py (AssetMarks, marked_price),
backend/test_scripts/test_services/test_financial/test_summary_day_change_house.py (the house's change_ratio, MF-A12).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.portfolio import PortfolioHolding
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.returns import change_ratio
from backend.app.services.financial_math.valuation import compute_holding_value
from backend.app.services.portfolio_service import PortfolioService

D = Decimal
EUR = "EUR"
USD = "USD"
QUANTUM = Decimal("0.0001")

MAR_03 = date(2025, 3, 3)
MAR_04 = date(2025, 3, 4)
MAR_05 = date(2025, 3, 5)


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Scenario:
    """One stock at one broker: a DEPOSIT and BUY on ``opened``, optional further BUYs, closes, EUR/USD rates."""

    label: str
    currency: str
    opened: date
    quantity: str
    cost: str
    closes: tuple[tuple[date, str], ...]
    later_buys: tuple[tuple[date, str, str], ...] = ()  # (day, quantity, cost)
    eur_usd: tuple[tuple[date, str], ...] = ()  # stored base EUR, quote USD: 1 EUR = rate USD


#: USD stock: closes on 03-03 and 03-05, none on 03-04; EUR/USD 1.25, 1.28, 1.25.
RATE_OF_THE_DAY_BEFORE = _Scenario(
    label="rate-day-before",
    currency=USD,
    opened=MAR_03,
    quantity="12.5",
    cost="2343.125",
    closes=((MAR_03, "187.45"), (MAR_05, "191.03")),
    eur_usd=((MAR_03, "1.25"), (MAR_04, "1.28"), (MAR_05, "1.25")),
)
#: EUR stock: closes 100 on 03-03 and 103 on 03-05; a second BUY on 03-04 at 120 a unit, no quote that day.
TRADE_THE_DAY_BEFORE = _Scenario(label="trade-day-before", currency=EUR, opened=MAR_03, quantity="10", cost="1000", closes=((MAR_03, "100"), (MAR_05, "103")), later_buys=((MAR_04, "5", "600"),))
#: EUR stock bought on 03-05, the portfolio's first day; closes 100 on 03-04 (before it) and 105 on 03-05.
FIRST_DAY = _Scenario(label="first-day", currency=EUR, opened=MAR_05, quantity="1", cost="100", closes=((MAR_04, "100"), (MAR_05, "105")))


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_id: int
    asset_id: int


async def _seed(engine: AsyncEngine, scenario: _Scenario) -> _Book:
    """The scenario's ledger, owned by a new user, committed to the private file."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"mf61_{scenario.label}_{tag}", email=f"mf61_{tag}@test.com", hashed_password="fakehash", is_active=True)
        broker = Broker(name=f"MF6-1 {scenario.label} {tag}")
        asset = Asset(display_name=f"MF6-1 {scenario.label} {tag}", currency=scenario.currency, asset_type=AssetType.STOCK)
        session.add_all([user, broker, asset])
        await session.flush()
        currency = scenario.currency
        session.add_all(
            [
                BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=D("1")),
                Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=scenario.opened, quantity=D("0"), amount=D("10000"), currency=currency),
                Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=scenario.opened, quantity=D(scenario.quantity), amount=-D(scenario.cost), currency=currency),
                *(Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=day, quantity=D(quantity), amount=-D(cost), currency=currency) for day, quantity, cost in scenario.later_buys),
                *(PriceHistory(asset_id=asset.id, date=day, open=D(close), high=D(close), low=D(close), close=D(close), volume=D("1"), currency=currency, source_plugin_key="mf61_test") for day, close in scenario.closes),
                *(FxRate(date=day, base=EUR, quote=USD, rate=D(rate), source="TEST") for day, rate in scenario.eur_usd),
            ]
        )
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_id=broker.id, asset_id=asset.id)


@asynccontextmanager
async def _private_book(directory: Path, scenario: _Scenario) -> AsyncIterator[_Book]:
    """The app schema and the scenario's ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / f'mf61_{scenario.label}.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine, scenario)
    finally:
        await engine.dispose()


async def _holding(book: _Book, valuation: date) -> PortfolioHolding:
    """The book's one holding in the summary read in EUR as of ``valuation``: found by its asset and broker."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        summary = await PortfolioService(session).get_summary(user_id=book.user_id, target_currency_override=EUR, date_to=valuation)
    rows = [holding for holding in summary.holdings if holding.asset_id == book.asset_id and holding.broker_id == book.broker_id]
    assert len(rows) == 1, f"expected one holding of asset {book.asset_id} at broker {book.broker_id}, got {[(h.asset_id, h.broker_id) for h in summary.holdings]}"
    assert rows[0].valuation_source == "MARKET_PRICE", f"precondition: a holding valued at its market price, got {rows[0].valuation_source}"
    return rows[0]


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: each private file numbers its rows from 1."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


def _usd_in_eur(amount: str, eur_usd: str) -> Decimal:
    """``amount`` USD in EUR as the engine converts a mark: the unit rate USD → EUR is 1 / (the stored EUR/USD rate),
    then multiplied (``fx.conversion._converted`` and ``AssetMarks.in_target``)."""
    return D(amount) * (D(1) / D(eur_usd))


# =============================================================================
# THE TESTS
# =============================================================================


class TestTheDayBeforeReadsTheEngine:
    @pytest.mark.asyncio
    async def test_the_day_before_is_converted_at_its_own_rate(self, tmp_path):
        """No close on 03-04: the day before's price is the 03-03 close, converted at 03-04's rate (1.28), not at
        03-03's (1.25)."""
        scenario = RATE_OF_THE_DAY_BEFORE
        current_price = _usd_in_eur("191.03", "1.25")
        prev_at_its_day = _usd_in_eur("187.45", "1.28")
        prev_at_quote_day = D("187.45") / D("1.25")  # HEAD: convert_bulk at the quote's date
        expected = change_ratio(current_price - prev_at_its_day, prev_at_its_day).quantize(QUANTUM)
        head_value = change_ratio(current_price - prev_at_quote_day, prev_at_quote_day).quantize(QUANTUM)
        assert (str(current_price), str(prev_at_its_day), str(expected), str(head_value)) == ("152.824", "146.4453125", "0.0436", "0.0191"), "precondition: the arithmetic"

        async with _private_book(tmp_path, scenario) as book:
            holding = await _holding(book, MAR_05)

        assert holding.current_price == current_price, f"precondition: today's price {holding.current_price}"
        assert holding.price_change_1d == expected, f"price_change_1d {holding.price_change_1d}: the 03-03 close at 03-04's rate gives {expected} (at 03-03's own rate, HEAD's conversion: {head_value})"
        quantity = D(scenario.quantity)
        expected_change = compute_holding_value(quantity, current_price, None) - compute_holding_value(quantity, prev_at_its_day, None)
        assert holding.gain_loss_change_1d == expected_change, f"gain_loss_change_1d {holding.gain_loss_change_1d}, expected {expected_change}"

    @pytest.mark.asyncio
    async def test_a_trade_the_day_before_is_not_the_day_before_s_price(self, tmp_path):
        """A BUY at 120 on 03-04 and no quote that day: the day before is the last market quote, 100 on 03-03 —
        +3 %, never the trade's 120 (−14 %)."""
        scenario = TRADE_THE_DAY_BEFORE

        async with _private_book(tmp_path, scenario) as book:
            holding = await _holding(book, MAR_05)

        assert holding.current_price == D("103"), f"precondition: today's close, got {holding.current_price}"
        assert holding.price_change_1d == D("0.0300"), f"price_change_1d {holding.price_change_1d}: the day before is the 03-03 close"
        assert holding.gain_loss_change_1d == D("45"), f"gain_loss_change_1d {holding.gain_loss_change_1d}: 15 units × (103 − 100)"

    @pytest.mark.asyncio
    async def test_no_day_change_on_the_portfolio_s_first_day(self, tmp_path):
        """Bought on 03-05, valued on 03-05: 03-04 is outside the engine's days, so there is no day before to compare
        with — even though the asset has a close on it."""
        scenario = FIRST_DAY

        async with _private_book(tmp_path, scenario) as book:
            holding = await _holding(book, MAR_05)

        assert holding.current_price == D("105"), f"precondition: today's close, got {holding.current_price}"
        assert holding.price_change_1d is None, f"price_change_1d {holding.price_change_1d} on the portfolio's first day: the day before is outside the engine's days"
        assert holding.gain_loss_change_1d is None, f"gain_loss_change_1d {holding.gain_loss_change_1d} on the portfolio's first day"
        assert holding.gain_loss_change_1d_percent is None, f"gain_loss_change_1d_percent {holding.gain_loss_change_1d_percent} on the portfolio's first day"


class TestOneHomeOfThePrice:
    def test_the_service_has_no_price_reader_of_its_own(self):
        """T-U5: «the price of an asset on a day» has one home, the engine's ``AssetMarks``; the service's own query and
        conversion are gone."""
        left = [name for name in ("_get_price_at_date", "_convert_to_base") if hasattr(PortfolioService, name)]
        assert not left, f"PortfolioService still has {left}"
