"""MF-A12 (workstream MF, lot A12; coordinator's decision N92) — a Dashboard holding's one-day columns ask the house.

What changed. ``PortfolioService.get_summary`` (``backend/app/services/portfolio_service.py``), for a holding valued at
its market price (``valuation_source == "MARKET_PRICE"``) that has a usable price the day before:

* ``price_change_1d`` is ``returns.change_ratio(current_price - prev_price_base, prev_price_base)`` rounded to 4
  decimals. At HEAD ``efef5c876`` it was ``((current_price - prev_price_base) / prev_price_base).quantize(
  Decimal("0.0001"))``, in line;
* ``gain_loss_change_1d_percent`` is ``returns.change_ratio(gain_loss_change_1d, previous_position_value) × 100`` rounded
  to 2 decimals, under the caller's own materiality guard ``|previous_position_value| > 0.01``. At HEAD it was
  ``(gain_loss_change_1d / abs(previous_position_value) * 100).quantize(Decimal("0.01"))``, in line, under the same
  guard.

On a positive price both columns are HEAD's to the bit, rounding ties included; a negative price's change now keeps the
move's sign, as the percent column always did. The values are proved in
``test_financial_math/test_returns_rebase_and_ratios.py`` (``TestDayChangeColumnsFromTheHouse``,
``TestADayChangeOfANegativePrice``). This file locks the call site:

- ``test_the_columns_ask_the_house`` — a structural guard, not a value test (J-14's idea): a recorder that delegates to
  the house's ``change_ratio`` replaces it in ``portfolio_service``'s own namespace. One summary asks it exactly twice
  for the book's one holding, in this order: the price column with (today's price − the day before's, the day before's
  price), both converted into EUR; the percent with (the position's change, its value the day before). The columns are
  what HEAD's expressions give on those very figures, digit for digit and exponent included. An inline copy, whatever
  it computed, would never call it;
- ``test_below_the_materiality_guard_the_percent_is_not_asked`` — the guard stays in the caller: a position worth 0.004
  the day before still has a price change (asked once), but no percent, and the house is not asked for one. A guard
  moved into the house would show up as a second call here; a guard dropped, as a percent;
- ``test_the_tie_row_keeps_today_s_column`` — 200.00 → 202.47 USD (+1.235 %, exactly half-way between 0.0123 and
  0.0124) under EUR/USD 1.08 on both days: the column is HEAD's 0.0123 (``price_return``'s ``c / p − 1`` would say
  0.0124, the reason for N92), and on this long row of 10 units the two columns agree, 1.23 and 1.23;
- ``test_a_negative_price_keeps_the_move_s_sign`` — the one value change: closes of −10 then −12.5 EUR, 2 units. The
  price fell: ``price_change_1d`` −0.2500, as the percent −25.00 says; HEAD said +0.2500. Negative closes are stored
  and valued at market price like any other (``price_store`` only refuses a close it cannot keep or one truncated to 0).

Red on HEAD ``efef5c876`` (the module loaded from ``git show``):

- ``test_the_columns_ask_the_house``: «change_ratio was not asked twice for the holding: []», nothing being recorded;
- ``test_below_the_materiality_guard_the_percent_is_not_asked``: «… asked once for the price column: []»;
- ``test_a_negative_price_keeps_the_move_s_sign``: «price_change_1d 0.2500 … HEAD's expression gives 0.2500».

``test_the_tie_row_keeps_today_s_column`` is a guard, green on HEAD too: it fails if the column moves to ``price_return``.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of
its own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): one user owning one broker at 100 %, one stock; a
DEPOSIT and a BUY on OPEN (2025-03-03), a close on PREV (03-04) and on VALUATION (03-05), and for a USD stock an
EUR/USD rate on each of the three days. The summary is read in EUR as of VALUATION.

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The report (L2),
WAC and engine blob caches (process-global) are emptied around each test: a private file's ids start at 1 in every
test. Every patch goes through ``monkeypatch``. No sleep.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_summary_day_change_house``.

Reference: backend/app/services/portfolio_service.py (get_summary, the MARKET_PRICE branch),
backend/app/services/financial_math/returns.py (change_ratio, price_return),
LibreFolio_developer_journal/Release_2/Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md («MF-A12», N92).
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction
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
from backend.app.services.financial_math import returns
from backend.app.services.financial_math.valuation import compute_holding_value
from backend.app.services.portfolio_service import PortfolioService

D = Decimal
EUR = "EUR"
USD = "USD"

OPEN = date(2025, 3, 3)
PREV = date(2025, 3, 4)
VALUATION = date(2025, 3, 5)


# =============================================================================
# HEAD's expressions (efef5c876, portfolio_service.py:745 and :759), as written
# =============================================================================


def _price_change_1d_today(prev_price_base: Decimal, current_price: Decimal) -> Decimal:
    return ((current_price - prev_price_base) / prev_price_base).quantize(Decimal("0.0001"))


def _change_1d_percent_today(gain_loss_change_1d: Decimal, previous_position_value: Decimal) -> Decimal:
    return (gain_loss_change_1d / abs(previous_position_value) * 100).quantize(Decimal("0.01"))


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Scenario:
    """One stock held at one broker: bought on OPEN, closed on PREV and VALUATION; for a USD stock, EUR/USD on each day."""

    label: str
    currency: str
    quantity: str
    cost: str
    prev_close: str
    close: str
    eur_usd: tuple[str, str, str] | None = None  # on OPEN, PREV, VALUATION

    def in_eur(self, amount: str, day: date) -> Decimal:
        """``amount`` of the stock's currency in EUR on ``day``, as the FX service converts it: USD → EUR divides by
        the stored EUR/USD rate."""
        if self.eur_usd is None:
            return D(amount)
        return D(amount) / D(self.eur_usd[(OPEN, PREV, VALUATION).index(day)])

    def figures(self) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """(the day before's price, today's price, the position's change, its value the day before), in EUR, as
        ``get_summary`` computes them (``compute_holding_value``, no quote base)."""
        prev_price_base, current_price = self.in_eur(self.prev_close, PREV), self.in_eur(self.close, VALUATION)
        previous_position_value = compute_holding_value(D(self.quantity), prev_price_base, None)
        gain_loss_change_1d = compute_holding_value(D(self.quantity), current_price, None) - previous_position_value
        return prev_price_base, current_price, gain_loss_change_1d, previous_position_value


#: Long-digit converted prices, a move that is no tie: 187.4523 → 191.0377 USD, EUR/USD from 1.0876543219 to 1.0912345678.
CONVERTED = _Scenario(label="converted", currency=USD, quantity="12.5", cost="2343.15", prev_close="187.4523", close="191.0377", eur_usd=("1.0851234567", "1.0876543219", "1.0912345678"))
#: Worth 0.004 EUR the day before: at or under the caller's materiality guard (|previous value| > 0.01).
UNDER_THE_GUARD = _Scenario(label="under-the-guard", currency=EUR, quantity="0.001", cost="0.004", prev_close="4.00", close="4.40")
#: +1.235 % exactly in USD, under one EUR/USD rate: a rounding tie, on a long row of 10 units.
TIE = _Scenario(label="tie", currency=USD, quantity="10", cost="2000", prev_close="200.00", close="202.47", eur_usd=("1.08", "1.08", "1.08"))
#: Negative closes: −10 the day before, −12.5 today (the price fell), 2 units.
NEGATIVE = _Scenario(label="negative", currency=EUR, quantity="2", cost="20", prev_close="-10", close="-12.5")


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
        user = User(username=f"mfa12_{scenario.label}_{tag}", email=f"mfa12_{tag}@test.com", hashed_password="fakehash", is_active=True)
        broker = Broker(name=f"MF-A12 {scenario.label} {tag}")
        asset = Asset(display_name=f"MF-A12 {scenario.label} {tag}", currency=scenario.currency, asset_type=AssetType.STOCK)
        session.add_all([user, broker, asset])
        await session.flush()
        currency = scenario.currency
        session.add_all(
            [
                BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=D("1")),
                Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=OPEN, quantity=D("0"), amount=D("10000"), currency=currency),
                Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=OPEN, quantity=D(scenario.quantity), amount=-D(scenario.cost), currency=currency),
                *(PriceHistory(asset_id=asset.id, date=day, open=D(close), high=D(close), low=D(close), close=D(close), volume=D("1"), currency=currency, source_plugin_key="mf_a12_test") for day, close in ((PREV, scenario.prev_close), (VALUATION, scenario.close))),
                *((FxRate(date=day, base=EUR, quote=USD, rate=D(rate), source="TEST") for day, rate in zip((OPEN, PREV, VALUATION), scenario.eur_usd, strict=True)) if scenario.eur_usd else ()),
            ]
        )
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_id=broker.id, asset_id=asset.id)


@asynccontextmanager
async def _private_book(directory: Path, scenario: _Scenario) -> AsyncIterator[_Book]:
    """The app schema and the scenario's ledger on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / f'mf_a12_{scenario.label}.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine, scenario)
    finally:
        await engine.dispose()


