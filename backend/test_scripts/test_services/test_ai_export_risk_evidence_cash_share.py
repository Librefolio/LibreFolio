"""78 L8c — the cash share of `portfolio.risk_concentration` is the true cash, the overview's number.

WHAT. ``portfolio.risk_concentration`` writes ``cash_weight_ratio``, the cash of the measured scope over its net worth.
Inside one AI Export build, that number must be the one the overview prints for the cash: the ``percent`` of the
Liquidity slice in ``by_type`` of ``portfolio.allocations_cash`` (``summary.allocation_by_type``, the cash and the cash
in transit as one slice, named ``LIQUIDITY``). Same number, not the same formula: the slice divides by the sum of the
slices and is rounded to 0.01 %, the share divides by the net worth, unrounded.

The field follows the summary's ``cash_total``, the cash alone; the Liquidity slice adds the cash in transit. The two
coincide here only because no case of this book has cash in transit: the slice is the overview's figure a test can
compare with, not the definition of the field (consultant, 24/11/2026). With cash in transit they differ, by design.

WHY. Before 78 L8c the section copied Risk's ``cash_weight``: the residual at zero risk, 1 − Σ weights of the holdings
WITH a price series. It also held the holdings left out of the measures (no price series) and the value in transit, so
a portfolio with an unpriced holding told the AI it had more cash than the overview said. The consultant's requirement:
fix the same number as the overview, in the same build, in three cases — an excluded holding, a broker filter, an
overdraft.

THE BOOK, on a private SQLite file under ``tmp_path``: one user, OWNER of three brokers (share 1). Everything is in EUR:
no exchange rate is involved. Every trade is at 100 a unit and both priced assets close at exactly 100 on the period end
(a Friday), so every share asserted below is exact at two decimals and the slice's rounding costs nothing.

- B1: DEPOSIT 10 000, BUY 50 ``ETF_A`` for 5 000 → cash 5 000, net worth 10 000.
- B2 (``allow_cash_overdraft``): DEPOSIT 13 000, BUY 120 ``STOCK_B`` for 12 000, WITHDRAWAL 3 000 → cash −2 000, net
  worth 10 000.
- B3: DEPOSIT 5 000, BUY 40 ``UNPRICED`` for 4 000 → cash 1 000, net worth 5 000. ``UNPRICED`` has no price row: the
  valuation marks it at its trade (4 000), Risk leaves it out of the measures.
- ``ETF_A`` and ``STOCK_B`` have a close every weekday from January 2023, well before the 12-month window, to the
  period end, in two different non-zero patterns, so their returns are neither flat nor identical.

The period is 1 April – 28 June 2024. The cases, each in one ``BuildContext`` calling both builders:

- CS-01, an excluded holding: B1 + B3, cash 6 000 / 15 000 = 40 %. Equal to the Liquidity slice; and the old value,
  Risk's residual (1 − Σ row weights = 66.67 %), differs from it by the excluded weight (4 000 / 15 000).
- CS-02, a broker filter: B1 alone (50 %) and the whole portfolio (4 000 / 25 000 = 16 %), each equal to its own
  Liquidity slice, and different from each other: the filter changes the base.
- CS-03, an overdraft: B1 + B2, B2's cash negative, 3 000 / 20 000 = 15 %. Equal to the Liquidity slice.

Only the scopes holding B3 tell the old value from the new: without an excluded holding or value in transit Risk's
residual is the true cash. So CS-01 and the whole portfolio of CS-02 are red on the old code; B1 alone and CS-03 pin
that the share stays right where it already was.

Isolation: PURE with respect to the lane. The real ``RiskService`` and ``PortfolioService`` run in process on the
private file (the app schema by ``create_all``, NullPool, the engine disposed at teardown). The portfolio L2, WAC and
engine blob caches are process-global, and every private book's user has the same id: they are emptied before and
after each test. The market holiday table is an empty one (built for real it takes a QuantLib process). No lane
database, no server, no network, no sleep.

Runs in ``./dev.py test services ai-export``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_risk_evidence_cash_share.py``.
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
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.portfolio_financial import PortfolioAllocationsCashPayload, _build_portfolio_allocations_cash
from backend.app.services.ai_export.components.risk_evidence import PortfolioRiskConcentrationPayload, RiskEvidenceStatus, _build_risk_concentration
from backend.app.services.ai_export.components.types import BrokerScopeSource, BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.assets import price_query
from backend.app.services.financial_math.portfolio.allocation_view import LIQUIDITY
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.risk import service as risk_service_module

EUR = "EUR"
PERIOD_START = date(2024, 4, 1)
PERIOD_END = date(2024, 6, 28)  # a Friday: the last close is the period end's own, no weekend carry
CLOSES_FROM = date(2023, 1, 2)
LAST_CLOSE = Decimal("100")
UNIT_PRICE = Decimal("100")
DEPOSIT_DAY = date(2024, 1, 15)
BUY_DAY = date(2024, 1, 16)
WITHDRAWAL_DAY = date(2024, 2, 1)

# The slice is rounded to 0.01 %, the share is not; the book makes every share exact at two decimals, so what is left
# is the float conversion of the two Decimals.
FLOAT_TOLERANCE = 1e-9


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_ids: dict[str, int]
    asset_ids: dict[str, int]


def _weekdays() -> list[date]:
    days = (CLOSES_FROM + timedelta(days=offset) for offset in range((PERIOD_END - CLOSES_FROM).days + 1))
    return [day for day in days if day.weekday() < 5]


def _closes(pattern: str) -> list[tuple[date, Decimal]]:
    """(day, close) on every weekday from CLOSES_FROM to PERIOD_END, varying around 100, exactly LAST_CLOSE on the end.

    Two patterns of different periods, so the two priced assets neither stand still nor move in lockstep.
    """
    closes = []
    for index, day in enumerate(_weekdays()):
        if day == PERIOD_END:
            close = LAST_CLOSE
        elif pattern == "A":
            close = Decimal("100") + Decimal(index % 9 - 4) / 4
        else:
            close = Decimal("100") + Decimal((index * 5) % 11 - 5) / 5
        closes.append((day, close))
    return closes


async def _seed(engine: AsyncEngine) -> _Book:
    """The book, owned by a new user, committed to the private file."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username="l8c_cash_share", email="l8c_cash_share@test.com", hashed_password="fakehash", is_active=True)
        brokers = {
            "B1": Broker(name="L8c cash share B1"),
            "B2": Broker(name="L8c cash share B2 overdraft", allow_cash_overdraft=True),
            "B3": Broker(name="L8c cash share B3 unpriced"),
        }
        assets = {
            "ETF_A": Asset(display_name="L8c ETF_A", currency=EUR, asset_type=AssetType.ETF),
            "STOCK_B": Asset(display_name="L8c STOCK_B", currency=EUR, asset_type=AssetType.STOCK),
            "UNPRICED": Asset(display_name="L8c UNPRICED", currency=EUR, asset_type=AssetType.ETF),
        }
        session.add_all([user, *brokers.values(), *assets.values()])
        await session.flush()
        session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers.values()])

        def cash(broker: str, kind: TransactionType, day: date, amount: str) -> Transaction:
            return Transaction(broker_id=brokers[broker].id, asset_id=None, type=kind, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency=EUR)

        def buy(broker: str, asset: str, quantity: int) -> Transaction:
            return Transaction(broker_id=brokers[broker].id, asset_id=assets[asset].id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal(quantity), amount=-UNIT_PRICE * quantity, currency=EUR)

        session.add_all(
            [
                cash("B1", TransactionType.DEPOSIT, DEPOSIT_DAY, "10000"),
                buy("B1", "ETF_A", 50),
                cash("B2", TransactionType.DEPOSIT, DEPOSIT_DAY, "13000"),
                buy("B2", "STOCK_B", 120),
                cash("B2", TransactionType.WITHDRAWAL, WITHDRAWAL_DAY, "-3000"),
                cash("B3", TransactionType.DEPOSIT, DEPOSIT_DAY, "5000"),
                buy("B3", "UNPRICED", 40),
            ]
        )
        for label, pattern in (("ETF_A", "A"), ("STOCK_B", "B")):
            asset_id = assets[label].id
            session.add_all(PriceHistory(asset_id=asset_id, date=day, open=close, high=close, low=close, close=close, currency=EUR, source_plugin_key="MANUAL") for day, close in _closes(pattern))
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_ids={label: broker.id for label, broker in brokers.items()}, asset_ids={label: asset.id for label, asset in assets.items()})


