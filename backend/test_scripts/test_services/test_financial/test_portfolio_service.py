"""
Integration tests for PortfolioService.

Uses a real AsyncSession against the test database.
Tests WAC orchestration and history aggregation.

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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.portfolio_engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, Broker, BrokerUserAccess, PriceHistory, ProviderInputType, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import BRAccessBulkItem
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import AssetPeriodContribution, IssueCode, PortfolioReportQuery
from backend.app.services.broker_service import BrokerService
from backend.app.services.portfolio_service import (
    PortfolioService,
    _portfolio_l2_cache,
    _wac_cache,
    compute_wac_iterative_multi_broker,
)
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.financial.valuation_utils import compute_holding_value
from backend.app.utils.financial.wac_utils import WACInputTX, compute_wac_from_txlist

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
        role=UserRole.OWNER,
        share_percentage=Decimal("1.0"),
    )
    session.add(access)
    await session.flush()
    return broker, access


# =============================================================================
# TestComputeWacIterativeMultiBroker
# =============================================================================


class TestComputeWacIterativeMultiBroker:
    @pytest.mark.asyncio
    async def test_empty_position_returns_zero_wac(self, session, broker_with_access, test_asset):
        """No quantity transactions -> zero WAC, no qualifying rows."""
        broker, _ = broker_with_access
        _wac_cache.clear()

        result = await compute_wac_iterative_multi_broker(
            session=session,
            broker_ids=[broker.id],
            asset_id=test_asset.id,
            as_of_date=date(2025, 1, 1),
            asset_currency="EUR",
        )

        assert result.wac is not None
        assert result.wac.code == "EUR"
        assert result.wac.amount == Decimal("0")
        assert result.wac_qualifying_txs == []
        assert result.wac_missing_pairs == []

    @pytest.mark.asyncio
    async def test_matches_manual_merged_txlist(self, session, broker_with_access, test_asset):
        """Multi-broker WAC must match manual merged txlist math."""
        broker_one, _ = broker_with_access
        broker_two = Broker(name=f"PfBroker_{utcnow().timestamp()}_wac_two")
        session.add(broker_two)
        await session.flush()

        session.add_all(
            [
                Transaction(
                    broker_id=broker_one.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date(2025, 1, 10),
                    quantity=Decimal("10"),
                    amount=Decimal("-1000"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker_two.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date(2025, 2, 1),
                    quantity=Decimal("5"),
                    amount=Decimal("-600"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker_one.id,
                    asset_id=test_asset.id,
                    type=TransactionType.SELL,
                    date=date(2025, 3, 5),
                    quantity=Decimal("-4"),
                    amount=Decimal("520"),
                    currency="EUR",
                ),
            ]
        )
        await session.flush()

        service_result = await compute_wac_iterative_multi_broker(
            session=session,
            broker_ids=[broker_two.id, broker_one.id],
            asset_id=test_asset.id,
            as_of_date=date(2025, 3, 5),
            asset_currency="EUR",
        )

        merged_rows = list(
            (
                await session.execute(
                    select(Transaction).where(
                        Transaction.broker_id.in_([broker_one.id, broker_two.id]),
                        Transaction.asset_id == test_asset.id,
                        Transaction.date <= date(2025, 3, 5),
                        Transaction.quantity.is_not(None),
                        Transaction.quantity != 0,
                    )
                )
            )
            .scalars()
            .all()
        )
        manual_result = compute_wac_from_txlist(
            [
                WACInputTX(
                    tx_id=row.id,
                    type=row.type.value if hasattr(row.type, "value") else str(row.type),
                    date=row.date,
                    quantity=row.quantity,
                    unit_cost_converted=abs(row.amount) / row.quantity if row.quantity > 0 and row.amount else Decimal("0"),
                    original_currency=row.currency or test_asset.currency,
                )
                for row in merged_rows
            ],
            "EUR",
        )

        assert service_result.wac is not None
        assert service_result.wac.code == manual_result.wac_currency == "EUR"
        assert service_result.wac.amount == manual_result.wac_amount
        assert [tx.tx_id for tx in service_result.wac_qualifying_txs] == [tx.tx_id for tx in manual_result.qualifying]

    @pytest.mark.asyncio
    async def test_adjustment_cost_basis_override_and_cache_hit(self, session, broker_with_access, test_asset, monkeypatch):
        """Positive ADJUSTMENT uses cost_basis_override; identical repeat hits cache."""
        broker_one, _ = broker_with_access
        broker_two = Broker(name=f"PfBroker_{utcnow().timestamp()}_adj_two")
        session.add(broker_two)
        await session.flush()

        session.add_all(
            [
                Transaction(
                    broker_id=broker_one.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date(2025, 1, 10),
                    quantity=Decimal("10"),
                    amount=Decimal("-1000"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker_two.id,
                    asset_id=test_asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=date(2025, 1, 20),
                    quantity=Decimal("2"),
                    amount=Decimal("0"),
                    currency="EUR",
                    cost_basis_override=Decimal("120"),
                    cost_basis_currency="EUR",
                ),
            ]
        )
        await session.flush()
        _wac_cache.clear()

        first = await compute_wac_iterative_multi_broker(
            session=session,
            broker_ids=[broker_one.id, broker_two.id],
            asset_id=test_asset.id,
            as_of_date=date(2025, 1, 20),
            asset_currency="EUR",
        )

        assert first.wac is not None
        assert first.wac.code == "EUR"
        assert first.wac.amount == Decimal("1240") / Decimal("12")
        assert [tx.type for tx in first.wac_qualifying_txs] == ["BUY", "ADJUSTMENT"]
        assert first.wac_qualifying_txs[1].unit_cost == Decimal("120")
        assert first.wac_qualifying_txs[1].currency == "EUR"

        async def fail_compute(*args, **kwargs):
            raise AssertionError("WAC math should not rerun on cache hit")

        monkeypatch.setattr(portfolio_service_module, "compute_wac_from_txlist", fail_compute)

        second = await compute_wac_iterative_multi_broker(
            session=session,
            broker_ids=[broker_two.id, broker_one.id],
            asset_id=test_asset.id,
            as_of_date=date(2025, 1, 20),
            asset_currency="EUR",
        )

        assert second.wac is not None
        assert second.wac.amount == first.wac.amount
        assert [tx.tx_id for tx in second.wac_qualifying_txs] == [tx.tx_id for tx in first.wac_qualifying_txs]

    @pytest.mark.asyncio
    async def test_foreign_currency_costs_use_bulk_fx_conversion(self, session, broker_with_access, test_asset, monkeypatch):
        """BUY + positive ADJUSTMENT in foreign ccy use converted unit costs and FX metadata."""
        broker_one, _ = broker_with_access
        broker_two = Broker(name=f"PfBroker_{utcnow().timestamp()}_fx_two")
        session.add(broker_two)
        await session.flush()

        buy_date = date(2025, 2, 10)
        adj_date = date(2025, 2, 20)
        session.add_all(
            [
                Transaction(
                    broker_id=broker_one.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=buy_date,
                    quantity=Decimal("10"),
                    amount=Decimal("-1200"),
                    currency="USD",
                ),
                Transaction(
                    broker_id=broker_two.id,
                    asset_id=test_asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=adj_date,
                    quantity=Decimal("2"),
                    amount=Decimal("0"),
                    currency="USD",
                    cost_basis_override=Decimal("150"),
                    cost_basis_currency="USD",
                ),
            ]
        )
        await session.flush()
        _wac_cache.clear()

        async def fake_convert_bulk(_session, bulk_input, raise_on_error=False):
            assert bulk_input == [
                (Currency(code="USD", amount=Decimal("1200")), "EUR", buy_date),
                (Currency(code="USD", amount=Decimal("300")), "EUR", adj_date),
            ]
            return (
                [
                    (Currency(code="EUR", amount=Decimal("1080")), buy_date, None),
                    (Currency(code="EUR", amount=Decimal("270")), adj_date, None),
                ],
                [],
            )

        monkeypatch.setattr(portfolio_service_module, "convert_bulk", fake_convert_bulk)

        result = await compute_wac_iterative_multi_broker(
            session=session,
            broker_ids=[broker_one.id, broker_two.id],
            asset_id=test_asset.id,
            as_of_date=adj_date,
            asset_currency="EUR",
            target_currency_override="EUR",
        )

        assert result.wac is not None
        assert result.wac.code == "EUR"
        assert result.wac.amount == Decimal("1350") / Decimal("12")
        assert [tx.unit_cost for tx in result.wac_qualifying_txs] == [Decimal("108"), Decimal("135")]
        assert [tx.original_unit_cost for tx in result.wac_qualifying_txs] == [Decimal("120"), Decimal("150")]
        assert [tx.original_currency for tx in result.wac_qualifying_txs] == ["USD", "USD"]
        assert [tx.fx_rate_used for tx in result.wac_qualifying_txs] == [Decimal("0.9"), Decimal("0.9")]


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
    async def test_dividend_and_interest_move_nav_exactly_like_a_deposit(self, session, test_user, broker_with_access, test_asset):
        """E2 (beta-feedback guard): a DIVIDEND and an INTEREST move nav exactly
        like a DEPOSIT of the same amount — counted once, through cash.

        The beta tester suspected income was double counted (once as cash, once
        more somewhere else). With no BUY anywhere, market_value stays 0, so
        every euro of income must appear in nav exactly once: nav deltas equal
        the row amounts, and the nav == cash + market_value invariant holds on
        every point.
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2025, 6, 1), amount=Decimal("1000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.DIVIDEND, date=date(2025, 6, 2), amount=Decimal("200"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2025, 6, 3), amount=Decimal("50"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        result = await service.get_history(user_id=test_user.id)

        points = {p.date: p for p in result}
        for d in (date(2025, 6, 1), date(2025, 6, 2), date(2025, 6, 3)):
            assert d in points, f"No history point for {d} in {sorted(points)}"

        # Exact values are owned by this test: the user and broker are fresh
        # fixtures, so no neighbour can have contributed to them.
        assert points[date(2025, 6, 1)].nav_value.amount == Decimal("1000")
        assert points[date(2025, 6, 2)].nav_value.amount == Decimal("1200"), "DIVIDEND must move nav by exactly its amount, like a deposit"
        assert points[date(2025, 6, 3)].nav_value.amount == Decimal("1250"), "INTEREST must move nav by exactly its amount, like a deposit"

        for point in result:
            assert point.market_value.amount == Decimal("0"), f"no BUY happened — market value must stay 0 at {point.date}"
            assert point.nav_value == point.cash_value + point.market_value, f"NAV invariant violated at {point.date}: nav={point.nav_value} != cash+market_value"

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
                role=UserRole.OWNER,
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


class TestRoleAwareShareScaling:
    """F2 — broker share scaling is role-aware.

    An OWNER row scales the broker's contribution by share_percentage: 0% is a
    valid share and contributes nothing, NULL (legacy unset) means 100%.
    EDITOR/VIEWER rows always carry share 0 by schema rule, yet they must still
    see the FULL broker data — an intermediate version of this fix scaled them
    to 0 too and blanked every editor's dashboard/risk view (caught in CI).
    """

    async def _make_broker_with_role(self, session, user: User, role: str, share: Decimal | None, deposit: str = "1000") -> Broker:
        """One broker, one access row with the given role/share, one DEPOSIT."""
        broker = Broker(name=f"PfBroker_F2_{role}_{share}_{utcnow().timestamp()}")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=role, share_percentage=share))
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 1, 1),
                amount=Decimal(deposit),
                currency="EUR",
            )
        )
        await session.flush()
        return broker

    @pytest.mark.asyncio
    async def test_owner_with_zero_share_contributes_nothing(self, session, test_user):
        """OWNER share=0% is valid and contributes 0 to the summary."""
        await self._make_broker_with_role(session, test_user, "OWNER", Decimal("0"))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id)

        assert summary.cash_total.amount == Decimal("0"), f"0%-owner cash must be 0, got {summary.cash_total}"
        assert summary.net_worth.amount == Decimal("0"), f"0%-owner net_worth must be 0, got {summary.net_worth}"
        assert summary.total_invested.amount == Decimal("0")

    @pytest.mark.asyncio
    async def test_owner_with_full_share_contributes_full(self, session, test_user):
        """OWNER share=1 boundary: contributes 100% (the scale=1 anchor).

        NOTE on NULL: the column is NOT NULL DEFAULT 1, so a NULL share cannot
        exist at this layer — the `is not None` branch in the fix is reachable
        only from API payloads, and that semantic is covered frontend-side
        (brokerStore.getOwnedBrokers treats a null share as 100% for an OWNER).
        """
        await self._make_broker_with_role(session, test_user, "OWNER", Decimal("1"))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id)

        assert summary.cash_total.amount == Decimal("1000"), f"full-share owner must see full cash, got {summary.cash_total}"
        assert summary.net_worth.amount == Decimal("1000")

    @pytest.mark.asyncio
    async def test_owner_with_partial_share_scales(self, session, test_user):
        """OWNER share=30% contributes exactly 30% — pins the scale direction."""
        await self._make_broker_with_role(session, test_user, "OWNER", Decimal("0.3"))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id)

        assert summary.cash_total.amount == Decimal("300"), f"30%-owner cash must be 300, got {summary.cash_total}"
        assert summary.net_worth.amount == Decimal("300")

    @pytest.mark.asyncio
    async def test_editor_sees_full_data_despite_zero_share(self, session, test_user):
        """EDITOR rows carry share 0 by schema rule but must see FULL data.

        This is the risk-API regression lock: scale-by-share without the role
        check zeroes every non-owner's view.
        """
        await self._make_broker_with_role(session, test_user, "EDITOR", Decimal("0"))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id)

        assert summary.cash_total.amount == Decimal("1000"), f"EDITOR must see full cash, got {summary.cash_total}"
        assert summary.net_worth.amount == Decimal("1000"), f"EDITOR must see full net worth, got {summary.net_worth}"

    @pytest.mark.asyncio
    async def test_viewer_sees_full_data_despite_zero_share(self, session, test_user):
        """VIEWER rows carry share 0 by schema rule but must see FULL data."""
        await self._make_broker_with_role(session, test_user, "VIEWER", Decimal("0"))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id)

        assert summary.cash_total.amount == Decimal("1000"), f"VIEWER must see full cash, got {summary.cash_total}"
        assert summary.net_worth.amount == Decimal("1000")

    @pytest.mark.asyncio
    async def test_positions_contribution_scales_by_owner_share_not_by_role(self, session, test_user, test_asset):
        """get_positions_contribution applies the same rule: the same access row
        flipped OWNER(0) → EDITOR(0) → OWNER(NULL) → OWNER(0.3) must move the
        numbers — the role/share pair is the only variable."""
        broker = Broker(name=f"PfBroker_F2_contrib_{utcnow().timestamp()}")
        session.add(broker)
        await session.flush()
        access = BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("0"))
        session.add(access)
        session.add_all(
            [
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 1, 2), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.DIVIDEND, date=date(2025, 1, 15), amount=Decimal("100"), currency="EUR"),
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

        async def contribution_row() -> AssetPeriodContribution:
            contribution = await service.get_positions_contribution(user_id=test_user.id, date_from=date(2025, 1, 1), date_to=date(2025, 1, 31))
            row = next((p for p in contribution.positions if p.broker_id == broker.id and p.asset_id == test_asset.id), None)
            assert row is not None, "position row for this test's broker+asset missing"
            return row

        # OWNER share=0 → everything scaled to nothing (income 100×0, qty 10×0).
        # The row contract encodes "zero" as None (`income if income else None`),
        # so normalize before comparing: the assertion is "contributes nothing".
        row = await contribution_row()
        assert (row.period_income or Decimal("0")) == Decimal("0"), f"0%-owner income must be zero, got {row.period_income}"
        assert row.end_value == Decimal("0"), f"0%-owner end value must be 0, got {row.end_value}"

        # Same row as EDITOR (share stays 0 per the schema rule) → FULL data.
        # Assign the enum, not a raw string: the ORM does not coerce attribute
        # writes, and the engine's cache fingerprint reads `role.value` — a raw
        # str would never occur from a DB load, so the test must not invent one.
        access.role = UserRole.EDITOR
        await session.flush()
        row = await contribution_row()
        assert row.period_income == Decimal("100"), f"EDITOR income must be full, got {row.period_income}"
        assert row.end_value == Decimal("1100"), f"EDITOR end value must be full (10 × 110), got {row.end_value}"

        # OWNER with share=1 → full again (the scale=1 anchor).
        access.role = UserRole.OWNER
        access.share_percentage = Decimal("1")
        await session.flush()
        row = await contribution_row()
        assert row.period_income == Decimal("100"), f"full-share owner income must be full, got {row.period_income}"
        assert row.end_value == Decimal("1100")

        # OWNER with 30% → exactly 30%.
        access.share_percentage = Decimal("0.3")
        await session.flush()
        row = await contribution_row()
        assert row.period_income == Decimal("30"), f"30%-owner income must be 30, got {row.period_income}"
        assert row.end_value == Decimal("330"), f"30%-owner end value must be 330 (3 × 110), got {row.end_value}"