async def _holding(book: _Book) -> PortfolioHolding:
    """The book's one holding in the summary read in EUR as of VALUATION: found by its asset and broker."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        summary = await PortfolioService(session).get_summary(user_id=book.user_id, target_currency_override=EUR, date_to=VALUATION)
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


# =============================================================================
# THE RECORDER — the house's change_ratio, as portfolio_service reads it
# =============================================================================

_Calls = list[tuple[dict[str, object], Decimal | None]]


def _record_change_ratio(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    """Replace ``change_ratio`` in ``portfolio_service``'s namespace by a recorder that delegates to the house: every call,
    its arguments by name and what it returned. ``raising=False``: a service that never imported it (HEAD) gets the
    attribute and records nothing."""
    calls: _Calls = []
    real: Callable[..., Decimal | None] = returns.change_ratio

    def record(*args, **kwargs):
        result = real(*args, **kwargs)
        calls.append((dict(inspect.signature(real).bind(*args, **kwargs).arguments), result))
        return result

    monkeypatch.setattr(portfolio_service_module, "change_ratio", record, raising=False)
    return calls


def _texts(arguments: dict[str, object]) -> dict[str, str]:
    """The arguments as text: a Decimal's digits and exponent."""
    return {name: str(value) for name, value in arguments.items()}


