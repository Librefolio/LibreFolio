"""
MF-C (workstream MF, developer's decision D-MF7) — a holding's two weights in the Dashboard summary.

``PortfolioService.get_summary`` gives every holding with a value two weights, rounded to 0.01:
``allocation_percent``, its share of the holdings' total market value (cash excluded), and
``nav_weight_percent``, its share of the NAV (cash included). Since MF-C both come from
``financial_math.weights.percent_of``, which has no share of a total at or below zero.

Before MF-C (HEAD) the summary divided by whatever it had: the NAV when above zero and 1 otherwise,
so a holding worth 630 on a NAV of −70 weighed 63000.00 %; and the holdings' total ``or 1``, so a
total of −30 gave −166.67 % and 266.67 %, a total of 0 gave 5000.00 % and −5000.00 %. D-MF7: on a
NAV at or below zero ``nav_weight_percent`` is None («—»), on a holdings total at or below zero
``allocation_percent`` is None, and nothing else changes.

Green on HEAD and after (every expected weight computed by hand, value / total × 100 rounded to 0.01):

- TestOrdinaryPortfolio — two holdings, cash above zero: 56.08 / 43.92 of the holdings, 11.28 / 8.84
  of the NAV, and the AI Export concentration that reads them (11.28, 205.3840);
- TestLeveragedPortfolioAboveZero — cash below zero on an overdraft broker, NAV still above zero:
  296.08 % of the NAV stays. D-MF7 is about the total, not about cash below zero.

Red on HEAD, green after:

- TestNavAtOrBelowZero::test_no_nav_weight — overdraft broker, two holdings worth 930 (or 1000) on
  cash −1000: NAV −70 (or 0). HEAD gave 63000.00 / 30000.00 (or 70000.00 / 30000.00); now None,
  while ``allocation_percent`` keeps its value (the holdings' total is above zero);
- TestNavAtOrBelowZero::test_concentration_reads_no_weight — the consumer that summed those weights:
  ``broker_concentration_context.concentration_metrics`` gave (63000.00, 4869000000.0000, 2) (or
  (70000.00, 5800000000.0000, 2)); now (None, None, 2);
- TestHoldingsTotalAtOrBelowZero::test_no_allocation — a holding quoted below zero (a price below
  zero happens: WTI front-month futures on 20 April 2020) brings the holdings' total to −30 (or 0)
  while the NAV stays above zero. HEAD gave −166.67 / 266.67 (or 5000.00 / −5000.00); now None,
  while ``nav_weight_percent`` keeps its value, below zero for the holding below zero.

Isolation: every test owns its user, broker and assets (unique names) and writes only through a
session that is rolled back: nothing is committed. Every amount is in EUR and read in EUR
(``target_currency_override``), so no FX rate and no other test's row reaches the figures. The
report, WAC and engine blob caches are emptied around each test. Holdings are found by the test's
own asset ids. The overdraft flag is set on the brokers whose cash goes below zero, as a real
ledger would need it; the engine itself does not read it (rows are flushed directly, not through
the transaction service that enforces it).

Reference: backend/app/services/portfolio_service.py (get_summary, step 4),
backend/app/services/financial_math/weights.py.
"""

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import PortfolioHolding, PortfolioSummary
from backend.app.services.ai_export.components.broker_concentration_context import concentration_metrics
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
OPEN_DAY = date(2025, 1, 2)  # the DEPOSIT and every BUY
REPORT_DAY = date(2025, 1, 31)  # every close, and the summary's date_to


# =============================================================================
# HELPERS
# =============================================================================


@dataclass(frozen=True)
class _Position:
    """One holding: bought on OPEN_DAY for ``cost`` (paid, a positive amount), quoted ``close`` on REPORT_DAY."""

    quantity: str
    cost: str
    close: str

    @property
    def value(self) -> Decimal:
        """What the summary must show as its current value: quantity × close."""
        return Decimal(self.quantity) * Decimal(self.close)