class TestAccessFingerprintCacheBust:
    """R2-F2a — role/share edits must bust the report caches.

    get_report is guarded by two caches: the L2 report cache (30 min TTL) and
    the engine's daily-states blob cache (24 h TTL). Both keys now include an
    access fingerprint (broker_id, role, share per access row). Before that, a
    share edit moved no tx/price fingerprint, so every scaled number stayed
    stale for the whole TTL — the user changed their ownership % and kept
    seeing the old values.

    One test suffices for both layers: the L2 key change forces the miss that
    reaches the engine, and the engine blob key change is what makes THAT
    recompute return fresh numbers instead of a stale blob — a missing
    fingerprint in either layer shows up as r2 still saying 1000.
    """

    @pytest.mark.asyncio
    async def test_share_change_busts_report_caches(self, session, test_user):
        broker = Broker(name=f"PfBroker_F2cache_{utcnow().timestamp()}")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 1, 1),
                amount=Decimal("1000"),
                currency="EUR",
            )
        )
        await session.flush()

        service = PortfolioService(session)
        query = PortfolioReportQuery(include_summary=True, include_history=False, include_allocation_history=False)

        async def net_worth() -> Decimal:
            report = await service.get_report(test_user.id, query)
            assert report.summary is not None
            return report.summary.net_worth.amount

        async def set_share(share: str) -> None:
            """Through BrokerService.bulk_update_access — the production write path."""
            ok, message, _ = await BrokerService(session).bulk_update_access(
                broker.id,
                [BRAccessBulkItem(user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal(share))],
                current_user_id=test_user.id,
            )
            assert ok, f"share update to {share} refused: {message}"

        # Baseline at 100%.
        assert await net_worth() == Decimal("1000")

        # Share 1.0 → 0.3: both cache keys must move, so this is a MISS and a
        # recompute — not a stale hit. 300, not 1000.
        await set_share("0.3")
        assert await net_worth() == Decimal("300"), "share edit did not bust the report caches — stale 1000 served"

        # And back: 1.0 restores the original numbers (a legitimately-cached or
        # freshly-recomputed 1000 — same fingerprint, same truth).
        await set_share("1")
        assert await net_worth() == Decimal("1000")

    @pytest.mark.asyncio
    async def test_role_change_busts_report_caches(self, session, test_user):
        """Same fingerprint, other field: OWNER(1) → EDITOR keeps the FULL numbers
        (role-aware scaling, F2) — but only if the cache actually misses. A stale
        hit would be invisible here numerically, so this flips twice: 1 → 0.5 →
        EDITOR. If the role were missing from the key, the second flip would still
        serve the cached 500."""
        broker = Broker(name=f"PfBroker_F2role_{utcnow().timestamp()}")
        session.add(broker)
        await session.flush()
        # A co-owner (share 0) exists only so the bulk path allows the last-step
        # demotion (F4: a last OWNER cannot demote themselves). Their row never
        # enters test_user's report scope — get_report filters accesses by
        # user_id — so the numbers below are test_user's alone.
        co_owner = User(username=f"pfco_{utcnow().timestamp()}", email=f"pfco_{utcnow().timestamp()}@test.com", hashed_password="fakehash", is_active=True)
        session.add(co_owner)
        await session.flush()
        session.add_all(
            [
                BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
                BrokerUserAccess(broker_id=broker.id, user_id=co_owner.id, role=UserRole.OWNER, share_percentage=Decimal("0")),
            ]
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 1, 1),
                amount=Decimal("1000"),
                currency="EUR",
            )
        )
        await session.flush()

        service = PortfolioService(session)
        query = PortfolioReportQuery(include_summary=True, include_history=False, include_allocation_history=False)

        assert (await service.get_report(test_user.id, query)).summary.net_worth.amount == Decimal("1000")

        # Halve the share: 500, cached under the (OWNER, 0.5) fingerprint.
        ok, message, _ = await BrokerService(session).bulk_update_access(
            broker.id,
            [
                BRAccessBulkItem(user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("0.5")),
                BRAccessBulkItem(user_id=co_owner.id, role=UserRole.OWNER, share_percentage=Decimal("0")),
            ],
            current_user_id=test_user.id,
        )
        assert ok, message
        assert (await service.get_report(test_user.id, query)).summary.net_worth.amount == Decimal("500")

        # OWNER(0.5) → EDITOR(0): role-aware scaling says EDITOR sees FULL data
        # (1000). A cache keyed without the role would serve the stale 500.
        ok, message, _ = await BrokerService(session).bulk_update_access(
            broker.id,
            [
                BRAccessBulkItem(user_id=test_user.id, role=UserRole.EDITOR, share_percentage=Decimal("0")),
                BRAccessBulkItem(user_id=co_owner.id, role=UserRole.OWNER, share_percentage=Decimal("0")),
            ],
            current_user_id=test_user.id,
        )
        assert ok, message
        assert (await service.get_report(test_user.id, query)).summary.net_worth.amount == Decimal("1000"), "role edit did not bust the report caches — stale 500 served"