# =============================================================================
# ONE BUILD — both builders on one BuildContext
# =============================================================================


@dataclass(frozen=True)
class _Build:
    concentration: PortfolioRiskConcentrationPayload
    allocations: PortfolioAllocationsCashPayload


async def _build(book: _Book, *broker_labels: str) -> _Build:
    """`portfolio.risk_concentration` and `portfolio.allocations_cash` of one build over ``broker_labels``.

    No label: the whole portfolio, the owned brokers (78 L10b: named, never an empty scope, which means no broker).
    """
    owned = tuple(book.broker_ids.values())
    scope = BuildScope(
        request_id=f"l8c-cash-share-{'-'.join(broker_labels) or 'all'}",
        user_id=book.user_id,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency=EUR,
        broker_scope=tuple(book.broker_ids[label] for label in broker_labels) or owned,
        broker_scope_source=BrokerScopeSource.REQUESTED if broker_labels else BrokerScopeSource.OWNED,
        owned_broker_ids=owned,
    )
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)
        concentration = await _build_risk_concentration(context, {})
        allocations = await _build_portfolio_allocations_cash(context, {})
    return _Build(concentration=concentration, allocations=allocations)


def _measured(payload: PortfolioRiskConcentrationPayload) -> PortfolioRiskConcentrationPayload:
    """The section, after asserting Risk measured it."""
    assert payload.status in {RiskEvidenceStatus.OK, RiskEvidenceStatus.PARTIAL}, f"risk concentration {payload.status}: reason_code={payload.reason_code} message={payload.message}"
    assert payload.cash_weight_ratio is not None
    return payload