# =============================================================================
# THE TESTS
# =============================================================================


class TestTheDayColumnsAskTheHouse:
    @pytest.mark.asyncio
    async def test_the_columns_ask_the_house(self, tmp_path, monkeypatch):
        """One holding, both prices converted from USD into EUR (28 significant digits each): the service asks
        ``change_ratio`` twice, the price column first and the percent second, with the converted figures, and states
        what HEAD's expressions give on the same figures."""
        scenario = CONVERTED
        calls = _record_change_ratio(monkeypatch)
        prev_price_base, current_price, gain_loss_change_1d, previous_position_value = scenario.figures()
        assert len(prev_price_base.as_tuple().digits) == len(current_price.as_tuple().digits) == 28, "precondition: long-digit converted prices"

        async with _private_book(tmp_path, scenario) as book:
            holding = await _holding(book)

        assert str(holding.current_price) == str(current_price), "precondition: today's price converted as the test converts it"
        assert len(calls) == 2, f"change_ratio was not asked twice for the holding: {calls}"
        (price_arguments, price_ratio), (percent_arguments, percent_ratio) = calls
        assert _texts(price_arguments) == {"change": str(current_price - prev_price_base), "base": str(prev_price_base)}, "first, the price column"
        assert _texts(percent_arguments) == {"change": str(gain_loss_change_1d), "base": str(previous_position_value)}, "second, the percent"

        today_price_change = _price_change_1d_today(prev_price_base, current_price)
        today_percent = _change_1d_percent_today(gain_loss_change_1d, previous_position_value)
        assert str(holding.price_change_1d) == str(price_ratio.quantize(Decimal("0.0001"))) == str(today_price_change) == "0.0158", f"price_change_1d {holding.price_change_1d}: the house's {price_ratio}, HEAD's expression {today_price_change}"
        assert str(holding.gain_loss_change_1d) == str(gain_loss_change_1d)
        assert str(holding.gain_loss_change_1d_percent) == str((percent_ratio * 100).quantize(Decimal("0.01"))) == str(today_percent) == "1.58", f"gain_loss_change_1d_percent {holding.gain_loss_change_1d_percent}: the house's {percent_ratio}, HEAD's expression {today_percent}"

    @pytest.mark.asyncio
    async def test_below_the_materiality_guard_the_percent_is_not_asked(self, tmp_path, monkeypatch):
        """0.001 units at 4.00 EUR: worth 0.004 the day before, at or under the caller's guard |value| > 0.01. The price
        change is still the house's (+10 %, asked once); the percent is None, and the house is not asked for one — the
        guard is the caller's, not the house's."""
        scenario = UNDER_THE_GUARD
        calls = _record_change_ratio(monkeypatch)

        async with _private_book(tmp_path, scenario) as book:
            holding = await _holding(book)

        assert len(calls) == 1, f"change_ratio was not asked once for the price column: {calls}"
        assert calls[0][0] == {"change": D("0.40"), "base": D("4.00")}, f"the price column's change over the day before's price, as stored: {calls[0][0]}"
        assert str(holding.price_change_1d) == "0.1000", f"price_change_1d {holding.price_change_1d}"
        assert holding.gain_loss_change_1d == D("0.0004")
        assert holding.gain_loss_change_1d_percent is None, f"no percent of a previous value of 0.004, got {holding.gain_loss_change_1d_percent}"