class TestPortfolioServicePrivateHelpers:
    @pytest.mark.asyncio
    async def test_price_bulk_loader_quote_base_map_and_latest_price(self, session):
        """Private loaders return sorted filtered data and latest tuple."""
        first_asset = Asset(
            display_name=f"LoaderAssetA_{utcnow().timestamp()}",
            ticker="LOADA",
            currency="EUR",
            type=AssetType.STOCK,
            quote_base_quantity=100,
        )
        second_asset = Asset(
            display_name=f"LoaderAssetB_{utcnow().timestamp()}",
            ticker="LOADB",
            currency="USD",
            type=AssetType.STOCK,
        )
        no_price_asset = Asset(
            display_name=f"LoaderAssetC_{utcnow().timestamp()}",
            ticker="LOADC",
            currency="EUR",
            type=AssetType.STOCK,
        )
        session.add_all([first_asset, second_asset, no_price_asset])
        await session.flush()

        session.add_all(
            [
                PriceHistory(
                    asset_id=first_asset.id,
                    date=date(2025, 1, 1),
                    open=Decimal("99"),
                    high=Decimal("99"),
                    low=Decimal("99"),
                    close=Decimal("99"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=first_asset.id,
                    date=date(2025, 1, 3),
                    open=Decimal("100"),
                    high=Decimal("100"),
                    low=Decimal("100"),
                    close=Decimal("100"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=first_asset.id,
                    date=date(2025, 1, 5),
                    open=Decimal("101"),
                    high=Decimal("101"),
                    low=Decimal("101"),
                    close=Decimal("101"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=second_asset.id,
                    date=date(2025, 1, 4),
                    open=Decimal("55"),
                    high=Decimal("55"),
                    low=Decimal("55"),
                    close=Decimal("55"),
                    volume=Decimal("1"),
                    currency="USD",
                    source_plugin_key="manual_test",
                ),
            ]
        )
        await session.flush()

        service = PortfolioService(session)

        assert await service._bulk_load_asset_prices(set(), date(2025, 1, 1), date(2025, 1, 5)) == {}
        assert await service._get_quote_base_map(set()) == {}

        bulk = await service._bulk_load_asset_prices(
            {first_asset.id, second_asset.id},
            date(2025, 1, 2),
            date(2025, 1, 5),
        )
        assert bulk == {
            first_asset.id: [
                (date(2025, 1, 3), Decimal("100"), "EUR"),
                (date(2025, 1, 5), Decimal("101"), "EUR"),
            ],
            second_asset.id: [
                (date(2025, 1, 4), Decimal("55"), "USD"),
            ],
        }

        quote_map = await service._get_quote_base_map({first_asset.id, second_asset.id, no_price_asset.id})
        assert quote_map == {
            first_asset.id: 100,
            second_asset.id: 1,
            no_price_asset.id: 1,
        }


# =============================================================================
# TestTransactionImpliedDataQuality
# =============================================================================


class TestTransactionImpliedDataQuality:
    """TRANSACTION_IMPLIED is an *as-of* health flag: it fires only when a held asset is
    STILL valued at cost on the valuation date (date_to), respecting a placement grace
    period for brand-new acquisitions.

    Regression test: previously the flag was aggregated across the engine's full-lifetime
    daily_states (always computed from t=0 for correct cumulative values). Even after a
    placement gap (e.g. BTP collocamento) was priced, or a fund received its first provider
    quotes, the asset kept showing the "valued at cost — no market price" warning forever,
    contradicting the message's own "as of {as_of_date}" wording. The flag now reflects only
    the valuation-date state, so a currently-priced asset clears the warning.
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
    async def test_resolved_gap_with_current_price_not_flagged(self, session, test_user, broker_with_access, test_asset_with_provider):
        """A placement gap that has since been priced must NOT be flagged as 'valued at
        cost' once a market price exists on the valuation date — even when the report range
        still spans the long historical at-cost period. This is the exact reported bug: a
        fund priced only from its first provider sync onward stayed flagged forever despite a
        fresh current price. date_from no longer affects the flag (it is purely as-of)."""
        broker, _ = broker_with_access
        buy_date = date(2024, 1, 1)
        report_end = date(2024, 6, 1)
        # Fresh quote two days before the report date -> current value is MARKET, not cost.
        fresh_price_date = report_end - timedelta(days=2)
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=buy_date, amount=Decimal("10000"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset_with_provider.id, type=TransactionType.BUY, date=buy_date, quantity=Decimal("100"), amount=Decimal("-9950"), currency="EUR"),
                PriceHistory(asset_id=test_asset_with_provider.id, date=fresh_price_date, open=Decimal("100"), high=Decimal("100"), low=Decimal("100"), close=Decimal("100"), volume=Decimal("1"), currency="EUR", source_plugin_key="manual_test"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)

        # Full range spans the historical at-cost period, but the asset is currently priced.
        summary_all = await service.get_summary(user_id=test_user.id, date_to=report_end)
        assert IssueCode.TRANSACTION_IMPLIED not in {i.code for i in summary_all.data_quality.issues}

        # Narrow range behaves identically (the flag is as-of, not range-dependent).
        summary_narrow = await service.get_summary(user_id=test_user.id, date_from=date(2024, 3, 1), date_to=report_end)
        assert IssueCode.TRANSACTION_IMPLIED not in {i.code for i in summary_narrow.data_quality.issues}


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
                amount=Decimal("-450"),
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
        assert summary.holdings[0].gain_loss_change_1d == Decimal("50")
        assert summary.holdings[0].gain_loss_change_1d_percent == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_holding_gain_loss_change_1d_respects_quote_base_quantity(self, session, test_user, broker_with_access):
        """Regression test for a real prod bug report: a BTP bond (quote_base_quantity=100,
        i.e. quoted per 100 nominal) showed an absurd +93.60% "1-day" P&L swing on a stable
        position. Root cause: gain_loss_change_1d used to do `(current_price - prev_price) *
        quantity` directly, ignoring quote_base_quantity — unlike market_value/gain_loss,
        which already go through compute_holding_value() for this exact scaling. This test
        uses quantity=10000 (nominal) + quote_base_quantity=100, so a naive unscaled calc
        would be 100x too large; a correctly-scaled calc must match compute_holding_value().
        """
        broker, _ = broker_with_access
        today = date.today()
        yesterday = today - timedelta(days=1)

        bond_asset = Asset(
            display_name=f"TestBTP_{utcnow().timestamp()}",
            asset_type=AssetType.BOND,
            currency="EUR",
            quote_base_quantity=100,
        )
        session.add(bond_asset)
        await session.flush()

        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=yesterday,
                amount=Decimal("10000"),
                currency="EUR",
            )
        )
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.BUY,
                date=yesterday,
                # 10000 nominal bought at an implied rate of 97.70 per 100 nominal.
                amount=Decimal("-9770"),
                currency="EUR",
                asset_id=bond_asset.id,
                quantity=Decimal("10000"),
            )
        )
        session.add_all(
            [
                PriceHistory(
                    asset_id=bond_asset.id,
                    date=yesterday,
                    open=Decimal("98.51"),
                    high=Decimal("98.51"),
                    low=Decimal("98.51"),
                    close=Decimal("98.51"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=bond_asset.id,
                    date=today,
                    open=Decimal("98.70"),
                    high=Decimal("98.70"),
                    low=Decimal("98.70"),
                    close=Decimal("98.70"),
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
        holding = summary.holdings[0]

        # market_value already applies quote_base_quantity scaling — use it as the
        # independent source of truth for what "correctly scaled" looks like.
        expected_change_1d = compute_holding_value(Decimal("10000"), Decimal("98.70"), 100) - compute_holding_value(Decimal("10000"), Decimal("98.51"), 100)
        assert expected_change_1d == Decimal("19.00")  # sanity-check the fixture's own arithmetic
        assert holding.gain_loss_change_1d == expected_change_1d

        # A pre-fix implementation would have produced (98.70 - 98.51) * 10000 = 1900 —
        # 100x too large. Explicitly guard against regressing to that.
        assert holding.gain_loss_change_1d != Decimal("1900")

        previous_position_value = compute_holding_value(Decimal("10000"), Decimal("98.51"), 100)
        expected_pct = (expected_change_1d / abs(previous_position_value) * 100).quantize(Decimal("0.01"))
        assert holding.gain_loss_change_1d_percent == expected_pct

    @pytest.mark.asyncio
    async def test_holding_daily_percent_uses_previous_position_value(self, session, test_user, broker_with_access):
        """A small market move must stay small even when unrealized P&L is near zero."""
        broker, _ = broker_with_access
        today = date.today()
        yesterday = today - timedelta(days=1)
        asset = Asset(
            display_name=f"DailyPercent_{utcnow().timestamp()}",
            asset_type=AssetType.ETF,
            currency="EUR",
            quote_base_quantity=1,
        )
        session.add(asset)
        await session.flush()
        session.add_all(
            [
                Transaction(
                    broker_id=broker.id,
                    type=TransactionType.BUY,
                    date=yesterday,
                    amount=Decimal("-473.11"),
                    currency="EUR",
                    asset_id=asset.id,
                    quantity=Decimal("17"),
                ),
                PriceHistory(
                    asset_id=asset.id,
                    date=yesterday,
                    close=Decimal("27.81"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=asset.id,
                    date=today,
                    close=Decimal("27.84"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
            ]
        )
        await session.flush()

        summary = await PortfolioService(session).get_summary(user_id=test_user.id)
        holding = next(item for item in summary.holdings if item.asset_id == asset.id)

        assert holding.gain_loss_change_1d == Decimal("0.51")
        assert holding.gain_loss_change_1d_percent == Decimal("0.11")


class TestPortfolioServiceDateAwareDashboardData:
    @pytest.mark.asyncio
    async def test_summary_selects_historical_buy_reference_before_future_buy(self, session, test_user, broker_with_access, test_asset):
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 1, 2), quantity=Decimal("1"), amount=Decimal("-100"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 1, 10), quantity=Decimal("1"), amount=Decimal("-120"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        historical = await service.get_summary(user_id=test_user.id, date_to=date(2025, 1, 5))
        current = await service.get_summary(user_id=test_user.id, date_to=date(2025, 1, 15))

        historical_holding = historical.holdings[0]
        assert historical_holding.quantity == Decimal("1")
        assert historical_holding.current_price == Decimal("100")
        assert historical_holding.current_value == Decimal("100")
        assert historical_holding.valuation_reference_date == date(2025, 1, 2)
        assert historical_holding.valuation_reference_unit_price == Decimal("100")

        current_holding = current.holdings[0]
        assert current_holding.quantity == Decimal("2")
        assert current_holding.current_price == Decimal("120")
        assert current_holding.current_value == Decimal("240")
        assert current_holding.valuation_reference_date == date(2025, 1, 10)
        assert current_holding.valuation_reference_unit_price == Decimal("120")

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
        assert holding.valuation_source == "MARKET_PRICE"
        assert holding.valuation_reference_date == date(2025, 1, 31)
        assert holding.valuation_reference_unit_price == Decimal("110")
        assert holding.valuation_reference_currency == "EUR"
        assert holding.missing_fx_pair is None
        assert holding.nav_weight_percent == Decimal("10.89")

    @pytest.mark.asyncio
    async def test_summary_maps_seed_cost_valuation_reference(self, session, test_user, broker_with_access, test_asset):
        broker, _ = broker_with_access
        split_event = AssetEvent(
            asset_id=test_asset.id,
            date=date(2025, 1, 10),
            type=AssetEventType.SPLIT,
            value=Decimal("2"),
            currency="EUR",
        )
        session.add(split_event)
        await session.flush()
        session.add_all(
            [
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=date(2025, 1, 2),
                    quantity=Decimal("5"),
                    amount=Decimal("0"),
                    currency="EUR",
                    cost_basis_override=Decimal("20"),
                    cost_basis_currency="EUR",
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    asset_event_id=split_event.id,
                    type=TransactionType.ADJUSTMENT,
                    date=date(2025, 1, 10),
                    quantity=Decimal("5"),
                    amount=Decimal("0"),
                    currency="EUR",
                ),
            ]
        )
        await session.flush()

        summary = await PortfolioService(session).get_summary(
            user_id=test_user.id,
            date_to=date(2025, 1, 31),
        )

        assert summary.net_worth.amount == Decimal("100")
        assert len(summary.holdings) == 1
        holding = summary.holdings[0]
        assert holding.quantity == Decimal("10")
        assert holding.current_price == Decimal("10")
        assert holding.current_value == Decimal("100")
        assert holding.gain_loss == Decimal("0")
        assert holding.valuation_source == "LAST_TRADE_PRICE"
        assert holding.valuation_effective_unit_price == Decimal("10")
        assert holding.valuation_effective_currency == "EUR"
        assert holding.valuation_reference_date == date(2025, 1, 2)
        assert holding.valuation_reference_unit_price == Decimal("20")
        assert holding.valuation_reference_currency == "EUR"
        assert holding.valuation_split_adjusted is True
        assert holding.missing_fx_pair is None

    @pytest.mark.asyncio
    async def test_summary_deduplicates_shared_split_event_and_maps_effective_price(self, session, test_user, broker_with_access, test_asset):
        broker_one, _ = broker_with_access
        broker_two = Broker(name=f"PfBroker_{utcnow().timestamp()}_split_two")
        session.add(broker_two)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker_two.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))

        split_event = AssetEvent(
            asset_id=test_asset.id,
            date=date(2025, 1, 5),
            type=AssetEventType.SPLIT,
            value=Decimal("2"),
            currency="EUR",
        )
        session.add(split_event)
        await session.flush()

        session.add_all(
            [
                Transaction(broker_id=broker_one.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 1, 2), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
                Transaction(broker_id=broker_two.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2025, 1, 2), quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
                Transaction(broker_id=broker_one.id, asset_id=test_asset.id, asset_event_id=split_event.id, type=TransactionType.ADJUSTMENT, date=date(2025, 1, 5), quantity=Decimal("10"), amount=Decimal("0"), currency="EUR"),
                Transaction(broker_id=broker_two.id, asset_id=test_asset.id, asset_event_id=split_event.id, type=TransactionType.ADJUSTMENT, date=date(2025, 1, 5), quantity=Decimal("10"), amount=Decimal("0"), currency="EUR"),
            ]
        )
        await session.flush()

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, date_to=date(2025, 1, 10))

        assert len(summary.holdings) == 2
        for holding in summary.holdings:
            assert holding.quantity == Decimal("20")
            assert holding.current_price == Decimal("50")
            assert holding.current_value == Decimal("1000")
            assert holding.valuation_effective_unit_price == Decimal("50")
            assert holding.valuation_effective_currency == "EUR"
            assert holding.valuation_reference_date == date(2025, 1, 2)
            assert holding.valuation_reference_unit_price == Decimal("100")
            assert holding.valuation_reference_currency == "EUR"
            assert holding.valuation_split_adjusted is True

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

    @pytest.mark.asyncio
    async def test_positions_contribution_closed_position_has_annualized_return(self, session, test_user, broker_with_access, test_asset):
        """A fully-closed position (no still-open lot) must still expose an annualized
        return in the performance/contribution table. The generic path cannot annualize
        it — there is no open lot to date the window start and no end cost basis to
        normalize against — so it falls back to the realized net return over the
        position's real flight time [oldest lot opened -> last lot closed], normalized on
        the capital actually deployed. Modelled on the real "MARINA DI SCARLINO"
        (Recrowd/CROWDFUND) case: ~2005 deployed, +257.32 interest, -66.92 tax, sold flat
        -> ~+9.5% total over ~1000 days -> ~+3.4%/yr net."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2022, 11, 1), amount=Decimal("2100"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.BUY, date=date(2022, 11, 5), quantity=Decimal("1"), amount=Decimal("-2005"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.INTEREST, date=date(2023, 11, 5), amount=Decimal("257.32"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.TAX, date=date(2023, 11, 6), amount=Decimal("-66.92"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.SELL, date=date(2025, 8, 1), quantity=Decimal("-1"), amount=Decimal("2005"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        contribution = await service.get_positions_contribution(
            user_id=test_user.id,
            date_to=date(2025, 8, 1),
        )

        assert len(contribution.positions) == 1
        row = contribution.positions[0]
        assert row.is_fully_sold is True
        assert row.period_pnl == Decimal("190.40")  # realized 0 + interest 257.32 - tax 66.92
        # Closed-position annualized: ~9.5% total over ~1000 days -> ~+3.4%/yr net.
        assert row.annualized_return is not None
        assert Decimal("0.02") < row.annualized_return < Decimal("0.05")

    @pytest.mark.asyncio
    async def test_positions_contribution_includes_income_only_asset_rows(self, session, test_user, broker_with_access, test_asset):
        """Asset-linked income/fee rows without BUY/SELL still become contribution rows."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.DIVIDEND,
                    date=date(2025, 4, 10),
                    amount=Decimal("30"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.FEE,
                    date=date(2025, 4, 11),
                    amount=Decimal("-4"),
                    currency="EUR",
                ),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        contribution = await service.get_positions_contribution(
            user_id=test_user.id,
            date_from=date(2025, 4, 1),
            date_to=date(2025, 4, 30),
        )

        assert len(contribution.positions) == 1
        row = contribution.positions[0]
        assert row.asset_id == test_asset.id
        assert row.broker_id == broker.id
        assert row.period_income == Decimal("30")
        assert row.period_fees_taxes == Decimal("4")
        assert row.period_pnl == Decimal("26")
        assert row.start_value == Decimal("0")
        assert row.end_value == Decimal("0")
        assert row.is_fully_sold is True
        assert contribution.unallocated == []
        assert contribution.other_effects == []
        assert contribution.gross_gains == Decimal("26")
        assert contribution.gross_losses == Decimal("0")

    @pytest.mark.asyncio
    async def test_positions_contribution_in_kind_adjustment_is_held_not_fully_sold(self, session, test_user, broker_with_access, test_asset):
        """An in-kind ADJUSTMENT-seeded position held through the period must be treated as
        held (end value + unrealized delta + net annualized return), not collapsed to
        fully-sold. Regression: qty was summed over BUY/SELL only, so ADJUSTMENT/TRANSFER
        (e.g. succession in-kind transfers) reported qty 0 at period end -> empty column."""
        broker, _ = broker_with_access
        session.add_all(
            [
                # In-kind seed: +100 units at a per-unit cost of 10 (amount 0 = no cash leg).
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=date(2024, 1, 1),
                    quantity=Decimal("100"),
                    amount=Decimal("0"),
                    cost_basis_override=Decimal("10"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.INTEREST,
                    date=date(2024, 6, 1),
                    amount=Decimal("50"),
                    currency="EUR",
                ),
                PriceHistory(
                    asset_id=test_asset.id,
                    date=date(2025, 1, 10),
                    open=Decimal("11"),
                    high=Decimal("11"),
                    low=Decimal("11"),
                    close=Decimal("11"),
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
            date_from=date(2023, 12, 1),
            date_to=date(2025, 1, 15),
        )

        assert len(contribution.positions) == 1
        row = contribution.positions[0]
        assert row.asset_id == test_asset.id
        # Held, not fully-sold: qty at end = +100 from the ADJUSTMENT.
        assert row.is_fully_sold is False
        assert row.end_value == Decimal("1100")  # 100 units * price 11
        assert row.start_value == Decimal("0")  # seeded after date_from
        assert row.period_unrealized_delta == Decimal("100")  # mv 1100 - cost 1000
        assert row.period_income == Decimal("50")
        assert row.period_pnl == Decimal("150")  # 100 unrealized + 50 income
        # start_value == 0 -> period_pnl_percent stays None (unchanged semantics),
        # but the net annualized return uses the end cost basis as fallback base.
        assert row.period_pnl_percent is None
        assert row.annualized_return is not None
        assert row.annualized_return > Decimal("0")  # net positive return, >30-day window
        assert row.oldest_open_lot_date == date(2024, 1, 1)


class TestPortfolioServiceGetReport:
    @pytest.mark.asyncio
    async def test_get_report_includes_requested_sections(self, session, test_user, broker_with_access, test_asset):
        """Full-feature report populates summary/history/allocation/positions sections in one call."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(
                    broker_id=broker.id,
                    type=TransactionType.DEPOSIT,
                    date=date(2025, 7, 1),
                    amount=Decimal("1000"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date(2025, 7, 2),
                    quantity=Decimal("5"),
                    amount=Decimal("-500"),
                    currency="EUR",
                ),
                PriceHistory(
                    asset_id=test_asset.id,
                    date=date(2025, 7, 3),
                    open=Decimal("105"),
                    high=Decimal("105"),
                    low=Decimal("105"),
                    close=Decimal("105"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
            ]
        )
        await session.flush()
        _portfolio_l2_cache.clear()

        service = PortfolioService(session)
        report = await service.get_report(
            user_id=test_user.id,
            query=PortfolioReportQuery(
                broker_ids=[broker.id],
                include_summary=True,
                include_history=True,
                include_allocation_history=True,
                include_positions_contribution=True,
                date_range={"start": "2025-07-01", "end": "2025-07-03"},
            ),
        )

        assert report.summary is not None
        assert report.history is not None
        assert report.allocation_history is not None
        assert report.positions_contribution is not None
        assert report.summary.net_worth.amount == Decimal("1025")
        assert [point.date for point in report.history] == [date(2025, 7, 1), date(2025, 7, 2), date(2025, 7, 3)]
        assert report.allocation_history.type
        assert report.positions_contribution.positions
        assert report.metadata.included_features == [
            "summary",
            "history",
            "allocation_history",
            "positions_contribution",
        ]

    @pytest.mark.asyncio
    async def test_get_report_respects_include_flags(self, session, test_user, broker_with_access):
        """When all include flags false, report omits optional sections but keeps metadata/data-quality."""
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 5, 1),
                amount=Decimal("1000"),
                currency="EUR",
            )
        )
        await session.flush()
        _portfolio_l2_cache.clear()

        service = PortfolioService(session)
        report = await service.get_report(
            user_id=test_user.id,
            query=PortfolioReportQuery(
                broker_ids=[broker.id],
                include_summary=False,
                include_history=False,
                include_allocation_history=False,
                include_positions_contribution=False,
            ),
        )

        assert report.summary is None
        assert report.history is None
        assert report.allocation_history is None
        assert report.positions_contribution is None
        assert report.data_quality is not None
        assert report.metadata.broker_ids == [broker.id]
        assert report.metadata.included_features == []

    @pytest.mark.asyncio
    async def test_get_report_uses_layer2_cache(self, session, test_user, broker_with_access, monkeypatch):
        """Second identical get_report call should return cached report without rerunning engine."""
        broker, _ = broker_with_access
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2025, 6, 1),
                amount=Decimal("750"),
                currency="EUR",
            )
        )
        await session.flush()
        _portfolio_l2_cache.clear()

        service = PortfolioService(session)
        query = PortfolioReportQuery(
            broker_ids=[broker.id],
            include_summary=False,
            include_history=False,
            include_allocation_history=False,
            include_positions_contribution=False,
        )
        first = await service.get_report(user_id=test_user.id, query=query)

        async def fail_calculate(self, *args, **kwargs):
            raise AssertionError("Engine should not run on layer-2 cache hit")

        monkeypatch.setattr(portfolio_engine_module.PortfolioCalculationEngine, "calculate", fail_calculate)

        second = await service.get_report(user_id=test_user.id, query=query)

        assert second.model_dump() == first.model_dump()

    @pytest.mark.asyncio
    async def test_get_report_narrower_date_to_not_corrupted_by_wider_blob_cache(self, session, test_user, broker_with_access, test_asset):
        """Regression test for dashboard KPI cards showing 0-delta for a custom date range.

        Root cause: the L1 portfolio "blob" cache (portfolio_engine.py) is keyed by
        tx/price fingerprints, NOT by date range. Its old "contained" condition
        (blob_to >= actual_to) returned a wider cached blob unmodified whenever a
        narrower date_to was requested with an identical fingerprint — which happens
        whenever no new PriceHistory rows were synced between the two requested end
        dates (exactly what happens over a weekend). This leaked "phantom" future
        days (forward-filled from the last known price) into `history`, so the
        frontend's day-over-day KPI delta (history[-1] - history[-2]) compared two
        identical phantom days instead of the real last two days, and `get_summary()`
        reported the wrong end-of-period state.
        """
        broker, _ = broker_with_access
        day1, day2, day3 = date(2025, 6, 1), date(2025, 6, 2), date(2025, 6, 3)
        day4, day5 = date(2025, 6, 4), date(2025, 6, 5)
        session.add_all(
            [
                Transaction(
                    broker_id=broker.id,
                    type=TransactionType.DEPOSIT,
                    date=day1,
                    amount=Decimal("1000"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=day2,
                    quantity=Decimal("5"),
                    amount=Decimal("-500"),
                    currency="EUR",
                ),
                PriceHistory(
                    asset_id=test_asset.id,
                    date=day2,
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
                    date=day3,
                    open=Decimal("110"),
                    high=Decimal("110"),
                    low=Decimal("110"),
                    close=Decimal("110"),
                    volume=Decimal("1"),
                    currency="EUR",
                    source_plugin_key="manual_test",
                ),
                # Deliberately no PriceHistory rows after day3: day4/day5 are
                # backward-filled from day3's close, and the tx/price fingerprint
                # for date_to=day3 is identical to date_to=day5 — the scenario that
                # triggers the blob cache bug.
            ]
        )
        await session.flush()
        _portfolio_l2_cache.clear()
        portfolio_engine_module._portfolio_blob_cache.clear()

        service = PortfolioService(session)

        # Wide call: populates the L1 blob cache with daily_states day1..day5.
        wide = await service.get_report(
            user_id=test_user.id,
            query=PortfolioReportQuery(
                broker_ids=[broker.id],
                include_summary=True,
                include_history=True,
                date_range={"start": str(day1), "end": str(day5)},
            ),
        )
        assert [p.date for p in wide.history] == [day1, day2, day3, day4, day5]
        assert wide.metadata.computed_date_to == day5

        # Narrow call: same tx/price fingerprint as the wide call (no PriceHistory
        # rows exist between day3 and day5), so the L1 blob cache key collides with
        # the wide call above. Must NOT reuse the wide blob unmodified.
        narrow = await service.get_report(
            user_id=test_user.id,
            query=PortfolioReportQuery(
                broker_ids=[broker.id],
                include_summary=True,
                include_history=True,
                date_range={"start": str(day1), "end": str(day3)},
            ),
        )

        assert [p.date for p in narrow.history] == [day1, day2, day3]
        assert narrow.metadata.computed_date_to == day3
        assert narrow.summary.net_worth.amount == Decimal("1050")
        # Day-over-day delta (mirrors the frontend KPI calc: history[-1] - history[-2])
        # must reflect day3 vs day2 (real data), not two identical phantom future days.
        assert narrow.history[-1].nav_value.amount - narrow.history[-2].nav_value.amount == Decimal("50")