def _liquidity_percent(allocations: PortfolioAllocationsCashPayload) -> float:
    """The percent of the one Liquidity slice of ``by_type``, found by its name."""
    slices = [item for item in allocations.by_type if item.name == LIQUIDITY]
    assert len(slices) == 1, f"expected one {LIQUIDITY} slice in by_type: {[(item.name, item.percent) for item in allocations.by_type]}"
    assert slices[0].percent is not None, "the Liquidity slice has no percent"
    return float(slices[0].percent)


def _assert_same_cash_share(build: _Build, expected_percent: float) -> float:
    """The section's cash share × 100 is the Liquidity slice's percent; both are the book's ``expected_percent``."""
    share_percent = _measured(build.concentration).cash_weight_ratio * 100
    liquidity = _liquidity_percent(build.allocations)
    assert share_percent == pytest.approx(liquidity, abs=FLOAT_TOLERANCE), f"cash share {share_percent} % vs Liquidity slice {liquidity} %"
    assert liquidity == pytest.approx(expected_percent, abs=FLOAT_TOLERANCE), f"premise: the book's cash share is {expected_percent} %, the slice says {liquidity} %"
    return share_percent


# =============================================================================
# FIXTURES
# =============================================================================


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    report_module._portfolio_l2_cache.clear()
    wac_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _no_market_holidays() -> frozenset[date]:
    return frozenset()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request: pytest.FixtureRequest) -> None:
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@pytest.fixture(autouse=True)
def no_market_holidays(monkeypatch: pytest.MonkeyPatch) -> None:
    """The market holiday table, empty, wherever the build awaits it: the price reads and the Risk run."""
    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _no_market_holidays)


@pytest_asyncio.fixture
async def book(tmp_path: Path) -> AsyncIterator[_Book]:
    """The book on a private SQLite file under tmp_path, with the whole ORM schema; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'l8c_cash_share.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine)
    finally:
        await engine.dispose()


# =============================================================================
# THE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_cs01_an_excluded_holding_leaves_the_cash_share_at_the_overviews(book):
    """CS-01 — B1 + B3: the unpriced holding is left out of the measures, and the cash share is still the overview's.

    Cash 6 000 over a net worth of 15 000 (ETF_A 5 000, UNPRICED marked at its trade, 4 000): 40 %, the Liquidity slice.
    The old value, Risk's residual 1 − Σ row weights (the rows are the priced holdings), is 66.67 %: the cash plus the
    excluded weight. So the new share sits below it by ``excluded_weight_ratio``, 4 000 / 15 000.
    """
    build = await _build(book, "B1", "B3")

    share_percent = _assert_same_cash_share(build, 40.0)
    payload = build.concentration
    unpriced_id = book.asset_ids["UNPRICED"]
    assert [item.asset_id for item in payload.excluded_assets] == [unpriced_id], payload.excluded_assets
    assert unpriced_id not in {row.asset_id for row in payload.rows}, "premise: the rows are the measured holdings"
    assert payload.excluded_weight_ratio == pytest.approx(4000 / 15000, abs=FLOAT_TOLERANCE), "premise: UNPRICED is valued at its trade, 4 000"
    residual = 1 - sum(row.weight_ratio for row in payload.rows)
    assert residual == pytest.approx(1 - 5000 / 15000, abs=FLOAT_TOLERANCE)
    assert share_percent / 100 < residual
    assert residual - share_percent / 100 == pytest.approx(payload.excluded_weight_ratio, abs=FLOAT_TOLERANCE)


@pytest.mark.asyncio
async def test_cs02_a_broker_filter_changes_the_base_and_each_share_is_its_overviews(book):
    """CS-02 — B1 alone (5 000 / 10 000 = 50 %) and the whole portfolio (4 000 / 25 000 = 16 %).

    Each build's cash share is its own Liquidity slice, and the two differ: the filter changes both the cash and the
    net worth it is a share of. The whole portfolio holds UNPRICED, so its old residual (1 − 17 000 / 25 000 = 32 %)
    would have been wrong too.
    """
    filtered = await _build(book, "B1")
    whole = await _build(book)

    filtered_percent = _assert_same_cash_share(filtered, 50.0)
    whole_percent = _assert_same_cash_share(whole, 16.0)
    assert filtered_percent != pytest.approx(whole_percent, abs=1.0)
    assert [item.asset_id for item in whole.concentration.excluded_assets] == [book.asset_ids["UNPRICED"]]
    assert filtered.concentration.excluded_assets == ()


@pytest.mark.asyncio
async def test_cs03_an_overdrawn_broker_counts_its_negative_cash_as_the_overview_does(book):
    """CS-03 — B1 + B2, B2's cash at −2 000: 3 000 / 20 000 = 15 %, the Liquidity slice.

    The overdraft lowers the scope's cash, and the share follows it; the scope's total cash stays positive, so Risk
    measures the holdings.
    """
    build = await _build(book, "B1", "B2")

    _assert_same_cash_share(build, 15.0)
    assert build.concentration.excluded_assets == ()