@dataclass(frozen=True)
class _Scope:
    """One user owning 100 % of one broker, and one EUR asset with no provider per position."""

    user: User
    broker: Broker
    assets: tuple[Asset, ...]


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    """Add and flush ``rows`` (never commit), keeping a strong reference to each one."""
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


async def _portfolio(session: AsyncSession, keep_alive: list[object], label: str, *, deposit: str, positions: Sequence[_Position], overdraft: bool) -> _Scope:
    """DEPOSIT ``deposit`` and one BUY per position on OPEN_DAY, each position's close on REPORT_DAY."""
    tag = uuid4().hex[:12]
    user = User(username=f"mfc_{label}_{tag}", email=f"mfc_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"MfC_{label}_{tag}", allow_cash_overdraft=overdraft)
    assets = tuple(Asset(display_name=f"MfC {label} {index} {tag}", identifier_ticker=f"MC{index}{tag[:8].upper()}", currency=EUR, asset_type=AssetType.STOCK) for index in range(len(positions)))
    await _persist(session, keep_alive, user, broker, *assets)
    await _persist(session, keep_alive, BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1.0")))

    rows: list[object] = [Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=OPEN_DAY, quantity=Decimal("0"), amount=Decimal(deposit), currency=EUR)]
    for asset, position in zip(assets, positions, strict=True):
        close = Decimal(position.close)
        rows.append(Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=OPEN_DAY, quantity=Decimal(position.quantity), amount=-Decimal(position.cost), currency=EUR))
        rows.append(PriceHistory(asset_id=asset.id, date=REPORT_DAY, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=EUR, source_plugin_key="manual_test"))
    await _persist(session, keep_alive, *rows)
    return _Scope(user=user, broker=broker, assets=assets)


async def _summary(session: AsyncSession, scope: _Scope) -> PortfolioSummary:
    return await PortfolioService(session).get_summary(user_id=scope.user.id, target_currency_override=EUR, date_to=REPORT_DAY)


def _holdings(summary: PortfolioSummary, scope: _Scope, positions: Sequence[_Position], *, nav: str, market: str) -> list[PortfolioHolding]:
    """The scope's holdings in the order of its positions, once the scenario is proven to be the one intended:
    one row per asset (one broker), each quoted at its close, and the NAV and holdings' total expected."""
    by_asset = {holding.asset_id: holding for holding in summary.holdings}
    assert len(summary.holdings) == len(scope.assets) and set(by_asset) == {asset.id for asset in scope.assets}, f"holdings {[(h.asset_id, h.broker_id) for h in summary.holdings]}, expected one per asset {[asset.id for asset in scope.assets]}"
    holdings = [by_asset[asset.id] for asset in scope.assets]
    for holding, position in zip(holdings, positions, strict=True):
        assert holding.valuation_source == "MARKET_PRICE", f"precondition: asset {holding.asset_id} is valued from {holding.valuation_source}, expected its close"
        assert holding.current_value == position.value, f"precondition: asset {holding.asset_id} is worth {holding.current_value}, expected {position.value}"
    assert summary.net_worth.amount == Decimal(nav), f"precondition: NAV {summary.net_worth.amount}, expected {nav}"
    assert summary.market_value.amount == Decimal(market), f"precondition: holdings' total {summary.market_value.amount}, expected {market}"
    return holdings


def _weights(holdings: Sequence[PortfolioHolding]) -> list[tuple[Decimal | None, Decimal | None]]:
    """(allocation_percent, nav_weight_percent) per holding."""
    return [(holding.allocation_percent, holding.nav_weight_percent) for holding in holdings]


def _cents(*texts: str | None) -> list[Decimal | None]:
    return [None if text is None else Decimal(text) for text in texts]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.fixture
def keep_alive() -> list[object]:
    """Strong references to every row the test flushes (see _persist)."""
    return []


