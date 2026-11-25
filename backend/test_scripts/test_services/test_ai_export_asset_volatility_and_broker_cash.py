"""78 L6 · S1 + S7 — the per-asset return volatility in the market rows, and the cash of each broker.

WHAT.
- S1: `portfolio.asset_market_context` and `broker.asset_market_context` (v2) write each asset's
  `daily_return_volatility_ratio`; `fx.market_summary` (v2) writes the pair's. One definition everywhere: the sample
  volatility (ddof = 1, `risk.metrics.sample_standard_deviation`) of the simple returns (`financial_math.returns.
  price_return`) between consecutive observed values of the period.
- S7: `portfolio.allocations_cash` (v3) lists `cash_by_broker`, the report's per-broker cash, and the rows add up to
  `cash_total`, also for a broker owned at a share.

WHY. A close-only ETF had no volatility at all in the overview (NATR needs highs and lows), and a model attributed the
cash to a broker by itself (`segnali-AIX.md`, S1 and S7). Until v1 the FX summary used a population deviation: two
definitions of one column in one catalog (coordinator, 25/11).

THE BOOK, on a private SQLite file under ``tmp_path``: one user owning B1 at share 1 and B2 at share 0.5.
- B1: DEPOSIT 10 000 EUR, BUY 10 ``CLOSE_ONLY`` (an ETF priced by its close only, EUR).
- B2: DEPOSIT 4 000 EUR and 1 000 USD, BUY 10 ``CLOSE_ONLY`` and 10 ``OTHER``.
- Both assets close on every weekday from January 2023 in two different non-flat patterns; USD/EUR has a rate on every
  weekday too. The period is April–June 2024.

The cases:
- AV-01: the portfolio row of each asset has the volatility, equal to the definition computed here from the seeded closes.
- AV-02: the broker export gives the same figure for the same asset (one definition, one value).
- AV-03: with a single close in the period the volatility is None.
- BC-01: `cash_by_broker` has B1 and B2, their cash adds up to `cash_total`, and the list says its basis (the user's
  share); with nothing in flight the cash in transit is zero.
- BC-02: B2 counts at its share: half of its EUR and of its USD balances.
- BC-04: the portfolio's positions count a co-owned broker at its share too: B2's 10 units of each asset are 5 (the
  premise of the portfolio domain note «the quantities and the cash shown are the user's part»).
- BC-03: with 1 000 EUR in flight from B1 to B2 on the period end (a CASH_TRANSFER that lands after it), the brokers'
  cash still adds up to `cash_total`, which leaves the cash in transit out; the Liquidity slice of `by_type` holds it
  (L8c): the slice minus `cash_total` is exactly the 1 000 in flight, and `cash_in_transit` carries those 1 000 as a
  row of its own, read from the engine (Liquidity = `cash_total` + `cash_in_transit`).

Isolation: PURE with respect to the lane (private file, NullPool, the engine disposed at teardown; portfolio caches
emptied around each test; an empty market holiday table). No lane database, no server, no network, no sleep.

Runs in ``./dev.py test services ai-export``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_asset_volatility_and_broker_cash.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.types import BrokerScopeSource, BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.assets import price_query
from backend.app.services.financial_math.portfolio.allocation_view import LIQUIDITY
from backend.app.services.financial_math.returns import price_return
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.risk.metrics import sample_standard_deviation

EUR = "EUR"
USD = "USD"
PERIOD_START = date(2024, 4, 1)
PERIOD_END = date(2024, 6, 28)  # a Friday
CLOSES_FROM = date(2023, 1, 2)
DEPOSIT_DAY = date(2024, 1, 15)
BUY_DAY = date(2024, 1, 16)
TOLERANCE = 1e-12


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    brokers: dict[str, int]
    assets: dict[str, int]


def _weekdays(start: date = CLOSES_FROM, end: date = PERIOD_END) -> list[date]:
    days = (start + timedelta(days=offset) for offset in range((end - start).days + 1))
    return [day for day in days if day.weekday() < 5]


def _close(pattern: str, index: int) -> Decimal:
    if pattern == "A":
        return Decimal("100") + Decimal(index % 9 - 4) / 4
    return Decimal("50") + Decimal((index * 5) % 11 - 5) / 5


def _rate(index: int) -> Decimal:
    """USD per EUR, stored as the alphabetical pair EUR/USD."""
    return Decimal("1.08") + Decimal(index % 7 - 3) / 200


def _observed(values: list[tuple[date, Decimal]]) -> list[Decimal]:
    return [value for day, value in values if PERIOD_START <= day <= PERIOD_END]


def _definition(values: list[Decimal]) -> float | None:
    """The one definition (78 L6), written here from its two home functions, never from the component."""
    returns = [float(price_return(previous, current)) for previous, current in zip(values, values[1:], strict=False)]
    return sample_standard_deviation(returns) if len(returns) >= 2 else None


SERIES = {
    "CLOSE_ONLY": [(day, _close("A", index)) for index, day in enumerate(_weekdays())],
    "OTHER": [(day, _close("B", index)) for index, day in enumerate(_weekdays())],
}
RATES = [(day, _rate(index)) for index, day in enumerate(_weekdays())]


IN_FLIGHT_DEPARTURE = date(2024, 6, 25)
IN_FLIGHT_ARRIVAL = date(2024, 7, 5)  # after the period end: in flight on the as-of day


async def _seed(engine: AsyncEngine, *, single_close: bool = False, cash_in_flight: bool = False) -> _Book:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username="l6_volatility_cash", email="l6_volatility_cash@test.com", hashed_password="fakehash", is_active=True)
        brokers = {"B1": Broker(name="L6 B1"), "B2": Broker(name="L6 B2 half")}
        assets = {
            "CLOSE_ONLY": Asset(display_name="L6 CLOSE_ONLY", currency=EUR, asset_type=AssetType.ETF),
            "OTHER": Asset(display_name="L6 OTHER", currency=EUR, asset_type=AssetType.STOCK),
        }
        session.add_all([user, *brokers.values(), *assets.values()])
        await session.flush()
        session.add(BrokerUserAccess(broker_id=brokers["B1"].id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        session.add(BrokerUserAccess(broker_id=brokers["B2"].id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("0.5")))

        def cash(broker: str, currency: str, amount: str) -> Transaction:
            return Transaction(broker_id=brokers[broker].id, asset_id=None, type=TransactionType.DEPOSIT, date=DEPOSIT_DAY, quantity=Decimal("0"), amount=Decimal(amount), currency=currency)

        def buy(broker: str, asset: str) -> Transaction:
            return Transaction(broker_id=brokers[broker].id, asset_id=assets[asset].id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal(10), amount=Decimal(-1000), currency=EUR)

        session.add_all([cash("B1", EUR, "10000"), buy("B1", "CLOSE_ONLY"), cash("B2", EUR, "4000"), cash("B2", USD, "1000"), buy("B2", "CLOSE_ONLY"), buy("B2", "OTHER")])
        if cash_in_flight:
            departure = Transaction(broker_id=brokers["B1"].id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=IN_FLIGHT_DEPARTURE, quantity=Decimal("0"), amount=Decimal("-1000"), currency=EUR)
            arrival = Transaction(broker_id=brokers["B2"].id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=IN_FLIGHT_ARRIVAL, quantity=Decimal("0"), amount=Decimal("1000"), currency=EUR)
            session.add_all([departure, arrival])
            await session.flush()
            departure.related_transaction_id = arrival.id
            arrival.related_transaction_id = departure.id
        for label, series in SERIES.items():
            rows = [(day, close) for day, close in series if not single_close or day < PERIOD_START or day == PERIOD_END or label != "CLOSE_ONLY"]
            session.add_all(PriceHistory(asset_id=assets[label].id, date=day, open=close, high=close, low=close, close=close, currency=EUR, source_plugin_key="MANUAL") for day, close in rows)
        session.add_all(FxRate(date=day, base=EUR, quote=USD, rate=rate, source="ECB") for day, rate in [(date(1990, 1, 1), Decimal("1.1")), *RATES])
        await session.commit()
        return _Book(engine=engine, user_id=user.id, brokers={k: v.id for k, v in brokers.items()}, assets={k: v.id for k, v in assets.items()})


def _scope(book: _Book, domain: Domain, **extra) -> BuildScope:
    owned = tuple(sorted(book.brokers.values()))
    if domain is Domain.BROKER:
        broker_scope, source = (extra["broker_id"],), BrokerScopeSource.REQUESTED
    elif domain is Domain.FX:
        broker_scope, source = owned, BrokerScopeSource.OWNED
    else:
        broker_scope, source = owned, BrokerScopeSource.OWNED
    return BuildScope(
        request_id=f"l6-{domain.value}",
        user_id=book.user_id,
        domain=domain,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency=EUR,
        broker_scope=broker_scope,
        broker_scope_source=source,
        owned_broker_ids=owned,
        **extra,
    )


async def _resolve(book: _Book, scope: BuildScope, component_id: str) -> dict:
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)
        envelope = await context.resolve(component_id, required=True)
    return envelope.payload


def _volatility(payload: dict, asset_id: int) -> float | None:
    rows = [row for row in payload["entities"] if row["entity_id"] == f"asset:{asset_id}"]
    assert len(rows) == 1, payload["entities"]
    return rows[0]["daily_return_volatility_ratio"]


def _clear_portfolio_caches() -> None:
    report_module._portfolio_l2_cache.clear()
    wac_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _no_market_holidays() -> frozenset[date]:
    return frozenset()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request: pytest.FixtureRequest) -> None:
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@pytest.fixture(autouse=True)
def no_market_holidays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)


async def _engine(tmp_path: Path, name: str) -> AsyncEngine:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / name}", poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    return engine


@pytest_asyncio.fixture
async def book(tmp_path: Path) -> AsyncIterator[_Book]:
    engine = await _engine(tmp_path, "l6_book.sqlite")
    try:
        yield await _seed(engine)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def in_flight_book(tmp_path: Path) -> AsyncIterator[_Book]:
    engine = await _engine(tmp_path, "l6_in_flight.sqlite")
    try:
        yield await _seed(engine, cash_in_flight=True)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def single_close_book(tmp_path: Path) -> AsyncIterator[_Book]:
    engine = await _engine(tmp_path, "l6_single.sqlite")
    try:
        yield await _seed(engine, single_close=True)
    finally:
        await engine.dispose()


# =============================================================================
# S1 — the per-asset volatility, one definition
# =============================================================================


@pytest.mark.asyncio
async def test_av01_the_portfolio_row_carries_each_assets_volatility_by_the_one_definition(book):
    payload = await _resolve(book, _scope(book, Domain.PORTFOLIO), "portfolio.asset_market_context")

    for label, series in SERIES.items():
        expected = _definition(_observed(series))
        assert expected is not None and expected > 0, "premise: the seeded closes move"
        assert _volatility(payload, book.assets[label]) == pytest.approx(expected, abs=TOLERANCE), label


@pytest.mark.asyncio
async def test_av02_the_broker_export_gives_the_same_figure(book):
    portfolio = await _resolve(book, _scope(book, Domain.PORTFOLIO), "portfolio.asset_market_context")
    broker = await _resolve(book, _scope(book, Domain.BROKER, broker_id=book.brokers["B1"]), "broker.asset_market_context")

    asset_id = book.assets["CLOSE_ONLY"]
    assert _volatility(broker, asset_id) == pytest.approx(_volatility(portfolio, asset_id), abs=TOLERANCE)


@pytest.mark.asyncio
async def test_av03_a_single_close_in_the_period_has_no_volatility(single_close_book):
    payload = await _resolve(single_close_book, _scope(single_close_book, Domain.PORTFOLIO), "portfolio.asset_market_context")

    assert _volatility(payload, single_close_book.assets["CLOSE_ONLY"]) is None
    assert _volatility(payload, single_close_book.assets["OTHER"]) is not None, "premise: the other asset keeps its closes"


# =============================================================================
# S7 — the cash of each broker
# =============================================================================


@pytest.mark.asyncio
async def test_bc01_the_cash_of_each_broker_adds_up_to_the_total(book):
    payload = await _resolve(book, _scope(book, Domain.PORTFOLIO), "portfolio.allocations_cash")

    rows = {row["broker_id"]: row for row in payload["cash_by_broker"]}
    assert set(rows) == set(book.brokers.values())
    total = sum(Decimal(str(row["cash_total"]["amount"])) for row in rows.values())
    assert total == pytest.approx(Decimal(str(payload["cash_total"]["amount"])), abs=Decimal("0.000001"))
    assert payload["cash_by_broker_basis"] == "user_ownership_share"
    assert Decimal(str(payload["cash_in_transit"]["amount"])) == 0, "nothing is in flight in this book"


@pytest.mark.asyncio
async def test_bc02_a_broker_owned_at_a_share_counts_its_share(book):
    payload = await _resolve(book, _scope(book, Domain.PORTFOLIO), "portfolio.allocations_cash")

    rows = {row["broker_id"]: row for row in payload["cash_by_broker"]}
    b2 = {balance["code"]: Decimal(str(balance["amount"])) for balance in rows[book.brokers["B2"]]["cash_balances"]}
    # B2: 4 000 EUR deposited, 2 000 spent on two buys, at half; 1 000 USD at half
    assert b2 == {EUR: Decimal("1000"), USD: Decimal("500")}
    b1 = {balance["code"]: Decimal(str(balance["amount"])) for balance in rows[book.brokers["B1"]]["cash_balances"]}
    assert b1 == {EUR: Decimal("9000")}


@pytest.mark.asyncio
async def test_bc03_cash_in_flight_stays_out_of_the_brokers_and_in_the_liquidity_slice(in_flight_book):
    payload = await _resolve(in_flight_book, _scope(in_flight_book, Domain.PORTFOLIO), "portfolio.allocations_cash")

    cash_total = Decimal(str(payload["cash_total"]["amount"]))
    brokers = sum(Decimal(str(row["cash_total"]["amount"])) for row in payload["cash_by_broker"])
    assert brokers == pytest.approx(cash_total, abs=Decimal("0.000001"))
    liquidity = [Decimal(str(item["amount"]["amount"])) for item in payload["by_type"] if item["name"] == LIQUIDITY]
    assert len(liquidity) == 1, payload["by_type"]
    assert liquidity[0] - cash_total == pytest.approx(Decimal("1000"), abs=Decimal("0.000001")), "the Liquidity slice holds the cash in flight"
    in_transit = Decimal(str(payload["cash_in_transit"]["amount"]))
    assert in_transit == pytest.approx(Decimal("1000"), abs=Decimal("0.000001")), "the engine's cash in transit, as a row of its own"
    assert liquidity[0] == pytest.approx(cash_total + in_transit, abs=Decimal("0.000001")), "the two liquidity figures explain each other"
    b1 = {balance["code"]: Decimal(str(balance["amount"])) for balance in next(row for row in payload["cash_by_broker"] if row["broker_id"] == in_flight_book.brokers["B1"])["cash_balances"]}
    assert b1 == {EUR: Decimal("8000")}, "B1 has sent the 1 000: it is no longer its cash"


@pytest.mark.asyncio
async def test_bc04_the_portfolio_positions_count_a_co_owned_broker_at_its_share(book):
    """The portfolio domain note says the quantities and the cash shown are the user's part (78 L6): fixed here."""
    payload = await _resolve(book, _scope(book, Domain.PORTFOLIO), "portfolio.positions")

    quantities = {(row["broker_id"], row["asset_id"]): Decimal(str(row["quantity"])) for row in payload["positions"]}
    assert quantities == {
        (book.brokers["B1"], book.assets["CLOSE_ONLY"]): Decimal("10"),
        (book.brokers["B2"], book.assets["CLOSE_ONLY"]): Decimal("5"),
        (book.brokers["B2"], book.assets["OTHER"]): Decimal("5"),
    }
