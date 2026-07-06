"""
Integration tests for PortfolioService.

Uses a real AsyncSession against the test database.
Tests WAC orchestration, FIFO lots, history aggregation.

Also contains pure unit tests for _build_history_series() —
synchronous, no DB, verify computation in isolation (TestBuildHistorySeries).

Reference: backend/app/services/portfolio_service.py
"""

import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, Broker, BrokerUserAccess, PriceHistory, ProviderInputType, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import IssueCode
from backend.app.services.portfolio_service import PortfolioService, _build_history_series, _HistoryTxRow
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
async def test_asset_with_provider(session, test_asset) -> Asset:
    """Same as test_asset, but with a price provider assigned (like a real BTP with
    borsa_italiana) — needed so TRANSACTION_IMPLIED isn't suppressed as a "manual asset"
    (assets with no provider are permanently cost-valued by design, see get_summary()).
    """
    session.add(
        AssetProviderAssignment(
            asset_id=test_asset.id,
            provider_code="yfinance",
            identifier="PFTEST",
            identifier_type=ProviderInputType.TICKER,
        )
    )
    await session.flush()
    return test_asset


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

    NOTE: _build_history_series was refactored to produce a *dense daily* series
    (one point per calendar day) rather than one point per transaction date.
    `market_value` is always 0 at this stage (patched by mark-to-market in
    get_history()). `nav_value == cash_value` always in the raw output.

    All transaction types contribute to cash_value (no type-based filtering here).
    """

    def test_empty_input(self):
        assert _build_history_series([]) == []

    def test_single_deposit(self):
        """
        Single DEPOSIT 10000 -> point on that date has cash=10000, market_value=0, nav=10000.
        This test would have caught Bug 2 (NameError on vals["cash"]).
        """
        rows = [_row("2025-01-01", "DEPOSIT", "10000")]
        result = _build_history_series(rows)

        assert len(result) >= 1
        pt = result[0]
        assert pt.date == date(2025, 1, 1)
        assert pt.cash_value == Decimal("10000")
        assert pt.market_value == Decimal("0")
        assert pt.nav_value == Decimal("10000")

    def test_buy_moves_cash_to_invested(self):
        """DEPOSIT 10000 then BUY -5000 (BUY amounts are negative = cash out).
        Dense series: point on 2025-01-01 has cash=10000; point on 2025-03-01 has
        cash=10000+(-5000)=5000. market_value is always 0 (MtM layer patches it).
        """
        rows = [
            _row("2025-01-01", "DEPOSIT", "10000"),
            _row("2025-03-01", "BUY", "-5000"),  # BUY: negative amount (cash out)
        ]
        result = _build_history_series(rows)

        # Dense expansion: many daily points between 2025-01-01 and 2025-03-01
        assert len(result) > 2
        # Find points by date
        t0 = next(p for p in result if p.date == date(2025, 1, 1))
        t1 = next(p for p in result if p.date == date(2025, 3, 1))
        assert t0.cash_value == Decimal("10000")
        assert t0.nav_value == Decimal("10000")
        assert t1.cash_value == Decimal("5000")
        assert t1.nav_value == Decimal("5000")  # market_value=0, so nav=cash

    def test_nav_invariant(self):
        """For every point: nav_value == cash_value + market_value (market_value=0 always)."""
        rows = [
            _row("2025-01-01", "DEPOSIT", "10000"),
            _row("2025-02-01", "BUY", "-3000"),
            _row("2025-04-01", "SELL", "1000"),
            _row("2025-06-01", "WITHDRAWAL", "-2000"),
            _row("2025-09-01", "DEPOSIT", "5000"),
        ]
        result = _build_history_series(rows)
        # Dense: many more than 5 points
        assert len(result) > 5
        for point in result:
            assert point.nav_value == point.cash_value + point.market_value, f"NAV invariant violated at {point.date}: " f"nav={point.nav_value} != cash={point.cash_value} + market_value={point.market_value}"

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

        assert len(result) >= 1
        assert result[0].cash_value == Decimal("5000")
        assert result[0].nav_value == Decimal("5000")

    def test_withdrawal_reduces_cash(self):
        """DEPOSIT 10000 -> WITHDRAWAL -3000 -> cash = 7000 on withdrawal date."""
        rows = [
            _row("2025-01-01", "DEPOSIT", "10000"),
            _row("2025-06-01", "WITHDRAWAL", "-3000"),
        ]
        result = _build_history_series(rows)

        # Dense: many points; find the withdrawal date
        assert len(result) > 2
        pt = next(p for p in result if p.date == date(2025, 6, 1))
        assert pt.cash_value == Decimal("7000")
        assert pt.nav_value == Decimal("7000")

    def test_sell_increases_cash_reduces_invested(self):
        """DEPOSIT 10000 -> BUY -8000 -> SELL 3000.
        Net cash at end: 10000 - 8000 + 3000 = 5000.
        market_value is always 0 in the raw series (patched by MtM later).
        """
        rows = [
            _row("2025-01-01", "DEPOSIT", "10000"),
            _row("2025-02-01", "BUY", "-8000"),
            _row("2025-03-01", "SELL", "3000"),
        ]
        result = _build_history_series(rows)

        final = result[-1]
        assert final.cash_value == Decimal("5000")
        assert final.nav_value == Decimal("5000")  # market_value=0 at this stage

    def test_all_types_contribute_to_cash(self):
        """All transaction types (including DIVIDEND) contribute to cash_value.
        There is no type-based filtering in _build_history_series.
        """
        rows = [
            _row("2025-01-01", "DEPOSIT", "10000"),
            _row("2025-02-01", "DIVIDEND", "500"),
        ]
        result = _build_history_series(rows)
        final = result[-1]
        # DIVIDEND adds to cash (no type filtering at this layer)
        assert final.cash_value == Decimal("10500")
        assert final.nav_value == Decimal("10500")

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
            user_id=test_user.id,
            broker_id=999999,
            asset_id=999999,
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
            user_id=test_user.id,
            broker_id=broker.id,
            asset_id=test_asset.id,
        )
        assert result.open_lots == []
        assert result.closed_lots == []

    @pytest.mark.asyncio
    async def test_get_lots_buy_only(self, session, test_user, broker_with_access, test_asset):
        """Single BUY -> 1 open lot, 0 closed lots."""
        broker, _ = broker_with_access
        tx = Transaction(
            broker_id=broker.id,
            asset_id=test_asset.id,
            type=TransactionType.BUY,
            date=date(2025, 1, 10),
            quantity=Decimal("100"),
            amount=Decimal("5000"),
            currency="EUR",
        )
        session.add(tx)
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_lots(
            user_id=test_user.id,
            broker_id=broker.id,
            asset_id=test_asset.id,
        )
        assert len(result.open_lots) >= 1
        assert result.total_unrealized_quantity >= Decimal("100")

    @pytest.mark.asyncio
    async def test_get_lots_buy_and_partial_sell(self, session, test_user, broker_with_access, test_asset):
        """BUY 100, SELL 30 -> open lot with 70 remaining, closed lot with 30."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 2, 1), quantity=Decimal("100"), amount=Decimal("5000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2025, 6, 1), quantity=Decimal("-30"), amount=Decimal("1800"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_lots(
            user_id=test_user.id,
            broker_id=broker.id,
            asset_id=test_asset.id,
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
        NOTE: PortfolioHistoryPoint.cash_value/market_value/nav_value are Currency objects.
        """
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 3, 1),
                amount=Decimal("10000"),
                currency="EUR",
            )
        )
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_history(user_id=test_user.id)

        assert len(result) >= 1
        point = next((p for p in result if p.date == date(2025, 3, 1)), None)
        assert point is not None, f"No point for 2025-03-01 in {[p.date for p in result]}"
        assert point.cash_value.amount == Decimal("10000"), f"Expected cash=10000, got {point.cash_value}"
        assert point.market_value.amount == Decimal("0")
        assert point.nav_value.amount == Decimal("10000")

    @pytest.mark.asyncio
    async def test_nav_invariant_on_deposit(self, session, test_user, broker_with_access):
        """For every returned point: nav_value == cash_value + market_value."""
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 4, 1),
                amount=Decimal("7500"),
                currency="EUR",
            )
        )
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_history(user_id=test_user.id)

        for point in result:
            assert point.nav_value == point.cash_value + point.market_value, f"NAV invariant violated at {point.date}: " f"nav={point.nav_value} != cash+market_value"

    @pytest.mark.asyncio
    async def test_history_date_range_filter(self, session, test_user, broker_with_access):
        """date_from/date_to filter excludes out-of-range transactions."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2025, 5, 15), amount=Decimal("5000"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2024, 1, 1), amount=Decimal("3000"), currency="EUR"),
            ]
        )
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
        """User with no brokers -> all numeric fields are zero.
        NOTE: net_worth, total_invested, etc. are Currency objects (not bare Decimal).
        """
        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        assert summary is not None
        assert summary.net_worth.amount == Decimal("0")
        assert summary.total_invested.amount == Decimal("0")
        assert summary.total_gain_loss.amount == Decimal("0")
        assert summary.cash_total.amount == Decimal("0")
        assert summary.holdings == []
        assert summary.by_broker is None

    @pytest.mark.asyncio
    async def test_summary_cash_only_portfolio(self, session, test_user, broker_with_access):
        """
        Solo depositi (nessun asset) -> net_worth = cash_total = deposito.
        gain_loss = 0, simple_roi = 0.
        NOTE: monetary fields are Currency objects; compare via .amount.
        """
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 1, 1),
                amount=Decimal("10000"),
                currency="EUR",
            )
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        assert summary.cash_total.amount == Decimal("10000"), f"Expected cash_total=10000, got {summary.cash_total}"
        assert summary.net_worth.amount == Decimal("10000"), f"Expected net_worth=10000, got {summary.net_worth}"
        assert summary.total_gain_loss.amount == Decimal("0")
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
    async def test_summary_with_breakdown_uses_per_broker_invested(self, session, test_user, broker_with_access):
        """Per-broker breakdown must use invested capital for same broker only."""
        broker_one, _ = broker_with_access
        broker_two = Broker(name=f"PfBroker_{utcnow().timestamp()}_two")
        session.add(broker_two)
        await session.flush()
        session.add(
            BrokerUserAccess(
                broker_id=broker_two.id,
                user_id=test_user.id,
                role="OWNER",
                share_percentage=Decimal("1.0"),
            )
        )
        session.add_all(
            [
                Transaction(broker_id=broker_one.id, type=TransactionType.DEPOSIT, date=date(2025, 1, 1), amount=Decimal("100"), currency="EUR"),
                Transaction(broker_id=broker_two.id, type=TransactionType.DEPOSIT, date=date(2025, 1, 2), amount=Decimal("200"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, include_breakdown=True)

        assert summary.by_broker is not None
        by_broker = {item.broker_id: item for item in summary.by_broker}
        assert by_broker[broker_one.id].net_worth.amount == Decimal("100")
        assert by_broker[broker_one.id].gain_loss.amount == Decimal("0")
        assert by_broker[broker_one.id].gain_loss_percent == Decimal("0")
        assert by_broker[broker_two.id].net_worth.amount == Decimal("200")
        assert by_broker[broker_two.id].gain_loss.amount == Decimal("0")
        assert by_broker[broker_two.id].gain_loss_percent == Decimal("0")

    @pytest.mark.asyncio
    async def test_summary_filter_by_broker(self, session, test_user, broker_with_access):
        """broker_ids filter: valid broker_id -> no crash, valid structure."""
        broker, _ = broker_with_access
        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, broker_ids=[broker.id])
        assert summary is not None
        assert summary.net_worth.amount >= Decimal("0")

    @pytest.mark.asyncio
    async def test_summary_nonexistent_broker_ignored(self, session, test_user):
        """Non-existent broker_id -> empty but valid summary."""
        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, broker_ids=[999999])
        assert summary is not None
        assert summary.holdings == []
        assert summary.net_worth.amount == Decimal("0")


# =============================================================================
# TestTransactionImpliedDataQuality
# =============================================================================


class TestTransactionImpliedDataQuality:
    """TRANSACTION_IMPLIED must respect the selected date range and a placement grace period.

    Regression test: previously, the issue was aggregated from the engine's full-lifetime
    daily_states (always computed from t=0 regardless of the requested date_from, for
    correct cumulative values) with no date_from filtering and no grace period. This meant
    a placement-period gap (e.g. BTP collocamento) from months/years ago kept showing up
    as a warning even after the price feed caught up and even when the user's selected
    date range no longer covered that period at all.
    """

    @pytest.mark.asyncio
    async def test_recent_purchase_within_grace_period_not_flagged(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Asset bought a few days ago with no price yet -> NOT flagged (placement grace)."""
        broker, _ = broker_with_access
        today = date.today()
        buy_date = today - timedelta(days=5)
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=buy_date, amount=Decimal("10000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset_with_provider.id, type=TransactionType.BUY, date=buy_date, quantity=Decimal("100"), amount=Decimal("-9950"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, date_to=today)

        codes = {i.code for i in summary.data_quality.issues}
        assert IssueCode.TRANSACTION_IMPLIED not in codes

    @pytest.mark.asyncio
    async def test_stale_purchase_past_grace_period_is_flagged(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Asset bought >2 weeks ago with STILL no price -> flagged (real problem)."""
        broker, _ = broker_with_access
        today = date.today()
        buy_date = today - timedelta(days=30)
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=buy_date, amount=Decimal("10000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset_with_provider.id, type=TransactionType.BUY, date=buy_date, quantity=Decimal("100"), amount=Decimal("-9950"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id, date_to=today)

        codes = {i.code for i in summary.data_quality.issues}
        assert IssueCode.TRANSACTION_IMPLIED in codes

    @pytest.mark.asyncio
    async def test_old_resolved_gap_excluded_when_date_range_narrowed(self, session, test_user, broker_with_access, test_asset_with_provider):
        """A placement gap that resolved long ago must not resurface once the
        selected date range no longer includes it (the exact reported bug)."""
        broker, _ = broker_with_access
        buy_date = date(2024, 1, 1)
        first_price_date = date(2024, 2, 1)  # ~31 days later, well past the grace period
        report_end = date(2024, 6, 1)
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=buy_date, amount=Decimal("10000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset_with_provider.id, type=TransactionType.BUY, date=buy_date, quantity=Decimal("100"), amount=Decimal("-9950"), currency="EUR"),
                # Price feed catches up on first_price_date -> backward-fill covers all later days
                PriceHistory(asset_id=test_asset_with_provider.id, date=first_price_date, open=Decimal("100"), high=Decimal("100"), low=Decimal("100"), close=Decimal("100"), volume=Decimal("1"), currency="EUR", source_plugin_key="manual_test"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)

        # "All" — includes the resolved placement gap -> flagged
        summary_all = await service.get_summary(user_id=test_user.id, date_to=report_end)
        codes_all = {i.code for i in summary_all.data_quality.issues}
        assert IssueCode.TRANSACTION_IMPLIED in codes_all

        # "3 months"-like narrower window that excludes the gap -> NOT flagged
        summary_narrow = await service.get_summary(user_id=test_user.id, date_from=date(2024, 3, 1), date_to=report_end)
        codes_narrow = {i.code for i in summary_narrow.data_quality.issues}
        assert IssueCode.TRANSACTION_IMPLIED not in codes_narrow


# =============================================================================
# TestNetDepositedCapital
# =============================================================================


class TestNetDepositedCapital:
    """Tests for total_deposited, total_withdrawn, net_deposited_capital fields."""

    @pytest.mark.asyncio
    async def test_deposits_only(self, session, test_user, broker_with_access):
        """Only deposits → total_deposited = sum, total_withdrawn = None, net = deposited."""
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 1, 1),
                amount=Decimal("5000"),
                currency="EUR",
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 2, 1),
                amount=Decimal("3000"),
                currency="EUR",
            )
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        assert summary.total_deposited is not None
        assert summary.total_deposited.amount == Decimal("8000")
        assert summary.total_withdrawn is None  # 0 → None
        assert summary.net_deposited_capital is not None
        assert summary.net_deposited_capital.amount == Decimal("8000")

    @pytest.mark.asyncio
    async def test_deposits_and_withdrawals(self, session, test_user, broker_with_access):
        """Deposits + withdrawals → net = deposited - withdrawn."""
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 1, 1),
                amount=Decimal("10000"),
                currency="EUR",
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date(2025, 3, 1),
                amount=Decimal("-2000"),
                currency="EUR",
            )
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        assert summary.total_deposited.amount == Decimal("10000")
        assert summary.total_withdrawn.amount == Decimal("2000")
        assert summary.net_deposited_capital.amount == Decimal("8000")

    @pytest.mark.asyncio
    async def test_buy_sell_fee_tax_excluded(self, session, test_user, broker_with_access, test_asset):
        """BUY, SELL, FEE, TAX, DIVIDEND, INTEREST do not affect net_deposited_capital."""
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 1, 1),
                amount=Decimal("10000"),
                currency="EUR",
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.BUY,
                date=date(2025, 1, 2),
                amount=Decimal("-5000"),
                currency="EUR",
                asset_id=test_asset.id,
                quantity=Decimal("100"),
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.SELL,
                date=date(2025, 2, 1),
                amount=Decimal("3000"),
                currency="EUR",
                asset_id=test_asset.id,
                quantity=Decimal("-50"),
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.FEE,
                date=date(2025, 1, 2),
                amount=Decimal("-10"),
                currency="EUR",
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.TAX,
                date=date(2025, 2, 1),
                amount=Decimal("-15"),
                currency="EUR",
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DIVIDEND,
                date=date(2025, 3, 1),
                amount=Decimal("50"),
                currency="EUR",
                asset_id=test_asset.id,
            )
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        # Only the DEPOSIT of 10000 counts
        assert summary.total_deposited.amount == Decimal("10000")
        assert summary.total_withdrawn is None
        assert summary.net_deposited_capital.amount == Decimal("10000")

    @pytest.mark.asyncio
    async def test_holding_price_change_1d(self, session, test_user, broker_with_access, test_asset):
        """Holdings expose daily market price change when current and previous prices exist."""
        broker, _ = broker_with_access
        today = date.today()
        yesterday = today - timedelta(days=1)

        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=yesterday,
                amount=Decimal("1000"),
                currency="EUR",
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.BUY,
                date=yesterday,
                amount=Decimal("-500"),
                currency="EUR",
                asset_id=test_asset.id,
                quantity=Decimal("5"),
            )
        )
        session.add_all(
            [
                PriceHistory(
                    asset_id=test_asset.id,
                    date=yesterday,
                    open=Decimal("100"),
                    high=Decimal("100"),
                    low=Decimal("100"),
                    close=Decimal("100"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=test_asset.id,
                    date=today,
                    open=Decimal("110"),
                    high=Decimal("110"),
                    low=Decimal("110"),
                    close=Decimal("110"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(user_id=test_user.id)

        assert len(summary.holdings) == 1
        assert summary.holdings[0].price_change_1d == Decimal("0.1000")


class TestPortfolioServiceDateAwareDashboardData:
    @pytest.mark.asyncio
    async def test_summary_holdings_use_date_to_snapshot(self, session, test_user, broker_with_access, test_asset):
        """Summary holdings and cash must reflect selected date_to, not current ledger state."""
        broker, _ = broker_with_access
        future_asset = Asset(
            display_name="FutureOnlyAsset",
            ticker="FUTONLY",
            currency="EUR",
            type=AssetType.STOCK,
        )
        session.add(future_asset)
        await session.flush()

        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2025, 1, 1), amount=Decimal("1000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 1, 2), quantity=Decimal("1"), amount=Decimal("-100"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2025, 3, 1), quantity=Decimal("-1"), amount=Decimal("120"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=future_asset.id, type=TransactionType.BUY, date=date(2025, 3, 10), quantity=Decimal("1"), amount=Decimal("-50"), currency="EUR"),
                PriceHistory(
                    asset_id=test_asset.id,
                    date=date(2025, 1, 31),
                    open=Decimal("110"),
                    high=Decimal("110"),
                    low=Decimal("110"),
                    close=Decimal("110"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        summary = await service.get_summary(
            user_id=test_user.id,
            date_to=date(2025, 1, 31),
        )

        assert summary.cash_total.amount == Decimal("900")
        assert summary.net_worth.amount == Decimal("1010")
        assert summary.total_gain_loss.amount == Decimal("10")
        assert [holding.asset_id for holding in summary.holdings] == [test_asset.id]
        holding = summary.holdings[0]
        assert holding.quantity == Decimal("1")
        assert holding.current_price == Decimal("110")
        assert holding.current_value == Decimal("110")
        assert holding.nav_weight_percent == Decimal("10.89")

    @pytest.mark.asyncio
    async def test_positions_contribution_uses_date_to_and_other_effects(self, session, test_user, broker_with_access, test_asset):
        """Contribution rows must use date-aware status/end value and expose other period effects."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2025, 1, 1), amount=Decimal("1000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 1, 2), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2025, 2, 15), quantity=Decimal("-10"), amount=Decimal("1200"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 3, 10), quantity=Decimal("5"), amount=Decimal("-600"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2025, 2, 20), amount=Decimal("20"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2025, 2, 21), amount=Decimal("-5"), currency="EUR"),
                PriceHistory(
                    asset_id=test_asset.id,
                    date=date(2025, 1, 31),
                    open=Decimal("110"),
                    high=Decimal("110"),
                    low=Decimal("110"),
                    close=Decimal("110"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        contribution = await service.get_positions_contribution(
            user_id=test_user.id,
            date_from=date(2025, 1, 31),
            date_to=date(2025, 2, 28),
        )
        summary = await service.get_summary(
            user_id=test_user.id,
            date_from=date(2025, 1, 31),
            date_to=date(2025, 2, 28),
        )

        assert len(contribution.positions) == 1
        row = contribution.positions[0]
        assert row.is_fully_sold is True
        assert row.start_value == Decimal("1100")
        assert row.end_value == Decimal("0")
        assert row.period_unrealized_delta == Decimal("-100")
        assert row.period_realized_gain_loss == Decimal("200")
        assert row.period_pnl == Decimal("100")
        assert row.period_pnl_percent == Decimal("0.0909")

        other_effects = sorted(
            [(item.category, item.description, item.period_pnl, item.broker_id) for item in contribution.other_effects],
            key=lambda item: (item[0], item[1]),
        )
        assert other_effects == [
            ("Cost", "Unallocated costs", Decimal("-5"), broker.id),
            ("Income", "Unallocated income", Decimal("20"), broker.id),
        ]

        total_positions = sum((item.period_pnl or Decimal("0")) for item in contribution.positions)
        total_other = sum(item.period_pnl for item in contribution.other_effects)
        assert summary.period_pnl is not None
        assert total_positions + total_other == summary.period_pnl.amount

    @pytest.mark.asyncio
    async def test_dust_quantity_residual_treated_as_closed(self, session, test_user, broker_with_access, test_asset):
        """A position redeemed via many small partial sells (e.g. CROWDFUND periodic
        buybacks) can leave a tiny non-zero quantity residual because each tranche is
        rounded independently by the platform and the sum doesn't exactly cancel the
        original buy (real observed case: 8x(-0.031102) + (-0.751182) against +1 buy
        leaves +0.000002). This is not a Decimal rounding bug in our own arithmetic —
        it's baked into the recorded transaction quantities — so it must still be
        treated as a fully closed position, not a dust "still open" holding."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2022, 11, 1), amount=Decimal("2100"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2022, 11, 5), quantity=Decimal("1"), amount=Decimal("-2005"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2024, 7, 8), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2024, 8, 1), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2024, 8, 29), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2024, 9, 27), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2024, 10, 25), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2024, 11, 28), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2024, 12, 30), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2025, 5, 9), quantity=Decimal("-0.031102"), amount=Decimal("62.36"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2025, 8, 1), quantity=Decimal("-0.751182"), amount=Decimal("1506.12"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)

        # Holdings snapshot at/after the final sell must NOT list the dust residual.
        summary = await service.get_summary(user_id=test_user.id, date_to=date(2025, 8, 1))
        assert summary.holdings == []

        # Performance view for the period containing the final sell must mark it closed.
        contribution = await service.get_positions_contribution(
            user_id=test_user.id,
            date_from=date(2025, 5, 9),
            date_to=date(2025, 8, 1),
        )
        assert len(contribution.positions) == 1
        row = contribution.positions[0]
        assert row.is_fully_sold is True
        assert row.end_value == Decimal("0")