@pytest.fixture(autouse=True)
def clean_portfolio_caches(request):
    """No cached report, WAC or engine blob crosses into or out of a test."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


# =============================================================================
# Green on HEAD and after: the weights of an ordinary portfolio do not move
# =============================================================================


class TestOrdinaryPortfolio:
    """DEPOSIT 10000; BUY 10 for 1000 and 5 for 1000; closes 113 and 177: values 1130 and 885,
    holdings' total 2015, cash 8000, NAV 10015."""

    POSITIONS = (_Position("10", "1000", "113"), _Position("5", "1000", "177"))

    @pytest.mark.asyncio
    async def test_weights_are_value_over_total(self, session, keep_alive):
        """1130 / 2015 = 56.079… → 56.08 and 885 / 2015 = 43.920… → 43.92 of the holdings;
        1130 / 10015 = 11.283… → 11.28 and 885 / 10015 = 8.836… → 8.84 of the NAV."""
        scope = await _portfolio(session, keep_alive, "ord", deposit="10000", positions=self.POSITIONS, overdraft=False)

        holdings = _holdings(await _summary(session, scope), scope, self.POSITIONS, nav="10015", market="2015")

        assert [holding.allocation_percent for holding in holdings] == _cents("56.08", "43.92")
        assert [holding.nav_weight_percent for holding in holdings] == _cents("11.28", "8.84")

    @pytest.mark.asyncio
    async def test_concentration_reads_the_nav_weights(self, session, keep_alive):
        """AI Export's broker concentration: the largest NAV weight, and 11.28² + 8.84² = 127.2384 + 78.1456 points."""
        scope = await _portfolio(session, keep_alive, "ordhhi", deposit="10000", positions=self.POSITIONS, overdraft=False)
        summary = await _summary(session, scope)
        _holdings(summary, scope, self.POSITIONS, nav="10015", market="2015")

        largest, herfindahl, count = concentration_metrics(summary)

        assert (largest, herfindahl, count) == (Decimal("11.28"), Decimal("205.3840"), 2)


class TestLeveragedPortfolioAboveZero:
    """Overdraft broker. DEPOSIT 1000; BUY 10 for 2000: cash −1000. Close 151: value 1510, NAV 510."""

    POSITIONS = (_Position("10", "2000", "151"),)

    @pytest.mark.asyncio
    async def test_a_weight_above_one_hundred_stays(self, session, keep_alive):
        """1510 / 1510 → 100.00 of the holdings; 1510 / 510 = 296.078… → 296.08 of the NAV: cash below zero
        with a NAV above zero keeps its weight, D-MF7 only takes the weight away on a NAV at or below zero."""
        scope = await _portfolio(session, keep_alive, "lev", deposit="1000", positions=self.POSITIONS, overdraft=True)

        holdings = _holdings(await _summary(session, scope), scope, self.POSITIONS, nav="510", market="1510")

        assert _weights(holdings) == [(Decimal("100.00"), Decimal("296.08"))]


# =============================================================================
# Red on HEAD: no NAV weight on a NAV at or below zero
# =============================================================================

# Overdraft broker. DEPOSIT 1000; BUY 10 for 1500 and 5 for 500: cash −1000. NAV = holdings' total − 1000.
NAV_NOT_ABOVE_ZERO = {
    # closes 63 and 60: 630 + 300 = 930, NAV −70. Holdings: 630 / 930 = 67.74…, 300 / 930 = 32.25… → 32.26.
    "nav-below-zero": ((_Position("10", "1500", "63"), _Position("5", "500", "60")), "-70", "930", ("67.74", "32.26"), ("63000.00", "30000.00"), ("63000.00", "4869000000.0000")),
    # closes 70 and 60: 700 + 300 = 1000, NAV 0. Holdings: 70.00 and 30.00.
    "nav-zero": ((_Position("10", "1500", "70"), _Position("5", "500", "60")), "0", "1000", ("70.00", "30.00"), ("70000.00", "30000.00"), ("70000.00", "5800000000.0000")),
}