class TestTheDayColumnsOnTheEdges:
    @pytest.mark.asyncio
    async def test_the_tie_row_keeps_today_s_column(self, tmp_path):
        """200.00 → 202.47 USD is +1.235 % exactly; converted at EUR/USD 1.08 on both days the prices carry 28 digits,
        and ``(c − p) / |p|`` keeps HEAD's 0.0123 where ``price_return``'s ``c / p − 1`` would land on the half and round
        it to 0.0124. On this long row of 10 units the two columns agree: 0.0123 × 100 = 1.23, the percent. Not every
        quantity's row does (``test_on_the_tie_row_the_columns_agree_for_some_quantities_only``), and a short position's
        percent has the opposite sign by design (|previous value| is its base): neither is asserted here."""
        scenario = TIE
        prev_price_base, current_price, gain_loss_change_1d, previous_position_value = scenario.figures()
        assert Fraction(scenario.close) / Fraction(scenario.prev_close) - 1 == Fraction("0.01235"), "precondition: a half-way move"
        assert str(_price_change_1d_today(prev_price_base, current_price)) == "0.0123", "precondition: HEAD's value"
        assert str(returns.price_return(prev_price_base, current_price).quantize(Decimal("0.0001"))) == "0.0124", "precondition: price_return rounds the other way"

        async with _private_book(tmp_path, scenario) as book:
            holding = await _holding(book)

        assert str(holding.current_price) == str(current_price), "precondition: today's price converted as the test converts it"
        assert str(holding.price_change_1d) == "0.0123", f"price_change_1d {holding.price_change_1d}: HEAD's 0.0123; 0.0124 is price_return's rounding of the tie"
        assert str(holding.gain_loss_change_1d_percent) == str(_change_1d_percent_today(gain_loss_change_1d, previous_position_value)) == "1.23", f"gain_loss_change_1d_percent {holding.gain_loss_change_1d_percent}"
        assert holding.price_change_1d * 100 == holding.gain_loss_change_1d_percent, f"the long row's columns: {holding.price_change_1d} and {holding.gain_loss_change_1d_percent}"

    @pytest.mark.asyncio
    async def test_a_negative_price_keeps_the_move_s_sign(self, tmp_path):
        """Closes of −10 then −12.5 EUR: the price fell by a quarter of its size. ``price_change_1d`` is −0.2500, the
        move's sign, as the percent (−25.00) of the position's value (−20 → −25) says; HEAD's ``(c − p) / p`` said
        +0.2500. N92's one value change."""
        scenario = NEGATIVE
        prev_price_base, current_price, gain_loss_change_1d, previous_position_value = scenario.figures()
        today = _price_change_1d_today(prev_price_base, current_price)
        assert str(today) == "0.2500", f"precondition: HEAD's value, got {today}"

        async with _private_book(tmp_path, scenario) as book:
            holding = await _holding(book)

        assert holding.current_price == D("-12.5"), f"precondition: a negative price valued at market, got {holding.current_price}"
        assert str(holding.price_change_1d) == "-0.2500", f"price_change_1d {holding.price_change_1d}: the move's sign is −0.2500; HEAD's expression gives {today}"
        assert holding.gain_loss_change_1d == D("-5")
        assert str(holding.gain_loss_change_1d_percent) == str(_change_1d_percent_today(gain_loss_change_1d, previous_position_value)) == "-25.00", f"gain_loss_change_1d_percent {holding.gain_loss_change_1d_percent}"
        assert holding.price_change_1d * 100 == holding.gain_loss_change_1d_percent, f"the long row's columns: {holding.price_change_1d} and {holding.gain_loss_change_1d_percent}"
