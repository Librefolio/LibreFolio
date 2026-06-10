"""
Integration tests for PortfolioService.

Uses a real AsyncSession against the test database.
Tests WAC orchestration, FIFO lots, history aggregation.

Also contains pure unit tests for _build_history_series() —
synchronous, no DB, verify computation in isolation (TestBuildHistorySeries).

Reference: backend/app/services/portfolio_service.py
"""

import sys
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.services.portfolio_service import PortfolioService, _HistoryTxRow, _build_history_series
from backend.app.utils.datetime_utils import utcnow


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


@pytest_asyncio.fixture
async def test_user(session) -> User:
    user = User(
        username=f"pfsvc_{utcnow().timestamp()}",
        email=f"pfsvc_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def test_asset(session) -> Asset:
    asset = Asset(
        display_name="PortfolioTestAsset",
        ticker="PFTEST",
        currency="EUR",
        type=AssetType.STOCK,
    )
    session.add(asset)
    await session.flush()
    return asset


@pytest_asyncio.fixture
async def broker_with_access(session, test_user) -> tuple[Broker, BrokerUserAccess]:
    """Create a broker with 100% share_percentage for test_user."""
    broker = Broker(name=f"PfBroker_{utcnow().timestamp()}")
    session.add(broker)
    await session.flush()
    access = BrokerUserAccess(
        broker_id=broker.id,
        user_id=test_user.id,
        role="OWNER",
        share_percentage=Decimal("1.0"),
    )
    session.add(access)
    await session.flush()
    return broker, access


# =============================================================================
# TestBuildHistorySeries — PURE UNIT TESTS (no DB, no async, no fixtures)
# =============================================================================


def _row(dt: str, type_: str, amount: str, share: str = "1") -> _HistoryTxRow:
    return _HistoryTxRow(
        date=date.fromisoformat(dt),
        type=type_,
        amount=Decimal(amount),
        share=Decimal(share),
    )


class TestBuildHistorySeries:
    """Pure unit tests — no DB, no async, no fixtures. Fast and deterministic.

    Any NameError or wrong variable name in the list comprehension
    (like Bug 2: vals["cash"] instead of daily[dt]["cash"]) would be
    caught immediately by test_single_deposit.
    """

    def test_empty_input(self):
        assert _build_history_series([]) == []

    def test_single_deposit(self):
        """
        Single DEPOSIT 10000 -> cash=10000, invested=0, nav=10000.
        This test would have caught Bug 2 (NameError on vals["cash"]).
        """
        rows = [_row("2025-01-01", "DEPOSIT", "10000")]
        result = _build_history_series(rows)

        assert len(result) == 1
        assert result[0].date == date(2025, 1, 1)
        assert result[0].cash_value == Decimal("10000")
        assert result[0].invested_value == Decimal("0")
        assert result[0].nav_value == Decimal("10000")

    def test_buy_moves_cash_to_invested(self):
        """DEPOSIT 10000 then BUY 5000.
        t0: cash=10000, invested=0,    nav=10000
        t1: cash=5000,  invested=5000, nav=10000
        """
        rows = [
            _row("2025-01-01", "DEPOSIT", "10000"),
            _row("2025-03-01", "BUY",     "5000"),
        ]
        result = _build_history_series(rows)

        assert len(result) == 2
        t0 = result[0]
        assert t0.cash_value == Decimal("10000")
        assert t0.invested_value == Decimal("0")
        assert t0.nav_value == Decimal("10000")
        t1 = result[1]
        assert t1.cash_value == Decimal("5000")
        assert t1.invested_value == Decimal("5000")
        assert t1.nav_value == Decimal("10000")

    def test_nav_invariant(self):
        """For every point: nav_value == cash_value + invested_value."""
        rows = [
            _row("2025-01-01", "DEPOSIT",    "10000"),
            _row("2025-02-01", "BUY",         "3000"),
            _row("2025-04-01", "SELL",         "1000"),
            _row("2025-06-01", "WITHDRAWAL",   "2000"),
            _row("2025-09-01", "DEPOSIT",      "5000"),
        ]
        result = _build_history_series(rows)
        assert len(result) == 5
        for point in result:
            assert point.nav_value == point.cash_value + point.invested_value, (
                f"NAV invariant violated at {point.date}: "
                f"nav={point.nav_value} != cash={point.cash_value} + invested={point.invested_value}"
            )

    def test_chronological_order(self):
        """Output must be sorted by date ascending regardless of input order."""
        rows = [
            _row("2025-06-01", "DEPOSIT", "3000"),
            _row("2025-01-01", "DEPOSIT", "5000"),
            _row("2025-03-15", "DEPOSIT", "2000"),
        ]
        result = _build_history_series(rows)
        dates = [p.date for p in result]
        assert dates == sorted(dates)

    def test_share_halves_values(self):
        """share=0.5 -> all monetary values are halved."""
        rows = [_row("2025-01-01", "DEPOSIT", "10000", share="0.5")]
        result = _build_history_series(rows)

        assert len(result) == 1
        assert result[0].cash_value == Decimal("5000")
        assert result[0].nav_value == Decimal("5000")

    def test_withdrawal_reduces_cash(self):
        """DEPOSIT 10000 -> WITHDRAWAL 3000 -> cash = 7000."""
        rows = [
            _row("2025-01-01", "DEPOSIT",    "10000"),
            _row("2025-06-01", "WITHDRAWAL",  "3000"),
        ]
        result = _build_history_series(rows)

        assert len(result) == 2
        t1 = result[1]
        assert t1.cash_value == Decimal("7000")
        assert t1.invested_value == Decimal("0")
        assert t1.nav_value == Decimal("7000")

    def test_sell_increases_cash_reduces_invested(self):
        """DEPOSIT 10000 -> BUY 8000 -> SELL 3000.
        After SELL: cash = 10000-8000+3000 = 5000, invested = 8000-3000 = 5000.
        """
        rows = [
            _row("2025-01-01", "DEPOSIT", "10000"),
            _row("2025-02-01", "BUY",      "8000"),
            _row("2025-03-01", "SELL",     "3000"),
        ]
        result = _build_history_series(rows)

        final = result[-1]
        assert final.cash_value == Decimal("5000")
        assert final.invested_value == Decimal("5000")
        assert final.nav_value == Decimal("10000")

    def test_unknown_type_skipped(self):
        """Unknown transaction types are silently ignored."""
        rows = [
            _row("2025-01-01", "DEPOSIT",  "10000"),
            _row("2025-02-01", "DIVIDEND",  "500"),
        ]
        result = _build_history_series(rows)
        final = result[-1]
        assert final.cash_value == Decimal("10000")
        assert final.nav_value == Decimal("10000")

    def test_multiple_transactions_same_date(self):
        """Two deposits on same date -> single point with cumulative state."""
        rows = [
            _row("2025-01-01", "DEPOSIT", "5000"),
            _row("2025-01-01", "DEPOSIT", "3000"),
        ]
        result = _build_history_series(rows)
        assert len(result) == 1
        assert result[0].cash_value == Decimal("8000")


# =============================================================================
# TestPortfolioServiceGetLots
# =============================================================================


class TestPortfolioServiceGetLots:
    @pytest.mark.asyncio
    async def test_get_lots_no_access(self, session, test_user):
        """User without broker access -> empty lots response."""
        service = PortfolioService(session)
        result = await service.get_lots(
            user_id=test_user.id, broker_id=999999, asset_id=999999,
        )
        assert result.open_lots == []
        assert result.closed_lots == []
        assert result.total_realized_pnl == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_lots_no_transactions(self, session, test_user, broker_with_access, test_asset):
        """Broker with access but no transactions -> empty lots."""
        broker, _ = broker_with_access
        service = PortfolioService(session)
        result = await service.get_lots(
            user_id=test_user.id, broker_id=broker.id, asset_id=test_asset.id,
        )
        assert result.open_lots == []
        assert result.closed_lots == []

    @pytest.mark.asyncio
    async def test_get_lots_buy_only(self, session, test_user, broker_with_access, test_asset):
        """Single BUY -> 1 open lot, 0 closed lots."""
        broker, _ = broker_with_access
        tx = Transaction(
            broker_id=broker.id, asset_id=test_asset.id,
            type=TransactionType.BUY, date=date(2025, 1, 10),
            quantity=Decimal("100"), amount=Decimal("5000"), currency="EUR",
        )
        session.add(tx)
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_lots(
            user_id=test_user.id, broker_id=broker.id, asset_id=test_asset.id,
        )
        assert len(result.open_lots) >= 1
        assert result.total_unrealized_quantity >= Decimal("100")

    @pytest.mark.asyncio
    async def test_get_lots_buy_and_partial_sell(self, session, test_user, broker_with_access, test_asset):
        """BUY 100, SELL 30 -> open lot with 70 remaining, closed lot with 30."""
        broker, _ = broker_with_access
        session.add_all([
            Transaction(broker_id=broker.id, asset_id=test_asset.id,
                        type=TransactionType.BUY, date=date(2025, 2, 1),
                        quantity=Decimal("100"), amount=Decimal("5000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=test_asset.id,
                        type=TransactionType.SELL, date=date(2025, 6, 1),
                        quantity=Decimal("-30"), amount=Decimal("1800"), currency="EUR"),
        ])
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_lots(
            user_id=test_user.id, broker_id=broker.id, asset_id=test_asset.id,
        )
        open_by_qty = [lot for lot in result.open_lots if lot.remaining_quantity == Decimal("70")]
        assert len(open_by_qty) >= 1, f"Expected open lot qty=70, got: {result.open_lots}"
        closed_by_qty = [lot for lot in result.closed_lots if lot.quantity == Decimal("30")]
        assert len(closed_by_qty) >= 1, f"Expected closed lot qty=30, got: {result.closed_lots}"


# =============================================================================
# TestPortfolioServiceGetHistory — Integration with value assertions
# =============================================================================


class TestPortfolioServiceGetHistory:
    @pytest.mark.asyncio
    async def test_empty_history(self, session, test_user):
        """User with no brokers -> empty history list."""
        service = PortfolioService(session)
        result = await service.get_history(user_id=test_user.id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_deposit_sets_cash_value(self, session, test_user, broker_with_access):
        """
        Deposito 10000 EUR -> il punto ha cash_value=10000, invested=0, nav=10000.
        Questo test avrebbe trovato Bug 2 (NameError su vals["cash"]).
        """
        broker, _ = broker_with_access
        session.add(Transaction(
            broker_id=broker.id, type=TransactionType.DEPOSIT,
            date=date(2025, 3, 1), amount=Decimal("10000"), currency="EUR",
        ))
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_history(user_id=test_user.id)

        assert len(result) >= 1
        point = next((p for p in result if p.date == date(2025, 3, 1)), None)
        assert point is not None, f"No point for 2025-03-01 in {[p.date for p in result]}"
        assert point.cash_value == Decimal("10000"), f"Expected cash=10000, got {point.cash_value}"
        assert point.invested_value == Decimal("0")
        assert point.nav_value == Decimal("10000")

    @pytest.mark.asyncio
    async def test_nav_invariant_on_deposit(self, session, test_user, broker_with_access):
        """For every returned point: nav_value == cash_value + invested_value."""
        broker, _ = broker_with_access
        session.add(Transaction(
            broker_id=broker.id, type=TransactionType.DEPOSIT,
            date=date(2025, 4, 1), amount=Decimal("7500"), currency="EUR",
        ))
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_history(user_id=test_user.id)

        for point in result:
            assert point.nav_value == point.cash_value + point.invested_value, (
                f"NAV invariant violated at {point.date}: "
                f"nav={point.nav_value} != cash+invested"
            )

    @pytest.mark.asyncio
    async def test_history_date_range_filter(self, session, test_user, broker_with_access):
        """date_from/date_to filter excludes out-of-range transactions."""
        broker, _ = broker_with_access
        session.add_all([
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT,
                        date=date(2025, 5, 15), amount=Decimal("5000"), currency="EUR"),
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT,
                        date=date(2024, 1, 1), amount=Decimal("3000"), currency="EUR"),
        ])
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_history(
            user_id=test_user.id,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 12, 31),
        )
        for point in result:
            assert date(2025, 1, 1) <= point.date <= date(2025, 12, 31)


