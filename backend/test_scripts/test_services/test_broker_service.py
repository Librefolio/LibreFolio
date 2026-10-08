"""
Tests for BrokerService.

Tests CRUD operations, initial balance handling, flag validation, and deletion logic.
See checklist: 01_test_broker_transaction_subsystem.md - Category 4

Reference: backend/app/services/broker_service.py
"""

import sys
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetType,
    Broker,
    BrokerUserAccess,
    FxConversionRoute,
    FxRate,
    PriceHistory,
    Transaction,
    TransactionType,
    User,
    UserRole,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import (
    BRAssetHolding,
    BRCreateItem,
    BRDeleteItem,
    BRSummary,
    BRUpdateItem,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.broker_service import BrokerService
from backend.app.services.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_services._tx_test_helpers import create_bulk

# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """Get async engine."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """Create a fresh session for each test with rollback."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(session) -> User:
    """Create a test user for broker ownership."""
    user = User(
        username=f"testuser_{utcnow().timestamp()}",
        email=f"test_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
        is_superuser=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def test_asset(session) -> Asset:
    """Create a test asset."""
    asset = Asset(
        display_name=f"Test Stock {utcnow().timestamp()}",
        asset_type=AssetType.STOCK,
        currency="EUR",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(asset)
    await session.flush()
    return asset


# ============================================================================
# 4.1 CREATE_BULK - BASIC CREATION
# ============================================================================


class TestCreateBulkBasic:
    """Test basic broker creation."""

    @pytest.mark.asyncio
    async def test_create_single_broker(self, session, test_user):
        """BR-U-001: Create one broker."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Test Broker {utcnow().timestamp()}",
                description="Test broker for unit tests",
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

        assert response.success_count == 1
        assert response.results[0].success is True
        assert response.results[0].broker_id is not None
        assert not response.errors

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, session, test_user):
        """BR-U-002: Create broker with existing name fails."""
        service = BrokerService(session)

        name = f"Unique Broker {utcnow().timestamp()}"

        # Create first
        items1 = [BRCreateItem(name=name)]
        await service.create_bulk(items1, user_id=test_user.id)

        # Try to create duplicate
        items2 = [BRCreateItem(name=name)]
        response = await service.create_bulk(items2, user_id=test_user.id)

        assert response.results[0].success is False
        # Error message can be "already exists" or "already have a broker named"
        error_msg = response.results[0].error.lower()
        assert "already" in error_msg and ("exists" in error_msg or "have" in error_msg)

    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, session, test_user):
        """BR-U-003: Created broker has timestamps set."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Timestamp Broker {utcnow().timestamp()}")]

        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        broker = await session.get(Broker, broker_id)

        assert broker.created_at is not None
        assert broker.updated_at is not None


# ============================================================================
# 4.2 CREATE_BULK - INITIAL BALANCES
# ============================================================================


class TestCreateBulkInitialBalances:
    """Test initial balance handling during broker creation."""

    @pytest.mark.asyncio
    async def test_create_with_initial_balances(self, session, test_user):
        """BR-U-010: Create broker with initial balances creates DEPOSIT transactions."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Balance Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

        assert response.success_count == 1
        assert response.results[0].deposits_created == 1

        # Verify the transaction exists
        broker_id = response.results[0].broker_id
        stmt = select(Transaction).where(
            Transaction.broker_id == broker_id,
            Transaction.type == TransactionType.DEPOSIT,
        )
        result = await session.execute(stmt)
        tx = result.scalar_one_or_none()

        assert tx is not None
        assert tx.amount == Decimal("1000")
        assert tx.currency == "EUR"

    @pytest.mark.asyncio
    async def test_create_deposits_count(self, session, test_user):
        """BR-U-011: Create with 2 currencies creates 2 deposits."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Multi Currency Broker {utcnow().timestamp()}",
                initial_balances=[
                    Currency(code="EUR", amount=Decimal("5000")),
                    Currency(code="USD", amount=Decimal("3000")),
                ],
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

        assert response.results[0].deposits_created == 2

    @pytest.mark.asyncio
    async def test_create_balances_filtered(self, session, test_user):
        """BR-U-012: Zero and negative amounts in initial_balances are filtered."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Filtered Balance Broker {utcnow().timestamp()}",
                initial_balances=[
                    Currency(code="EUR", amount=Decimal("5000")),
                    Currency(code="USD", amount=Decimal("0")),  # Should be filtered
                    Currency(code="GBP", amount=Decimal("-100")),  # Should be filtered
                ],
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

        # Only EUR should create a deposit
        assert response.results[0].deposits_created == 1


# ============================================================================
# 4.3 GET_ALL / GET_BY_ID
# ============================================================================


class TestGetOperations:
    """Test read operations."""

    @pytest.mark.asyncio
    async def test_get_all(self, session, test_user):
        """BR-U-020: Get all brokers returns list."""
        service = BrokerService(session)

        # Create a broker
        items = [BRCreateItem(name=f"List Broker {utcnow().timestamp()}")]
        await service.create_bulk(items, user_id=test_user.id)

        result = await service.get_all(user_id=test_user.id)

        assert isinstance(result.items, list)
        assert len(result.items) >= 1

    @pytest.mark.asyncio
    async def test_get_all_ordered(self, session, test_user):
        """BR-U-021: Get all brokers returns ordered by name."""
        service = BrokerService(session)

        # Create brokers with specific names
        ts = utcnow().timestamp()
        items = [
            BRCreateItem(name=f"ZZZ Broker {ts}"),
            BRCreateItem(name=f"AAA Broker {ts}"),
        ]
        await service.create_bulk(items, user_id=test_user.id)

        result = await service.get_all(user_id=test_user.id)

        # Extract names and check they are sorted
        names = [b.name for b in result.items]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_get_all_as_user_id_all_returns_all_brokers(self, session, test_user):
        """BR-U-021A: Superuser-style all filter returns every broker."""
        service = BrokerService(session)
        other_user = User(
            username=f"alluser_{utcnow().timestamp()}",
            email=f"all_{utcnow().timestamp()}@test.com",
            hashed_password="fakehash",
            is_active=True,
            is_superuser=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other_user)
        await session.flush()

        await service.create_bulk([BRCreateItem(name=f"Own Broker {utcnow().timestamp()}")], user_id=test_user.id)
        await service.create_bulk([BRCreateItem(name=f"Other Broker {utcnow().timestamp()}")], user_id=other_user.id)

        result = await service.get_all(user_id=test_user.id, as_user_id="all")

        names = [broker.name for broker in result.items]
        assert any(name.startswith("Own Broker ") for name in names)
        assert any(name.startswith("Other Broker ") for name in names)
        assert result.inaccessible == []

    @pytest.mark.asyncio
    async def test_get_all_as_specific_user_with_inaccessible(self, session, test_user):
        """BR-U-021B: Specific impersonation returns visible + inaccessible brokers."""
        service = BrokerService(session)
        other_user = User(
            username=f"impuser_{utcnow().timestamp()}",
            email=f"imp_{utcnow().timestamp()}@test.com",
            hashed_password="fakehash",
            is_active=True,
            is_superuser=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other_user)
        await session.flush()

        own_response = await service.create_bulk([BRCreateItem(name=f"Hidden Broker {utcnow().timestamp()}")], user_id=test_user.id)
        shared_response = await service.create_bulk([BRCreateItem(name=f"Visible Broker {utcnow().timestamp()}")], user_id=test_user.id)
        shared_broker_id = shared_response.results[0].broker_id

        session.add(
            BrokerUserAccess(
                user_id=other_user.id,
                broker_id=shared_broker_id,
                role=UserRole.VIEWER,
                share_percentage=Decimal("0.25"),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        await session.flush()

        result = await service.get_all(
            user_id=test_user.id,
            as_user_id=other_user.id,
            include_inaccessible=True,
        )

        assert [broker.id for broker in result.items] == [shared_broker_id]
        assert result.items[0].user_role == UserRole.VIEWER.value
        assert result.items[0].user_share_percentage == Decimal("0.25")
        inaccessible_ids = [broker.id for broker in result.inaccessible]
        assert own_response.results[0].broker_id in inaccessible_ids
        assert shared_broker_id not in inaccessible_ids

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self, session, test_user):
        """BR-U-022: Get existing broker returns BRReadItem."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Get Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        result = await service.get_by_id(broker_id, user_id=test_user.id)

        assert result is not None
        assert result.id == broker_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session, test_user):
        """BR-U-023: Get non-existent ID returns None."""
        service = BrokerService(session)

        result = await service.get_by_id(999999, user_id=test_user.id)

        assert result is None