class TestNavAtOrBelowZero:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("positions, nav, market, allocation, head_nav_weight, head_concentration", list(NAV_NOT_ABOVE_ZERO.values()), ids=list(NAV_NOT_ABOVE_ZERO))
    async def test_no_nav_weight(self, session, keep_alive, positions, nav, market, allocation, head_nav_weight, head_concentration):
        """D-MF7: «—» instead of value / 1 × 100 (HEAD's ``head_nav_weight``); the share of the holdings,
        whose total is above zero, keeps its value."""
        scope = await _portfolio(session, keep_alive, "navle0", deposit="1000", positions=positions, overdraft=True)

        holdings = _holdings(await _summary(session, scope), scope, positions, nav=nav, market=market)

        assert [holding.nav_weight_percent for holding in holdings] == [None, None], f"NAV {nav}: no share of it, got {[holding.nav_weight_percent for holding in holdings]} (HEAD: {head_nav_weight})"
        assert [holding.allocation_percent for holding in holdings] == _cents(*allocation)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("positions, nav, market, allocation, head_nav_weight, head_concentration", list(NAV_NOT_ABOVE_ZERO.values()), ids=list(NAV_NOT_ABOVE_ZERO))
    async def test_concentration_reads_no_weight(self, session, keep_alive, positions, nav, market, allocation, head_nav_weight, head_concentration):
        """AI Export's broker concentration over those weights: none to read, so no largest weight and no
        Herfindahl index (HEAD's ``head_concentration``), the position count unchanged."""
        scope = await _portfolio(session, keep_alive, "navle0hhi", deposit="1000", positions=positions, overdraft=True)
        summary = await _summary(session, scope)
        _holdings(summary, scope, positions, nav=nav, market=market)

        assert concentration_metrics(summary) == (None, None, 2), f"HEAD: {head_concentration}"


# =============================================================================
# Red on HEAD: no allocation on a holdings total at or below zero
# =============================================================================

# DEPOSIT 1000; BUY 10 for 100 twice: cash 800. The first closes at 5 (50), the second below zero.
HOLDINGS_TOTAL_NOT_ABOVE_ZERO = {
    # close −8: −80, holdings' total −30, NAV 770. NAV weights: 50 / 770 = 6.493… → 6.49, −80 / 770 = −10.389… → −10.39.
    "total-below-zero": ((_Position("10", "100", "5"), _Position("10", "100", "-8")), "770", "-30", ("6.49", "-10.39"), ("-166.67", "266.67")),
    # close −5: −50, holdings' total 0, NAV 800. NAV weights: 6.25 and −6.25.
    "total-zero": ((_Position("10", "100", "5"), _Position("10", "100", "-5")), "800", "0", ("6.25", "-6.25"), ("5000.00", "-5000.00")),
}


class TestHoldingsTotalAtOrBelowZero:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("positions, nav, market, nav_weight, head_allocation", list(HOLDINGS_TOTAL_NOT_ABOVE_ZERO.values()), ids=list(HOLDINGS_TOTAL_NOT_ABOVE_ZERO))
    async def test_no_allocation(self, session, keep_alive, positions, nav, market, nav_weight, head_allocation):
        """D-MF7: «—» instead of a division by the negative total, or by 1 on a zero total (HEAD's
        ``head_allocation``); the share of the NAV, which is above zero, keeps its value and its sign."""
        scope = await _portfolio(session, keep_alive, "mktle0", deposit="1000", positions=positions, overdraft=False)

        holdings = _holdings(await _summary(session, scope), scope, positions, nav=nav, market=market)

        assert [holding.allocation_percent for holding in holdings] == [None, None], f"holdings' total {market}: no share of it, got {[holding.allocation_percent for holding in holdings]} (HEAD: {head_allocation})"
        assert [holding.nav_weight_percent for holding in holdings] == _cents(*nav_weight)