# =============================================================================
# TestPortfolioServiceGetSummary — Integration with value assertions
# =============================================================================


class TestPortfolioServiceGetSummary:
    @pytest.mark.asyncio
    async def test_empty_summary_returns_zeros(self, session, test_user):
        """User with no brokers -> all numeric fields are zero."""
        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        assert summary is not None
        assert summary.net_worth == Decimal("0")
        assert summary.total_invested == Decimal("0")
        assert summary.total_gain_loss == Decimal("0")
        assert summary.cash_total == Decimal("0")
        assert summary.holdings == []
        assert summary.by_broker is None

    @pytest.mark.asyncio
    async def test_summary_cash_only_portfolio(self, session, test_user, broker_with_access):
        """
        Solo depositi (nessun asset) -> net_worth = cash_total = deposito.
        gain_loss = 0, simple_roi = 0.
        """
        broker, _ = broker_with_access
        session.add(Transaction(
            broker_id=broker.id, type=TransactionType.DEPOSIT,
            date=date(2025, 1, 1), amount=Decimal("10000"), currency="EUR",
        ))
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        assert summary.cash_total == Decimal("10000"), f"Expected cash_total=10000, got {summary.cash_total}"
        assert summary.net_worth == Decimal("10000"), f"Expected net_worth=10000, got {summary.net_worth}"
        assert summary.total_gain_loss == Decimal("0")
        assert summary.simple_roi_percent == Decimal("0")
        assert summary.holdings == []

    @pytest.mark.asyncio
    async def test_summary_with_breakdown(self, session, test_user, broker_with_access):
        """include_breakdown=True -> by_broker is a non-None list."""
        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, include_breakdown=True)
        assert summary.by_broker is not None
        assert isinstance(summary.by_broker, list)

    @pytest.mark.asyncio
    async def test_summary_filter_by_broker(self, session, test_user, broker_with_access):
        """broker_ids filter: valid broker_id -> no crash, valid structure."""
        broker, _ = broker_with_access
        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, broker_ids=[broker.id])
        assert summary is not None
        assert summary.net_worth >= Decimal("0")

    @pytest.mark.asyncio
    async def test_summary_nonexistent_broker_ignored(self, session, test_user):
        """Non-existent broker_id -> empty but valid summary."""
        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, broker_ids=[999999])
        assert summary is not None
        assert summary.holdings == []
        assert summary.net_worth == Decimal("0")