# ============================================================================
# 4.4 GET_SUMMARY
# ============================================================================


class TestGetSummary:
    """Test broker summary retrieval."""

    @pytest.mark.asyncio
    async def test_get_summary_basic(self, session, test_user):
        """BR-U-030: Get summary returns BRSummary."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Summary Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert summary is not None
        assert summary.id == broker_id

    @pytest.mark.asyncio
    async def test_get_summary_cash_balances(self, session, test_user):
        """BR-U-031: Summary includes cash balances after deposits."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Cash Summary Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert len(summary.cash_balances) == 1
        assert summary.cash_balances[0].code == "EUR"
        assert summary.cash_balances[0].amount == Decimal("1000")

    @pytest.mark.asyncio
    async def test_get_summary_holdings(self, session, test_user, test_asset):
        """BR-U-032: Summary includes holdings after BUYs."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with cash
        items = [
            BRCreateItem(
                name=f"Holdings Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Buy some assets
        buy_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            )
        ]
        await create_bulk(tx_service, buy_items)

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert len(summary.holdings) == 1
        assert summary.holdings[0].asset_id == test_asset.id
        assert summary.holdings[0].quantity == Decimal("10")

    @pytest.mark.asyncio
    async def test_get_summary_cost_basis(self, session, test_user, test_asset):
        """BR-U-033: Summary includes cost basis calculation."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        items = [
            BRCreateItem(
                name=f"Cost Basis Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Multiple buys
        buy_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            ),
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("20"),
                cash=Currency(code="EUR", amount=Decimal("-1200")),
            ),
        ]
        await create_bulk(tx_service, buy_items)

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert len(summary.holdings) == 1
        holding = summary.holdings[0]
        assert holding.quantity == Decimal("30")
        assert holding.total_cost.amount == Decimal("1700")  # 500 + 1200
        assert holding.average_cost_per_unit == Decimal("1700") / Decimal("30")

    @pytest.mark.asyncio
    async def test_get_summary_impersonated_user_with_price_metrics(self, session, test_user, test_asset):
        """BR-U-034: Summary includes pricing metrics and impersonated access role."""
        service = BrokerService(session)
        tx_service = TransactionService(session)
        other_user = User(
            username=f"summaryuser_{utcnow().timestamp()}",
            email=f"summary_{utcnow().timestamp()}@test.com",
            hashed_password="fakehash",
            is_active=True,
            is_superuser=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other_user)
        await session.flush()

        response = await service.create_bulk(
            [
                BRCreateItem(
                    name=f"Priced Summary Broker {utcnow().timestamp()}",
                    initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
                )
            ],
            user_id=test_user.id,
        )
        broker_id = response.results[0].broker_id

        session.add(
            BrokerUserAccess(
                user_id=other_user.id,
                broker_id=broker_id,
                role=UserRole.VIEWER,
                share_percentage=Decimal("0.40"),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        session.add(
            PriceHistory(
                asset_id=test_asset.id,
                date=date.today(),
                open=Decimal("100"),
                high=Decimal("130"),
                low=Decimal("90"),
                close=Decimal("120"),
                volume=Decimal("1"),
                currency="EUR",
                source_plugin_key="manual_test",
                fetched_at=utcnow(),
            )
        )
        await session.flush()

        await create_bulk(
            tx_service,
            [
                TXCreateItem(
                    broker_id=broker_id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date.today(),
                    quantity=Decimal("10"),
                    cash=Currency(code="EUR", amount=Decimal("-500")),
                )
            ],
        )

        summary = await service.get_summary(
            broker_id,
            user_id=test_user.id,
            as_user_id=other_user.id,
        )

        assert summary is not None
        assert summary.user_role == UserRole.VIEWER.value
        assert summary.user_share_percentage == Decimal("0.40")
        assert len(summary.holdings) == 1
        holding = summary.holdings[0]
        assert holding.current_price == Decimal("120")
        assert holding.current_value.amount == Decimal("1200")
        assert holding.unrealized_pnl.amount == Decimal("700")
        assert holding.unrealized_pnl_percent == Decimal("140.00")

    @pytest.mark.asyncio
    async def test_get_summary_not_found(self, session, test_user):
        """BR-U-035: Get summary for non-existent broker returns None."""
        service = BrokerService(session)

        summary = await service.get_summary(999999, user_id=test_user.id)

        assert summary is None


# ============================================================================
# 4.4b GET_SUMMARY — HOLDING COST = AVERAGE COST IN THE ASSET CURRENCY (#32)
# ============================================================================
#
# get_summary computes each holding's total_cost with financial_math.average_cost, in the asset
# currency: every purchase converted at its own date, every sale removing its share of the
# average cost, transfers and adjustments in at their cost_basis_override. When part of the cost
# cannot be known (no rate for a purchase, an acquisition without cost basis) total_cost,
# average_cost_per_unit and the unrealized P&L are None, and a missing pair is listed with the
# purchase dates that needed it.
#
# Rows are written straight into the session — no balance validation, these brokers hold no
# cash on purpose — and never committed: the session fixture rolls back. FX: the only rates
# written here are EUR/MUR, after proving nobody stores a MUR rate or route; the "missing rate"
# case uses PYG, proven absent the same way.


async def _assert_no_fx_data(session: AsyncSession, currency: str, other: str = "EUR") -> None:
    """Precondition: no rate and no route for {currency}/{other} exist, committed by anyone."""
    base, quote = sorted((currency, other))
    rates = (await session.execute(select(func.count()).select_from(FxRate).where(FxRate.base == base, FxRate.quote == quote))).scalar_one()
    routes = (await session.execute(select(func.count()).select_from(FxConversionRoute).where(or_(and_(FxConversionRoute.base == base, FxConversionRoute.quote == quote), and_(FxConversionRoute.base == quote, FxConversionRoute.quote == base))))).scalar_one()
    assert (rates, routes) == (0, 0), f"precondition broken: {base}/{quote} has {rates} rate(s) and {routes} route(s) — this case needs a pair nobody stores"


async def _owned_broker(session: AsyncSession, user: User, label: str) -> int:
    """A broker the user owns, created through the service (OWNER access, no cash)."""
    response = await BrokerService(session).create_bulk([BRCreateItem(name=f"{label} {uuid4().hex[:12]}")], user_id=user.id)
    assert response.success_count == 1, response.errors
    return response.results[0].broker_id


async def _own_asset(session: AsyncSession, currency: str) -> Asset:
    asset = Asset(display_name=f"Holding cost {currency} {uuid4().hex[:12]}", asset_type=AssetType.STOCK, currency=currency)
    session.add(asset)
    await session.flush()
    return asset


def _row(broker_id: int, asset: Asset, tx_type: TransactionType, day: date, quantity: str, amount: str = "0", currency: str | None = None, *, cbo: str | None = None) -> Transaction:
    return Transaction(
        broker_id=broker_id,
        asset_id=asset.id,
        type=tx_type,
        date=day,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=currency,
        cost_basis_override=None if cbo is None else Decimal(cbo),
        cost_basis_currency=None if cbo is None else asset.currency,
    )


async def _add(session: AsyncSession, *rows) -> None:
    session.add_all(rows)
    await session.flush()


def _price(asset: Asset, day: date, close: str) -> PriceHistory:
    return PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=asset.currency, source_plugin_key="holding_cost_test")


def _only_holding(summary: BRSummary | None, asset: Asset) -> BRAssetHolding:
    """The holding of ``asset``; the broker belongs to the test, so it is the only one."""
    assert summary is not None
    assert [holding.asset_id for holding in summary.holdings] == [asset.id]
    return summary.holdings[0]


def _cost_view(holding: BRAssetHolding) -> dict:
    return {
        "quantity": holding.quantity,
        "total_cost": holding.total_cost,
        "average_cost_per_unit": holding.average_cost_per_unit,
        "current_value": holding.current_value,
        "unrealized_pnl": holding.unrealized_pnl,
        "unrealized_pnl_percent": holding.unrealized_pnl_percent,
    }


class TestGetSummaryHoldingCost:
    """Holding cost through financial_math.average_cost, in the asset currency."""

    @pytest.mark.asyncio
    async def test_get_summary_holding_cost_is_the_average_cost_of_the_quantity_held(self, session, test_user):
        """BR-U-036: 10 @ 100 + 10 @ 200, 5 sold → 15 held at 150 = 2250 (the deleted sum of BUY amounts gave 3000)."""
        broker_id = await _owned_broker(session, test_user, "Holding cost sale")
        asset = await _own_asset(session, "EUR")
        await _add(
            session,
            _row(broker_id, asset, TransactionType.BUY, date(2019, 4, 1), "10", "-1000", "EUR"),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 4, 8), "10", "-2000", "EUR"),
            _row(broker_id, asset, TransactionType.SELL, date(2019, 4, 15), "-5", "1100", "EUR"),
            _price(asset, date(2019, 4, 16), "180"),
        )

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        assert _cost_view(_only_holding(summary, asset)) == {
            "quantity": Decimal("15"),
            "total_cost": Currency(code="EUR", amount=Decimal("2250")),
            "average_cost_per_unit": Decimal("150"),
            "current_value": Currency(code="EUR", amount=Decimal("2700")),
            "unrealized_pnl": Currency(code="EUR", amount=Decimal("450")),
            "unrealized_pnl_percent": Decimal("20.00"),
        }
        assert summary.missing_fx_pairs == []

    @pytest.mark.asyncio
    async def test_get_summary_converts_a_purchase_paid_in_another_currency_at_its_own_date(self, session, test_user):
        """BR-U-037: MUR asset; 10 bought for 100 EUR on 1 Feb (45 MUR that day, 40 the day before, 50 later) + 5 for 3000 MUR."""
        await _assert_no_fx_data(session, "MUR")
        broker_id = await _owned_broker(session, test_user, "Holding cost FX")
        asset = await _own_asset(session, "MUR")
        await _add(
            session,
            *(FxRate(date=day, base="EUR", quote="MUR", rate=Decimal(rate), source="TEST_HOLDING_COST") for day, rate in ((date(2019, 1, 31), "40"), (date(2019, 2, 1), "45"), (date(2019, 2, 5), "50"))),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 2, 1), "10", "-100", "EUR"),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 2, 4), "5", "-3000", "MUR"),
            _price(asset, date(2019, 2, 5), "520"),
        )

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        # 100 EUR × 45 = 4500 MUR, + 3000 MUR = 7500 MUR for 15 units.
        assert _cost_view(_only_holding(summary, asset)) == {
            "quantity": Decimal("15"),
            "total_cost": Currency(code="MUR", amount=Decimal("7500")),
            "average_cost_per_unit": Decimal("500"),
            "current_value": Currency(code="MUR", amount=Decimal("7800")),
            "unrealized_pnl": Currency(code="MUR", amount=Decimal("300")),
            "unrealized_pnl_percent": Decimal("4.00"),
        }
        assert summary.missing_fx_pairs == []

    @pytest.mark.asyncio
    async def test_get_summary_holding_cost_is_unknown_when_a_purchase_cannot_be_converted(self, session, test_user):
        """BR-U-038: EUR asset; 10 bought for 100 EUR + 10 for 50000 PYG (no PYG rate anywhere) → no cost, no P&L, PYG/EUR listed."""
        await _assert_no_fx_data(session, "PYG")
        broker_id = await _owned_broker(session, test_user, "Holding cost missing FX")
        asset = await _own_asset(session, "EUR")
        await _add(
            session,
            _row(broker_id, asset, TransactionType.BUY, date(2019, 6, 3), "10", "-100", "EUR"),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 6, 10), "10", "-50000", "PYG"),
            _price(asset, date(2019, 6, 11), "12"),
        )

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        assert _cost_view(_only_holding(summary, asset)) == {
            "quantity": Decimal("20"),
            "total_cost": None,
            "average_cost_per_unit": None,
            "current_value": Currency(code="EUR", amount=Decimal("240")),  # the valuation itself is complete
            "unrealized_pnl": None,
            "unrealized_pnl_percent": None,
        }
        assert summary.missing_fx_pairs == [WACMissingPairInfo(pair="PYG/EUR", dates=[date(2019, 6, 10)])]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("in_type", "cbo", "expected_cost"),
        [
            pytest.param(TransactionType.TRANSFER, None, None, id="transfer-in-without-cost-basis"),
            pytest.param(TransactionType.ADJUSTMENT, None, None, id="adjustment-in-without-cost-basis"),
            pytest.param(TransactionType.ADJUSTMENT, "130", ("1650", "110", "150", "9.09"), id="control-adjustment-in-with-cost-basis"),
        ],
    )
    async def test_get_summary_holding_cost_is_unknown_after_an_acquisition_without_cost_basis(self, session, test_user, in_type, cbo, expected_cost):
        """BR-U-039: 10 bought for 1000 EUR, then 5 in without a cost basis → no cost, no P&L; with 130 EUR each → 1650."""
        broker_id = await _owned_broker(session, test_user, "Holding cost unknown basis")
        asset = await _own_asset(session, "EUR")
        arrival = _row(broker_id, asset, in_type, date(2019, 7, 8), "5", cbo=cbo)
        await _add(
            session,
            _row(broker_id, asset, TransactionType.BUY, date(2019, 7, 1), "10", "-1000", "EUR"),
            arrival,
            _price(asset, date(2019, 7, 9), "120"),
        )
        if in_type == TransactionType.TRANSFER:
            # A real transfer: the 5 units leave another broker (not the user's), linked both ways.
            source = Broker(name=f"Holding cost source {uuid4().hex[:12]}")
            session.add(source)
            await session.flush()
            departure = _row(source.id, asset, TransactionType.TRANSFER, date(2019, 7, 8), "-5")
            await _add(session, _row(source.id, asset, TransactionType.BUY, date(2019, 7, 1), "5", "-500", "EUR"), departure)
            departure.related_transaction_id = arrival.id
            arrival.related_transaction_id = departure.id
            await session.flush()

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        expected_view = {"quantity": Decimal("15"), "current_value": Currency(code="EUR", amount=Decimal("1800"))}
        if expected_cost is None:
            expected_view |= {"total_cost": None, "average_cost_per_unit": None, "unrealized_pnl": None, "unrealized_pnl_percent": None}
        else:
            total, average, pnl, percent = expected_cost
            expected_view |= {
                "total_cost": Currency(code="EUR", amount=Decimal(total)),
                "average_cost_per_unit": Decimal(average),
                "unrealized_pnl": Currency(code="EUR", amount=Decimal(pnl)),
                "unrealized_pnl_percent": Decimal(percent),
            }
        assert _cost_view(_only_holding(summary, asset)) == expected_view
        assert summary.missing_fx_pairs == [], "an unknown cost basis is not a missing rate"


# ============================================================================
# 4.5 UPDATE_BULK - BASIC
# ============================================================================


class TestUpdateBulkBasic:
    """Test basic update functionality."""

    @pytest.mark.asyncio
    async def test_update_name(self, session, test_user):
        """BR-U-040: Update broker name."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Original Name {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        new_name = f"Updated Name {utcnow().timestamp()}"
        update_items = [BRUpdateItem(name=new_name)]

        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.name == new_name

    @pytest.mark.asyncio
    async def test_update_description(self, session, test_user):
        """BR-U-041: Update broker description."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Desc Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        update_items = [BRUpdateItem(description="Updated description")]

        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_portal_url(self, session, test_user):
        """BR-U-042: Update portal_url."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"URL Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        update_items = [BRUpdateItem(portal_url="https://updated.example.com")]

        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.portal_url == "https://updated.example.com"

    @pytest.mark.asyncio
    async def test_update_duplicate_name(self, session, test_user):
        """BR-U-043: Update to existing name fails."""
        service = BrokerService(session)

        ts = utcnow().timestamp()
        items = [
            BRCreateItem(name=f"Broker A {ts}"),
            BRCreateItem(name=f"Broker B {ts}"),
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_a_id = response.results[0].broker_id
        broker_b_name = f"Broker B {ts}"

        # Try to rename A to B's name
        update_items = [BRUpdateItem(name=broker_b_name)]
        update_response = await service.update_bulk(update_items, [broker_a_id], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert "already exists" in update_response.results[0].error

    @pytest.mark.asyncio
    async def test_update_not_found(self, session, test_user):
        """BR-U-044: Update non-existent ID fails."""
        service = BrokerService(session)

        update_items = [BRUpdateItem(description="Should fail")]
        update_response = await service.update_bulk(update_items, [999999], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert "not found" in update_response.results[0].error


# ============================================================================
# 4.6 UPDATE_BULK - FLAG VALIDATION
# ============================================================================


class TestUpdateBulkFlagValidation:
    """Test flag validation when disabling overdraft/shorting."""

    @pytest.mark.asyncio
    async def test_update_disable_overdraft_valid(self, session, test_user):
        """BR-U-050: Disable overdraft succeeds when no negative balance."""
        service = BrokerService(session)

        # Create broker with overdraft enabled
        items = [
            BRCreateItem(
                name=f"Overdraft Broker {utcnow().timestamp()}",
                allow_cash_overdraft=True,
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Disable overdraft - should succeed (balance is positive)
        update_items = [BRUpdateItem(allow_cash_overdraft=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_overdraft_invalid(self, session, test_user):
        """BR-U-051: Disable overdraft fails when negative balance exists."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with overdraft enabled
        items = [
            BRCreateItem(
                name=f"Negative Overdraft Broker {utcnow().timestamp()}",
                allow_cash_overdraft=True,
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Create a withdrawal without deposit (negative balance)
        tx_items = [
            TXCreateItem(
                broker_id=broker_id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            )
        ]
        await create_bulk(tx_service, tx_items)

        # Try to disable overdraft - should fail
        update_items = [BRUpdateItem(allow_cash_overdraft=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_shorting_valid(self, session, test_user, test_asset):
        """BR-U-052: Disable shorting succeeds when no negative holdings."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with shorting enabled
        items = [
            BRCreateItem(
                name=f"Shorting Broker {utcnow().timestamp()}",
                allow_asset_shorting=True,
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Buy some assets (positive holding)
        tx_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            )
        ]
        await create_bulk(tx_service, tx_items)

        # Disable shorting - should succeed
        update_items = [BRUpdateItem(allow_asset_shorting=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_shorting_invalid(self, session, test_user, test_asset):
        """BR-U-053: Disable shorting fails when negative holdings exist."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with shorting enabled
        items = [
            BRCreateItem(
                name=f"Shorted Broker {utcnow().timestamp()}",
                allow_asset_shorting=True,
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Sell without owning (short sale)
        tx_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.SELL,
                date=date.today(),
                quantity=Decimal("-10"),
                cash=Currency(code="EUR", amount=Decimal("500")),
            )
        ]
        await create_bulk(tx_service, tx_items)

        # Try to disable shorting - should fail
        update_items = [BRUpdateItem(allow_asset_shorting=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_enable_flags_no_validation(self, session, test_user):
        """BR-U-054: Enabling overdraft (False→True) doesn't trigger validation."""
        service = BrokerService(session)

        # Create broker with overdraft disabled
        items = [
            BRCreateItem(
                name=f"Enable Overdraft Broker {utcnow().timestamp()}",
                allow_cash_overdraft=False,
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Enable overdraft - should succeed without validation
        update_items = [BRUpdateItem(allow_cash_overdraft=True)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is False


# ============================================================================
# 4.7 DELETE_BULK - BASIC
# ============================================================================


class TestDeleteBulkBasic:
    """Test basic delete functionality."""

    @pytest.mark.asyncio
    async def test_delete_empty_broker(self, session, test_user):
        """BR-U-060: Delete broker with no transactions succeeds."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Empty Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        delete_items = [BRDeleteItem(id=broker_id)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.success_count == 1
        assert delete_response.total_deleted == 1

        # Expire session cache to force re-fetch from DB
        session.expire_all()

        # Verify deleted
        broker = await session.get(Broker, broker_id)
        assert broker is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, session, test_user):
        """BR-U-061: Delete non-existent ID fails."""
        service = BrokerService(session)

        delete_items = [BRDeleteItem(id=999999)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is False
        assert "not found" in delete_response.results[0].message


# ============================================================================
# 4.8 DELETE_BULK - FORCE BEHAVIOR
# ============================================================================


class TestDeleteBulkForceBehavior:
    """Test force delete behavior with transactions."""

    @pytest.mark.asyncio
    async def test_delete_with_tx_no_force(self, session, test_user):
        """BR-U-070: Delete broker with transactions without force fails."""
        service = BrokerService(session)

        # Create broker with initial balance (creates a transaction)
        items = [
            BRCreateItem(
                name=f"Has TX Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Try to delete without force
        delete_items = [BRDeleteItem(id=broker_id, force=False)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is False
        assert "transactions" in delete_response.results[0].message.lower()

    @pytest.mark.asyncio
    async def test_delete_with_tx_force(self, session, test_user):
        """BR-U-071: Delete broker with transactions with force succeeds."""
        service = BrokerService(session)

        # Create broker with initial balance
        items = [
            BRCreateItem(
                name=f"Force Delete Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Delete with force
        delete_items = [BRDeleteItem(id=broker_id, force=True)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is True
        assert delete_response.results[0].transactions_deleted == 1

    @pytest.mark.asyncio
    async def test_delete_force_cascade(self, session, test_user):
        """BR-U-072: Force delete actually removes transactions."""
        service = BrokerService(session)
        _tx_service = TransactionService(session)

        # Create broker with multiple transactions
        items = [
            BRCreateItem(
                name=f"Cascade Delete Broker {utcnow().timestamp()}",
                initial_balances=[
                    Currency(code="EUR", amount=Decimal("1000")),
                    Currency(code="USD", amount=Decimal("500")),
                ],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Verify transactions exist
        tx_count_before = await service._count_transactions(broker_id)
        assert tx_count_before == 2

        # Force delete
        delete_items = [BRDeleteItem(id=broker_id, force=True)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is True
        assert delete_response.results[0].transactions_deleted == 2

        # Verify transactions are gone
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        result = await session.execute(stmt)
        remaining = result.scalars().all()
        assert len(remaining) == 0
