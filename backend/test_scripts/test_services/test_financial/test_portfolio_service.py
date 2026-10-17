"""
Integration tests for PortfolioService.

Uses a real AsyncSession against the test database.
Tests WAC orchestration and history aggregation.

Reference: backend/app/services/portfolio_service.py
"""

import json
import re
import sys
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.financial_math.portfolio.models as portfolio_models_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, Broker, BrokerUserAccess, FxConversionRoute, FxRate, PriceHistory, ProviderInputType, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import BRAccessBulkItem
from backend.app.schemas.portfolio import (
    AssetPeriodContribution,
    DataQualityStatus,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    PortfolioReportQuery,
    StalePriceAsset,
)
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.valuation import compute_holding_value
from backend.app.services.platform.data_quality_thresholds import TRANSACTION_IMPLIED_GRACE_DAYS
from backend.app.services.portfolio_service import (
    PortfolioService,
    _portfolio_l2_cache,
)
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_services._range_bounds import lift_range_bound

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def range_bound_lifted():
    """R13-SEC7-1: the FX-in-transit, cache-identity and L2-key scenarios here live in 2032–2038, after tomorrow, so the
    range bound is lifted for the whole module, before any fixture builds data (see ``lift_range_bound``). Every other
    scenario is the same lifted or not: J-43's 2025 pair and the today-relative rows end by tomorrow, and the 2026–2027
    income/cost/deposit histories are read through the standalone getters, which do not apply the bound."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        lift_range_bound(monkeypatch)
        yield


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

    # Internal cash transfer between two owned brokers (lot 41). Moving one's own cash from
    # one broker to another changes where the value sits, not how much was earned: no broker
    # card may show the move as a gain or a loss.

    async def _owned_receiver_broker(self, session, user: User) -> Broker:
        """A second broker the user owns at 100%, beside ``broker_with_access``."""
        receiver = Broker(name=f"PfBroker_receiver_{uuid4().hex[:12]}")
        session.add(receiver)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=receiver.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1.0")))
        await session.flush()
        return receiver

    async def _deposit_and_transfer(self, session, sender: Broker, receiver: Broker, *, sent_on: date, received_on: date, deposited_on: date = date(2025, 1, 1)) -> None:
        """5000 EUR deposited at ``sender`` on ``deposited_on`` (2025-01-01 unless given), then
        1000 EUR moved to ``receiver`` as a linked CASH_TRANSFER pair: -1000 on ``sent_on``,
        +1000 on ``received_on``.

        Same construction as the linked pairs of test_transaction_service.py: both legs are
        flushed first to get their ids, then point at each other (the foreign key of
        ``related_transaction_id`` is deferred)."""
        session.add(Transaction(broker_id=sender.id, type=TransactionType.DEPOSIT, date=deposited_on, amount=Decimal("5000"), currency="EUR"))
        sent = Transaction(broker_id=sender.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=sent_on, quantity=Decimal("0"), amount=Decimal("-1000"), currency="EUR")
        received = Transaction(broker_id=receiver.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=received_on, quantity=Decimal("0"), amount=Decimal("1000"), currency="EUR")
        session.add_all([sent, received])
        await session.flush()
        sent.related_transaction_id = received.id
        received.related_transaction_id = sent.id
        await session.flush()

    @staticmethod
    def _card_problems(summary, when: str, expected: list[tuple[str, int, str, str, str]]) -> list[str]:
        """Every mismatch between ``summary.by_broker`` and the ``expected`` rows of
        (who, broker_id, net_worth, gain_loss, gain_loss_percent), so one red shows them all."""
        if summary.by_broker is None:
            return [f"{when}: by_broker is None"]
        cards = {card.broker_id: card for card in summary.by_broker}
        problems: list[str] = []
        for who, broker_id, *wanted in expected:
            card = cards.get(broker_id)
            if card is None:
                problems.append(f"{when} {who}: no broker card")
                continue
            actual = (card.net_worth.amount, card.gain_loss.amount, card.gain_loss_percent)
            for field, got, want in zip(("net_worth", "gain_loss", "gain_loss_percent"), actual, wanted, strict=True):
                if got != Decimal(want):
                    problems.append(f"{when} {who}: {field} expected {want}, got {got}")
        return problems

    @staticmethod
    def _card_cash_problems(summary, when: str, expected: list[tuple[str, int, str]]) -> list[str]:
        """Every mismatch between the cash of the cards in ``summary.by_broker``
        (``cash_total``) and the ``expected`` rows of (who, broker_id, cash_total)."""
        if summary.by_broker is None:
            return [f"{when}: by_broker is None"]
        cards = {card.broker_id: card for card in summary.by_broker}
        problems: list[str] = []
        for who, broker_id, want in expected:
            card = cards.get(broker_id)
            if card is None:
                problems.append(f"{when} {who}: no broker card")
            elif card.cash_total.amount != Decimal(want):
                problems.append(f"{when} {who}: cash_total expected {want}, got {card.cash_total.amount}")
        return problems

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_internal_cash_transfer_same_day_is_not_gain(self, session, test_user, broker_with_access):
        """Moving one's own cash between two owned brokers is neither a gain nor a loss.

        5000 EUR deposited at A; on 2025-01-10, 1000 EUR goes from A to B, both legs that day.
        Afterwards A's card shows 4000 and B's 1000, each with gain 0 and 0%: the invested
        capital moves with the cash. Before lot 41 the cards showed the move as P&L:
        A -1000, B +1000."""
        sender, _ = broker_with_access
        receiver = await self._owned_receiver_broker(session, test_user)
        await self._deposit_and_transfer(session, sender, receiver, sent_on=date(2025, 1, 10), received_on=date(2025, 1, 10))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2025, 1, 20))

        problems = self._card_problems(summary, "2025-01-20", [("A (sender)", sender.id, "4000", "0", "0"), ("B (receiver)", receiver.id, "1000", "0", "0")])
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_internal_cash_transfer_in_transit_stays_with_sender(self, session, test_user, broker_with_access):
        """Cash in transit between two owned brokers still belongs to the sender, and its
        arrival is not a gain.

        5000 EUR deposited at A; 1000 EUR leaves A on 2025-01-10 and reaches B on 2025-01-15.
        During the transit (2025-01-12) A's card keeps the whole 5000 with gain 0 and B's shows
        0 with gain 0; after the arrival (2025-01-20) A shows 4000 and B 1000, both with gain 0.
        Before lot 41 A showed 4000 with a loss of 1000 during the transit."""
        sender, _ = broker_with_access
        receiver = await self._owned_receiver_broker(session, test_user)
        await self._deposit_and_transfer(session, sender, receiver, sent_on=date(2025, 1, 10), received_on=date(2025, 1, 15))
        service = PortfolioService(session)

        in_transit = await service.get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2025, 1, 12))
        arrived = await service.get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2025, 1, 20))

        problems = self._card_problems(in_transit, "2025-01-12 (in transit)", [("A (sender)", sender.id, "5000", "0", "0"), ("B (receiver)", receiver.id, "0", "0", "0")])
        problems += self._card_problems(arrived, "2025-01-20 (arrived)", [("A (sender)", sender.id, "4000", "0", "0"), ("B (receiver)", receiver.id, "1000", "0", "0")])
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_internal_cash_transfer_foreign_currency_moves_capital_at_arrival_rate(self, session, test_user, broker_with_access):
        """An internal transfer of foreign cash moves the invested capital at the rate of the
        arrival day.

        Base EUR; 1 CNY is worth 0.8 EUR on 2038-01-01, 0.9 on 01-10, 0.95 on 01-14, 1.0 on
        01-15 and 1.2 on 01-20. 1000 CNY deposited at A on 01-01 (capital 1000 × 0.8 = 800);
        500 CNY leaves A on 01-10 and reaches B on 01-15. During the transit (01-14) A's card
        holds its 500 CNY of cash and the 500 in transit, both at 0.95: 950 with gain 150 on 800
        (0.1875); B's shows 0. On arrival the 500 CNY enter B at 1.0, so 500 of capital moves
        from A to B: on 01-20 each holds 500 CNY at 1.2 = 600, A with gain 300 on 300 (100%), B
        with gain 100 on 500 (20%). The FX gain on the moved money is split by where it sat: A's
        until the arrival (0.8 to 1.0), B's afterwards (1.0 to 1.2); the card gains add up to
        400 = 1000 CNY × 1.2 - 800. Before lot 41 A showed 475 with a loss of 325 on 01-14 (the
        in-transit value missing, the transfer invisible to the capital); on 01-20 A showed 600
        with a loss of 200 and B 600 with a gain of 600 (0%, no capital)."""
        sender, _ = broker_with_access
        receiver = await self._owned_receiver_broker(session, test_user)
        session.add_all(
            [
                FxRate(date=date(2038, 1, 1), base="CNY", quote="EUR", rate=Decimal("0.8"), source="TEST"),
                FxRate(date=date(2038, 1, 10), base="CNY", quote="EUR", rate=Decimal("0.9"), source="TEST"),
                FxRate(date=date(2038, 1, 14), base="CNY", quote="EUR", rate=Decimal("0.95"), source="TEST"),
                FxRate(date=date(2038, 1, 15), base="CNY", quote="EUR", rate=Decimal("1.0"), source="TEST"),
                FxRate(date=date(2038, 1, 20), base="CNY", quote="EUR", rate=Decimal("1.2"), source="TEST"),
            ]
        )
        session.add(Transaction(broker_id=sender.id, type=TransactionType.DEPOSIT, date=date(2038, 1, 1), amount=Decimal("1000"), currency="CNY"))
        sent = Transaction(broker_id=sender.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=date(2038, 1, 10), quantity=Decimal("0"), amount=Decimal("-500"), currency="CNY")
        received = Transaction(broker_id=receiver.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=date(2038, 1, 15), quantity=Decimal("0"), amount=Decimal("500"), currency="CNY")
        session.add_all([sent, received])
        await session.flush()
        sent.related_transaction_id = received.id
        received.related_transaction_id = sent.id
        await session.flush()
        service = PortfolioService(session)

        # Mid-transit check on 01-14, the last transit day, with its own rate: the engine fully re-values a day only when something happens on it (a transaction, a price, a transit boundary), not on a rate-only change (B4/F scope).
        in_transit = await service.get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2038, 1, 14))
        arrived = await service.get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2038, 1, 20))

        problems = self._card_problems(in_transit, "2038-01-14 (in transit)", [("A (sender)", sender.id, "950", "150", "0.1875"), ("B (receiver)", receiver.id, "0", "0", "0")])
        problems += self._card_problems(arrived, "2038-01-20 (arrived)", [("A (sender)", sender.id, "600", "300", "1"), ("B (receiver)", receiver.id, "600", "100", "0.2")])
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_foreign_cash_in_transit_headline_equals_sum_of_cards(self, session, test_user, broker_with_access):
        """The headline of the summary is the sum of its broker cards, also while foreign cash
        is in transit (T1c, lot 41 step F).

        Same scenario as the test above: base EUR; 1 CNY is worth 0.8 EUR on 2038-01-01, 0.9 on
        01-10, 0.95 on 01-14, 1.0 on 01-15 and 1.2 on 01-20; 1000 CNY deposited at A on 01-01
        (capital 800); 500 CNY leave A on 01-10 and reach B on 01-15. Cash is valued at the
        rate of the valuation day, at a broker or in transit alike. On 01-14 the headline is
        A's card: net worth 950 (500 CNY of cash at 0.95, 475, plus the 500 in transit, 475),
        gain 150, cash 475; B's card is all 0. On 01-20 the 1000 CNY are worth 1.2: net worth
        1200, gain 400, cash 1200, i.e. A's card 600 / 300 / 600 plus B's 600 / 100 / 600.

        Before F, the headline kept each cash movement at the rate of its own date while the
        cards revalued their cash at the valuation date: on 01-14 the headline showed cash 350
        (800 - 450), net worth 825 and P&L 25; on 01-20 cash 850 (350 + 500 at 1.0), net worth
        850 and P&L 50."""
        sender, _ = broker_with_access
        receiver = await self._owned_receiver_broker(session, test_user)
        session.add_all(
            [
                FxRate(date=date(2038, 1, 1), base="CNY", quote="EUR", rate=Decimal("0.8"), source="TEST"),
                FxRate(date=date(2038, 1, 10), base="CNY", quote="EUR", rate=Decimal("0.9"), source="TEST"),
                FxRate(date=date(2038, 1, 14), base="CNY", quote="EUR", rate=Decimal("0.95"), source="TEST"),
                FxRate(date=date(2038, 1, 15), base="CNY", quote="EUR", rate=Decimal("1.0"), source="TEST"),
                FxRate(date=date(2038, 1, 20), base="CNY", quote="EUR", rate=Decimal("1.2"), source="TEST"),
            ]
        )
        session.add(Transaction(broker_id=sender.id, type=TransactionType.DEPOSIT, date=date(2038, 1, 1), amount=Decimal("1000"), currency="CNY"))
        sent = Transaction(broker_id=sender.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=date(2038, 1, 10), quantity=Decimal("0"), amount=Decimal("-500"), currency="CNY")
        received = Transaction(broker_id=receiver.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=date(2038, 1, 15), quantity=Decimal("0"), amount=Decimal("500"), currency="CNY")
        session.add_all([sent, received])
        await session.flush()
        sent.related_transaction_id = received.id
        received.related_transaction_id = sent.id
        await session.flush()
        service = PortfolioService(session)

        in_transit = await service.get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2038, 1, 14))
        arrived = await service.get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2038, 1, 20))

        problems: list[str] = []
        # (when, summary, expected headline net_worth / total_gain_loss / cash_total)
        for when, summary, wanted in (("2038-01-14 (in transit)", in_transit, ("950", "150", "475")), ("2038-01-20 (arrived)", arrived, ("1200", "400", "1200"))):
            headline = (summary.net_worth.amount, summary.total_gain_loss.amount, summary.cash_total.amount)
            for field, got, want in zip(("net_worth", "total_gain_loss", "cash_total"), headline, wanted, strict=True):
                if got != Decimal(want):
                    problems.append(f"{when} headline: {field} expected {want}, got {got}")
            if summary.by_broker is not None:  # a missing breakdown is reported by _card_problems below
                card_sums = (sum((card.net_worth.amount for card in summary.by_broker), Decimal("0")), sum((card.gain_loss.amount for card in summary.by_broker), Decimal("0")), sum((card.cash_total.amount for card in summary.by_broker), Decimal("0")))
                for field, got, card_sum in zip(("net_worth", "total_gain_loss", "cash_total"), headline, card_sums, strict=True):
                    if got != card_sum:
                        problems.append(f"{when} headline: {field} {got} != sum of the cards {card_sum}")
        problems += self._card_problems(in_transit, "2038-01-14 (in transit)", [("A (sender)", sender.id, "950", "150", "0.1875"), ("B (receiver)", receiver.id, "0", "0", "0")])
        problems += self._card_cash_problems(in_transit, "2038-01-14 (in transit)", [("A (sender)", sender.id, "475"), ("B (receiver)", receiver.id, "0")])
        problems += self._card_problems(arrived, "2038-01-20 (arrived)", [("A (sender)", sender.id, "600", "300", "1"), ("B (receiver)", receiver.id, "600", "100", "0.2")])
        problems += self._card_cash_problems(arrived, "2038-01-20 (arrived)", [("A (sender)", sender.id, "600"), ("B (receiver)", receiver.id, "600")])
        assert not problems, "\n".join(problems)

    # The horizon of the card (lot 41). Called directly without ``date_to`` (get_report always
    # passes one, ``date_to or today``), the summary values the portfolio today: the engine
    # (capital, value in transit, headline) stops there, and every number the service reads
    # from the rows must stop there too, even when a row is dated after today. Dates are
    # relative to today so these tests never age; every row sits at least two days away from
    # it, so a midnight between the test and the service cannot move a row to the other side
    # of today.

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_internal_cash_transfer_arriving_after_today_stays_in_transit(self, session, test_user, broker_with_access):
        """Without ``date_to``, an internal cash transfer whose arrival is dated after today
        is still in transit today, on the cards as in the headline.

        5000 EUR deposited at A ten days ago; 1000 EUR leaves A two days ago and its arrival
        at B is dated three days from now. Today A's card holds 4000 of cash and the 1000 in
        transit: 5000 with gain 0 and 0%; B's holds 0 of cash: 0 with gain 0 and 0%. The two
        cards add up to the headline net worth, 5000. Before T2g the card cash read every row
        of the broker, the future arrival too, while capital, value in transit and headline
        stop at today: B showed 1000 of cash, a net worth of 1000 and a gain of 1000 (its
        capital had not moved yet), and the cards added up to 6000 against a headline of 5000."""
        sender, _ = broker_with_access
        receiver = await self._owned_receiver_broker(session, test_user)
        today = date.today()
        await self._deposit_and_transfer(session, sender, receiver, deposited_on=today - timedelta(days=10), sent_on=today - timedelta(days=2), received_on=today + timedelta(days=3))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR")

        when = f"{today} (no date_to, in transit)"
        problems = self._card_problems(summary, when, [("A (sender)", sender.id, "5000", "0", "0"), ("B (receiver)", receiver.id, "0", "0", "0")])
        problems += self._card_cash_problems(summary, when, [("A (sender)", sender.id, "4000"), ("B (receiver)", receiver.id, "0")])
        cards_net_worth = sum((card.net_worth.amount for card in summary.by_broker or [] if card.broker_id in (sender.id, receiver.id)), Decimal("0"))
        if cards_net_worth != summary.net_worth.amount:
            problems.append(f"{when}: the cards add up to {cards_net_worth}, the headline net_worth is {summary.net_worth.amount}")
        if summary.net_worth.amount != Decimal("5000"):
            problems.append(f"{when}: headline net_worth expected 5000, got {summary.net_worth.amount}")
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_future_dated_deposit_is_outside_today_valuation(self, session, test_user, broker_with_access):
        """Without ``date_to``, a deposit dated after today is in neither the card nor the
        period totals.

        5000 EUR deposited at A ten days ago, 700 EUR more with a date five days from now.
        Today A's card holds 5000 of cash: 5000 with gain 0 and 0%. The headline net worth is
        5000, and so is the total deposited: the period totals reconcile to that net worth,
        so they stop at the same day. Before T2g the card cash and the period totals read
        every row of the broker, the future deposit too, while capital and headline stop at
        today: the card showed 5700 with a gain of 700 (0.14) beside a headline of 5000, and
        the total deposited was 5700."""
        broker, _ = broker_with_access
        today = date.today()
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=today - timedelta(days=10), amount=Decimal("5000"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=today + timedelta(days=5), amount=Decimal("700"), currency="EUR"),
            ]
        )
        await session.flush()

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR")

        when = f"{today} (no date_to)"
        problems = self._card_problems(summary, when, [("A", broker.id, "5000", "0", "0")])
        problems += self._card_cash_problems(summary, when, [("A", broker.id, "5000")])
        if summary.net_worth.amount != Decimal("5000"):
            problems.append(f"{when}: headline net_worth expected 5000, got {summary.net_worth.amount}")
        total_deposited = summary.total_deposited.amount if summary.total_deposited is not None else None
        if total_deposited != Decimal("5000"):
            problems.append(f"{when}: total_deposited expected 5000, got {total_deposited}")
        assert not problems, "\n".join(problems)

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

    @pytest.mark.asyncio
    async def test_income_history_scales_by_owner_share_not_by_role(self, session, test_user):
        """G1c — get_income_history() must apply the SAME F2 rule as get_summary()/
        get_positions_contribution() (reuses this class's _make_broker_with_role,
        the existing multi-share fixture pattern, rather than inventing a new one):
        a 30%-OWNER broker's DIVIDEND is scaled by its share exactly once, while an
        EDITOR broker's INTEREST is shown in full despite share_percentage=0 (the
        schema-mandated value for non-owner roles must never be read as "0% of
        the data").
        """
        owner_broker = await self._make_broker_with_role(session, test_user, "OWNER", Decimal("0.3"))
        editor_broker = await self._make_broker_with_role(session, test_user, "EDITOR", Decimal("0"))
        session.add_all(
            [
                Transaction(broker_id=owner_broker.id, type=TransactionType.DIVIDEND, date=date(2025, 4, 10), amount=Decimal("100"), currency="EUR"),
                Transaction(broker_id=editor_broker.id, type=TransactionType.INTEREST, date=date(2025, 4, 10), amount=Decimal("40"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        history = await service.get_income_history(user_id=test_user.id, date_from=None, date_to=date(2025, 4, 30))

        assert [p.date for p in history.points] == [date(2025, 4, 10)], "both brokers' income lands on the same date -> one grouped point"
        point = history.points[0]
        assert point.dividend.amount == Decimal("30"), f"30%-owner dividend must be scaled to 30 (applied once, not skipped/doubled), got {point.dividend.amount}"
        assert point.interest.amount == Decimal("40"), f"EDITOR interest must be full despite share_percentage=0, got {point.interest.amount}"
        assert history.missing_fx_pairs == []


class TestPortfolioYieldOnCost:
    @pytest.mark.asyncio
    async def test_summary_wires_yoc_to_holding_independently_of_date_from(self, session, test_user, broker_with_access, test_asset):
        """YOC owns its trailing window: report date_from must not trim qualifying income."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date(2024, 1, 1),
                    quantity=Decimal("10"),
                    amount=Decimal("-100"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.DIVIDEND,
                    date=date(2025, 1, 15),
                    amount=Decimal("20"),
                    currency="EUR",
                ),
            ]
        )
        await session.flush()

        summary = await PortfolioService(session).get_summary(
            user_id=test_user.id,
            date_from=date(2025, 7, 1),
            date_to=date(2025, 12, 31),
        )

        holding = next(
            (item for item in summary.holdings if item.asset_id == test_asset.id and item.broker_id == broker.id),
            None,
        )
        assert holding is not None
        assert holding.yield_on_cost is not None
        assert "yield_on_cost" in holding.model_dump()
        assert holding.yield_on_cost.provenance.net_zero is False
        assert holding.yield_on_cost.status == "available"
        assert holding.yield_on_cost.value == Decimal("0.2")
        assert holding.yield_on_cost.reason is None
        assert holding.yield_on_cost.provenance.window_start == date(2025, 1, 1)
        assert holding.yield_on_cost.provenance.window_end == date(2025, 12, 31)
        assert holding.yield_on_cost.provenance.gross_income_transaction_count == 1
        assert holding.yield_on_cost.provenance.gross_income_per_unit is not None
        assert holding.yield_on_cost.provenance.gross_income_per_unit.amount == Decimal("2")


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


# =============================================================================
# TestPortfolioFxCacheIdentity — compute_portfolio_fx_cache_identity()
# =============================================================================


class TestPortfolioFxCacheIdentity:
    """compute_portfolio_fx_cache_identity() is the shared FX fingerprint for both
    portfolio cache layers (L1 blob in financial_math/portfolio/engine.py, L2 report in
    portfolio_service.py). Its dependency set is deliberately BOUNDED: only
    currencies actually present in a scope's transactions/held-asset
    currencies/price history, paired with the target currency. A global,
    unbounded fingerprint (e.g. hashing the whole fx_rates table) would bust
    every user's cache on any FX sync anywhere in the system; a fingerprint
    that ignores a real dependency would silently serve stale numbers for a
    whole TTL instead (see TestAccessFingerprintCacheBust above for that
    failure mode on the access side).

    All rows here use currency pairs nowhere else in this codebase (EUR/ZAR,
    EUR/THB, EUR/NOK) so "this identity doesn't already depend on unrelated
    committed data" is true by construction, not by cleanup — same reasoning
    as FX_CORE_BASE/FX_CORE_QUOTE in test_fx_core.py. Every row is created on
    the test's own rolled-back `session`, so nothing here needs cleanup.
    """

    FX_TARGET = "EUR"
    FX_SCOPE_CCY = "ZAR"  # currency actually present in the test's scope
    FX_IRRELEVANT_CCY = "THB"  # a pair the scope never touches
    FX_OUT_OF_SCOPE_CCY = "NOK"  # lives only on a broker outside scope_broker_ids
    FX_COST_BASIS_CCY = "KWD"  # enters the scope only through cost_basis_currency
    IDENTITY_DATE = date(2032, 6, 15)

    async def _scoped_broker(self, session, test_user, currency) -> Broker:
        """A broker in test_user's scope with one transaction in `currency`."""
        broker = Broker(name=f"PfFxIdentity_{currency}_{utcnow().timestamp()}")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=self.IDENTITY_DATE - timedelta(days=30),
                amount=Decimal("100"),
                currency=currency,
            )
        )
        await session.flush()
        return broker

    async def _cost_basis_only_broker(self, session, test_user) -> Broker:
        """Scope whose only non-target currency is an opening cost basis."""
        marker = uuid4().hex
        broker = Broker(name=f"PfFxIdentity_CostBasis_{marker}")
        asset = Asset(
            display_name=f"PfFxIdentityAsset_{marker}",
            ticker=f"PFCB{marker[:8]}",
            currency=self.FX_TARGET,
            type=AssetType.STOCK,
        )
        session.add_all([broker, asset])
        await session.flush()
        session.add_all(
            [
                BrokerUserAccess(
                    broker_id=broker.id,
                    user_id=test_user.id,
                    role=UserRole.OWNER,
                    share_percentage=Decimal("1"),
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=self.IDENTITY_DATE - timedelta(days=30),
                    quantity=Decimal("2"),
                    amount=Decimal("0"),
                    currency=None,
                    cost_basis_override=Decimal("25"),
                    cost_basis_currency=self.FX_COST_BASIS_CCY,
                ),
                PriceHistory(
                    asset_id=asset.id,
                    date=self.IDENTITY_DATE,
                    close=Decimal("100"),
                    currency=self.FX_TARGET,
                    source_plugin_key="manual_test",
                ),
            ]
        )
        await session.flush()
        return broker

    @pytest.mark.asyncio
    async def test_stable_identity_when_deps_unchanged(self, session, test_user):
        """Two calls, nothing written in between → identical identity (cache hit)."""
        broker = await self._scoped_broker(session, test_user, self.FX_SCOPE_CCY)
        id1 = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        id2 = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert id1 == id2
        assert id1 != "no_fx", "scope has a ZAR transaction against an EUR target — must be a real fingerprint, not the empty-deps sentinel"

    @pytest.mark.asyncio
    async def test_irrelevant_fx_pair_does_not_change_identity(self, session, test_user):
        """A rate+route for a pair the scope never touches (EUR/THB) must not move
        the EUR/ZAR-scoped identity — this is the bounded-query guarantee."""
        broker = await self._scoped_broker(session, test_user, self.FX_SCOPE_CCY)
        baseline = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)

        session.add(FxRate(date=self.IDENTITY_DATE, base=self.FX_TARGET, quote=self.FX_IRRELEVANT_CCY, rate=Decimal("35.0"), source="TEST"))
        session.add(
            FxConversionRoute(
                base=self.FX_TARGET,
                quote=self.FX_IRRELEVANT_CCY,
                priority=1,
                chain_steps=json.dumps([{"from": self.FX_TARGET, "to": self.FX_IRRELEVANT_CCY, "provider": "ECB"}]),
            )
        )
        await session.flush()

        after = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after == baseline, "an unrelated EUR/THB rate+route perturbed the EUR/ZAR-scoped identity"

    @pytest.mark.asyncio
    async def test_out_of_scope_broker_does_not_affect_identity(self, session, test_user):
        """A second broker+currency+rate that is NOT in scope_broker_ids must not
        leak into this scope's fingerprint — the query is bounded per scope, not
        per user or globally."""
        broker = await self._scoped_broker(session, test_user, self.FX_SCOPE_CCY)
        baseline = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)

        await self._scoped_broker(session, test_user, self.FX_OUT_OF_SCOPE_CCY)
        session.add(FxRate(date=self.IDENTITY_DATE, base=self.FX_TARGET, quote=self.FX_OUT_OF_SCOPE_CCY, rate=Decimal("11.0"), source="TEST"))
        await session.flush()

        after = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after == baseline, "an out-of-scope broker's currency/FX data leaked into this scope's identity"

    @pytest.mark.asyncio
    async def test_relevant_fx_rate_insert_and_update_change_identity(self, session, test_user):
        """A relevant EUR/ZAR rate insert moves the identity; editing its value
        moves it again — both are real dependency changes."""
        broker = await self._scoped_broker(session, test_user, self.FX_SCOPE_CCY)
        baseline = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)

        rate = FxRate(date=self.IDENTITY_DATE, base=self.FX_TARGET, quote=self.FX_SCOPE_CCY, rate=Decimal("20.50"), source="TEST")
        session.add(rate)
        await session.flush()
        after_insert = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_insert != baseline, "inserting the scope's own EUR/ZAR rate did not move the identity"

        rate.rate = Decimal("21.75")
        await session.flush()
        after_update = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_update != after_insert, "updating the scope's own EUR/ZAR rate value did not move the identity"

    @pytest.mark.asyncio
    async def test_relevant_fx_rate_deletion_and_replacement_change_identity(self, session, test_user):
        """Deleting and replacing the scope's only relevant rate must each move
        the identity."""
        broker = await self._scoped_broker(session, test_user, self.FX_SCOPE_CCY)
        rate = FxRate(date=self.IDENTITY_DATE, base=self.FX_TARGET, quote=self.FX_SCOPE_CCY, rate=Decimal("19.0"), source="TEST")
        session.add(rate)
        await session.flush()
        with_rate = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)

        await session.delete(rate)
        await session.flush()
        without_rate = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert without_rate != with_rate, "deleting the scope's only relevant rate did not move the identity"

        replacement = FxRate(date=self.IDENTITY_DATE, base=self.FX_TARGET, quote=self.FX_SCOPE_CCY, rate=Decimal("22.0"), source="REPLACEMENT")
        session.add(replacement)
        await session.flush()
        with_replacement = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert with_replacement != without_rate, "replacing the scope's relevant rate did not move the identity"
        assert with_replacement != with_rate, "replacement data produced the deleted rate's identity"

    @pytest.mark.asyncio
    async def test_relevant_route_change_changes_identity(self, session, test_user):
        """A conversion-route insert (provider/chain config) and a subsequent
        priority edit are both relevant config changes and must each move the
        identity — a stale route could route the same pair through a different,
        no-longer-configured provider chain without the cache noticing."""
        broker = await self._scoped_broker(session, test_user, self.FX_SCOPE_CCY)
        baseline = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)

        route = FxConversionRoute(
            base=self.FX_TARGET,
            quote=self.FX_SCOPE_CCY,
            priority=1,
            chain_steps=json.dumps([{"from": self.FX_TARGET, "to": self.FX_SCOPE_CCY, "provider": "ECB"}]),
        )
        session.add(route)
        await session.flush()
        after_route = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_route != baseline, "adding a route for the scope's own pair did not move the identity"

        route.priority = 2
        await session.flush()
        after_priority = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_priority != after_route, "editing the route's priority did not move the identity"

        route.chain_steps = json.dumps([{"from": self.FX_TARGET, "to": self.FX_SCOPE_CCY, "provider": "MOCKFX"}])
        await session.flush()
        after_provider = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_provider != after_priority, "editing the route's provider chain did not move the identity"

    @pytest.mark.asyncio
    async def test_cost_basis_currency_fx_cache_identity_tracks_rate_and_route(self, session, test_user):
        """A third currency used only by cost_basis_currency is an FX dependency."""
        broker = await self._cost_basis_only_broker(session, test_user)
        baseline = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert baseline != "no_fx", "cost_basis_currency was ignored when cash, asset, and price currencies all matched the target"

        rate = FxRate(
            date=self.IDENTITY_DATE,
            base=self.FX_TARGET,
            quote=self.FX_COST_BASIS_CCY,
            rate=Decimal("0.25"),
            source="TEST",
        )
        session.add(rate)
        await session.flush()
        after_rate = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_rate != baseline, "a rate used only by cost_basis_currency did not move the FX identity"

        route = FxConversionRoute(
            base=self.FX_TARGET,
            quote=self.FX_COST_BASIS_CCY,
            priority=1,
            chain_steps=json.dumps([{"from": self.FX_COST_BASIS_CCY, "to": self.FX_TARGET, "provider": "ECB"}]),
        )
        session.add(route)
        await session.flush()
        after_route = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_route != after_rate, "a route used only by cost_basis_currency did not move the FX identity"

        route.chain_steps = json.dumps([{"from": self.FX_COST_BASIS_CCY, "to": self.FX_TARGET, "provider": "MOCKFX"}])
        await session.flush()
        after_provider = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert after_provider != after_route, "changing the cost-basis route provider did not move the FX identity"

    @pytest.mark.asyncio
    async def test_future_dated_rate_beyond_date_to_excluded(self, session, test_user):
        """date_to bounds the FX dependency window: a rate dated after date_to is
        not yet usable for this valuation and must not appear in the identity —
        but the same rate DOES move the identity once date_to reaches it (sanity
        check that the function is sensitive at all, not just conveniently blind)."""
        broker = await self._scoped_broker(session, test_user, self.FX_SCOPE_CCY)
        baseline = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)

        session.add(FxRate(date=self.IDENTITY_DATE + timedelta(days=1), base=self.FX_TARGET, quote=self.FX_SCOPE_CCY, rate=Decimal("99.0"), source="TEST"))
        await session.flush()

        still_baseline = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE)
        assert still_baseline == baseline, "a rate dated after date_to leaked into the identity"

        widened = await portfolio_engine_module.compute_portfolio_fx_cache_identity(session, {broker.id}, self.FX_TARGET, self.IDENTITY_DATE + timedelta(days=1))
        assert widened != baseline, "widening date_to to include the future-dated rate did not move the identity"


# =============================================================================
# TestPortfolioBlobCacheFxSensitivity — L1 blob cache key integration
# =============================================================================


class TestPortfolioBlobCacheFxSensitivity:
    """The L1 blob cache key (PortfolioCalculationEngine.calculate) now includes
    compute_portfolio_fx_cache_identity(). This exercises the integration end to
    end: identical scope/date → cache hit (DailyStateBuilder.build not called
    again); an irrelevant FX pair → still a cache hit; a relevant FX rate insert
    → cache miss (recompute)."""

    @pytest.mark.asyncio
    async def test_blob_cache_hit_stable_then_miss_on_relevant_fx_change(self, session, test_user, monkeypatch):
        broker = Broker(name=f"PfFxBlob_{utcnow().timestamp()}")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date(2033, 1, 1),
                amount=Decimal("500"),
                currency="ZAR",
            )
        )
        await session.flush()
        portfolio_engine_module._portfolio_blob_cache.clear()

        build_calls = {"n": 0}
        original_build = DailyStateBuilder.build

        def counting_build(builder_self):
            build_calls["n"] += 1
            return original_build(builder_self)

        monkeypatch.setattr(DailyStateBuilder, "build", counting_build)

        engine = portfolio_engine_module.PortfolioCalculationEngine(session)
        date_to = date(2033, 1, 10)

        await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR")
        assert build_calls["n"] == 1

        # Unchanged deps → cache hit, no recompute.
        await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR")
        assert build_calls["n"] == 1, "identical scope/date recomputed instead of hitting the L1 blob cache"

        # Irrelevant FX pair (EUR/THB — this scope only has ZAR) → still a cache hit.
        session.add(FxRate(date=date_to, base="EUR", quote="THB", rate=Decimal("35.0"), source="TEST"))
        await session.flush()
        await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR")
        assert build_calls["n"] == 1, "an unrelated EUR/THB rate busted the L1 blob cache"

        # Relevant FX rate (EUR/ZAR) → must bust the cache.
        session.add(FxRate(date=date_to, base="EUR", quote="ZAR", rate=Decimal("20.5"), source="TEST"))
        await session.flush()
        await engine.calculate(test_user.id, broker_ids=[broker.id], date_to=date_to, target_currency="EUR")
        assert build_calls["n"] == 2, "a relevant EUR/ZAR rate insert did not bust the L1 blob cache"

    @pytest.mark.asyncio
    async def test_cost_basis_currency_fx_cache_change_busts_l1_blob(self, session, test_user, monkeypatch, request):
        identity_fixture = TestPortfolioFxCacheIdentity()
        broker = await identity_fixture._cost_basis_only_broker(session, test_user)
        portfolio_engine_module._portfolio_blob_cache.clear()
        request.addfinalizer(portfolio_engine_module._portfolio_blob_cache.clear)

        build_calls = {"n": 0}
        original_build = DailyStateBuilder.build

        def counting_build(builder_self):
            build_calls["n"] += 1
            return original_build(builder_self)

        monkeypatch.setattr(DailyStateBuilder, "build", counting_build)

        engine = portfolio_engine_module.PortfolioCalculationEngine(session)

        async def calculate():
            return await engine.calculate(
                test_user.id,
                broker_ids=[broker.id],
                date_to=identity_fixture.IDENTITY_DATE,
                target_currency=identity_fixture.FX_TARGET,
            )

        await calculate()
        await calculate()
        assert build_calls["n"] == 1, "unchanged cost-basis FX dependencies missed the L1 blob cache"

        session.add(
            FxRate(
                date=identity_fixture.IDENTITY_DATE,
                base=identity_fixture.FX_TARGET,
                quote=identity_fixture.FX_COST_BASIS_CCY,
                rate=Decimal("0.25"),
                source="TEST",
            )
        )
        await session.flush()
        await calculate()
        assert build_calls["n"] == 2, "a rate used only by cost_basis_currency did not bust the L1 blob cache"

        session.add(
            FxConversionRoute(
                base=identity_fixture.FX_TARGET,
                quote=identity_fixture.FX_COST_BASIS_CCY,
                priority=1,
                chain_steps=json.dumps(
                    [
                        {
                            "from": identity_fixture.FX_COST_BASIS_CCY,
                            "to": identity_fixture.FX_TARGET,
                            "provider": "MOCKFX",
                        }
                    ]
                ),
            )
        )
        await session.flush()
        await calculate()
        assert build_calls["n"] == 3, "a route used only by cost_basis_currency did not bust the L1 blob cache"


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
# TestTransactionImpliedGraceFromLastQuote — V-11 (decision 30, D-J15)
# =============================================================================


class TestTransactionImpliedGraceFromLastQuote:
    """V-11: the 14-day grace of TRANSACTION_IMPLIED («valued at cost») counts from the last market quote.

    Developer decision 30 (D-J15, 15/10), «si mi pare ottima!», on the proposal: the two weeks of
    ``TRANSACTION_IMPLIED_GRACE_DAYS`` count from the asset's LAST MARKET QUOTE on or before the
    valuation date; an asset that was never quoted counts from its first BUY/SELL, as today.

    Why the anchor moves: ``AssetPriceSeries.resolve`` (``financial_math/price_marks.py``) lets a
    trade of the day beat yesterday's quote, so an asset quoted every day and bought again on the
    valuation date is valued at that trade's price, transaction-implied, on that day. Today the
    grace counts from the first BUY/SELL (``PortfolioService.get_summary``, section «6. Data quality
    report»), so that asset is reported without a market price as soon as its first purchase is
    more than 14 days old.

    R1 and R2 are red until the fix, R2 as a declared change; G1, G2 and G3 are guards, green
    before and after it. Each test owns its user, broker, asset and quotes (flushed, then rolled
    back by ``session``). The valuation date ``V`` is fixed: the grace is measured from
    ``date_to``, not from the calendar. Before its verdict each case proves that on ``V`` the asset
    is valued at a trade price (the engine's transaction-implied state), through its holding row,
    and where its last market quote is: through the holding row of an earlier day when the asset
    was already held (R1, G1), otherwise from the quotes the test seeded (R2, G2, G3). So the
    verdict can only come from the grace. The list is read by asset id, from the
    TRANSACTION_IMPLIED issue.
    """

    V = date(2025, 6, 30)

    def _day(self, days_before_v: int) -> date:
        return self.V - timedelta(days=days_before_v)

    async def _seed_buy(self, session, broker: Broker, asset: Asset, *, days_before_v: int, quantity: str, unit_price: str) -> None:
        """Fund ``broker`` and BUY ``quantity`` units of ``asset`` at ``unit_price`` EUR, on V − ``days_before_v``."""
        day = self._day(days_before_v)
        cost = Decimal(quantity) * Decimal(unit_price)
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=day, amount=cost, currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=day, quantity=Decimal(quantity), amount=-cost, currency="EUR"),
            ]
        )
        await session.flush()

    async def _seed_quotes(self, session, asset: Asset, *, oldest: int, newest: int) -> None:
        """One EUR market quote (close 100) per day, from V − ``oldest`` to V − ``newest``, both included."""
        for days_before_v in range(newest, oldest + 1):
            session.add(PriceHistory(asset_id=asset.id, date=self._day(days_before_v), open=Decimal("100"), high=Decimal("100"), low=Decimal("100"), close=Decimal("100"), volume=Decimal("1"), currency="EUR", source_plugin_key="manual_test"))
        await session.flush()

    async def _summary(self, session, user: User, date_to: date | None = None):
        return await PortfolioService(session).get_summary(user_id=user.id, date_to=date_to or self.V)

    @staticmethod
    def _listed_ids(summary) -> set[int]:
        """The summary's transaction-implied list: the asset ids of its TRANSACTION_IMPLIED issue (none without the issue)."""
        issue = next((issue for issue in summary.data_quality.issues if issue.code == IssueCode.TRANSACTION_IMPLIED), None)
        return set(issue.affected_asset_ids) if issue is not None else set()

    @staticmethod
    def _valuation(summary, asset_id: int) -> tuple[str | None, date | None]:
        """(valuation source, reference date) of the asset's one open holding."""
        rows = [holding for holding in summary.holdings if holding.asset_id == asset_id]
        assert len(rows) == 1, f"expected exactly one open holding of asset {asset_id}, got {rows}"
        return rows[0].valuation_source, rows[0].valuation_reference_date

    @staticmethod
    async def _assert_never_quoted(session, asset: Asset) -> None:
        quotes = (await session.execute(select(PriceHistory.id).where(PriceHistory.asset_id == asset.id))).all()
        assert quotes == [], f"precondition: asset {asset.id} must have no market quote, found {len(quotes)}"

    async def _last_quote_date(self, session, asset: Asset) -> date | None:
        """Date of the asset's last market quote on or before ``V``, from the quotes in the session (None without any)."""
        days = (await session.execute(select(PriceHistory.date).where(PriceHistory.asset_id == asset.id, PriceHistory.date <= self.V))).scalars().all()
        return max(days, default=None)

    @pytest.mark.asyncio
    async def test_r1_quoted_until_the_day_before_and_bought_again_is_not_listed(self, session, test_user, broker_with_access, test_asset_with_provider):
        """R1 — red until V-11. First BUY on V−30, a market quote every day up to V−1, another BUY on V.

        On V the trade of the day beats the quote of V−1, so the asset is valued at cost on V. Today
        the grace counts from the first BUY: 30 days > 14, listed. After the fix it counts from the
        last quote, V−1: 1 day <= 14, not listed.
        """
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_buy(session, broker, asset, days_before_v=30, quantity="10", unit_price="100")
        await self._seed_quotes(session, asset, oldest=30, newest=1)
        await self._seed_buy(session, broker, asset, days_before_v=0, quantity="5", unit_price="102")

        day_before = await self._summary(session, test_user, date_to=self._day(1))
        summary = await self._summary(session, test_user)

        assert self._valuation(day_before, asset.id) == ("MARKET_PRICE", self._day(1)), "barrier: on V−1 the asset is valued at its quote of that day"
        assert self._valuation(summary, asset.id) == ("LAST_TRADE_PRICE", self.V), "barrier: on V the trade of the day makes the asset transaction-implied"
        assert asset.id not in self._listed_ids(summary), f"asset {asset.id} is listed as valued at cost on {self.V}, but its last market quote is from {self._day(1)}: the 14-day grace counts from the last quote (decision 30)"

    @pytest.mark.asyncio
    async def test_r2_feed_stopped_before_the_first_buy_is_listed_at_once(self, session, test_user, broker_with_access, test_asset_with_provider):
        """R2 — red until V-11, a DECLARED CHANGE. The asset has market quotes, the last one on V−100,
        before its first BUY on V−5; on V it is valued at that trade's price, its most recent
        observation.

        Today the grace counts from the first BUY: 5 days <= 14, not listed. After the fix it counts
        from the last quote, V−100: 100 days > 14, listed. This is the declared corner of the rule
        (D-J15: «la grazia parte dall'ultima quotazione di mercato; senza quotazioni dal primo
        BUY/SELL, come oggi»): an asset that has quotes is measured from its last quote, never from
        its purchases. The declared change: a stopped feed is reported at once, instead of only 14
        days after the asset's first purchase.

        The asset is held only from V−5, so no holding row can show its last quote: that one is read
        from the quotes the test seeded.
        """
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_quotes(session, asset, oldest=110, newest=100)
        await self._seed_buy(session, broker, asset, days_before_v=5, quantity="10", unit_price="100")
        assert await self._last_quote_date(session, asset) == self._day(100), "precondition: the asset's last market quote on or before V is the one of V−100"

        summary = await self._summary(session, test_user)

        assert self._valuation(summary, asset.id) == ("LAST_TRADE_PRICE", self._day(5)), "barrier: on V the trade of V−5, more recent than the last quote, makes the asset transaction-implied"
        assert asset.id in self._listed_ids(summary), f"asset {asset.id} is not listed as valued at cost on {self.V}, but its last market quote is from {self._day(100)}, 100 days before: the 14-day grace counts from the last quote, not from the first BUY of {self._day(5)} (decision 30)"

    @pytest.mark.asyncio
    async def test_g1_last_quote_twenty_days_before_is_listed(self, session, test_user, broker_with_access, test_asset_with_provider):
        """G1 — guard, listed before and after V-11. R1's history, but the quotes stop on V−20.

        Before: 30 days from the first BUY > 14. After: 20 days from the last quote > 14.
        """
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_buy(session, broker, asset, days_before_v=30, quantity="10", unit_price="100")
        await self._seed_quotes(session, asset, oldest=30, newest=20)
        await self._seed_buy(session, broker, asset, days_before_v=0, quantity="5", unit_price="102")

        day_before = await self._summary(session, test_user, date_to=self._day(1))
        summary = await self._summary(session, test_user)

        assert self._valuation(day_before, asset.id) == ("MARKET_PRICE", self._day(20)), "barrier: on V−1 the last market quote is the one of V−20"
        assert self._valuation(summary, asset.id) == ("LAST_TRADE_PRICE", self.V), "barrier: on V the trade of the day makes the asset transaction-implied"
        assert asset.id in self._listed_ids(summary), f"asset {asset.id} is not listed as valued at cost on {self.V}, but its last market quote is from {self._day(20)}, 20 days before"

    @pytest.mark.asyncio
    async def test_g2_never_quoted_and_bought_ten_days_before_is_not_listed(self, session, test_user, broker_with_access, test_asset_with_provider):
        """G2 — guard, not listed before and after V-11. Never quoted: the grace counts from the
        first BUY, on V−10, so 10 days <= 14."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_buy(session, broker, asset, days_before_v=10, quantity="10", unit_price="100")
        await self._assert_never_quoted(session, asset)

        summary = await self._summary(session, test_user)

        assert self._valuation(summary, asset.id) == ("LAST_TRADE_PRICE", self._day(10)), "barrier: on V the asset is valued at the price of its only trade"
        assert asset.id not in self._listed_ids(summary), f"asset {asset.id}, never quoted and first bought on {self._day(10)}, is listed as valued at cost within the 14-day grace"

    @pytest.mark.asyncio
    async def test_g3_never_quoted_and_bought_twenty_days_before_is_listed(self, session, test_user, broker_with_access, test_asset_with_provider):
        """G3 — guard, listed before and after V-11. Never quoted: the grace counts from the first
        BUY, on V−20, so 20 days > 14."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_buy(session, broker, asset, days_before_v=20, quantity="10", unit_price="100")
        await self._assert_never_quoted(session, asset)

        summary = await self._summary(session, test_user)

        assert self._valuation(summary, asset.id) == ("LAST_TRADE_PRICE", self._day(20)), "barrier: on V the asset is valued at the price of its only trade"
        assert asset.id in self._listed_ids(summary), f"asset {asset.id}, never quoted and first bought on {self._day(20)}, is not listed as valued at cost past the 14-day grace"


# =============================================================================
# J-17 — a holding with no price observation is valued at its book cost
# =============================================================================


class TestValuedAtCostHoldings:
    """J-17 (developer's P2 and option A, 16/10): an ADJUSTMENT is never a price, and a holding with
    no observation at all (no quote, BUY or SELL on or before the day) is valued at its book cost,
    as a declared estimate: ``valuation_source`` ESTIMATED_AT_COST, ``current_value`` = the historical
    cost in the report currency (each acquisition at its own date's rate), ``current_price`` None,
    ``gain_loss`` 0, not a missing price.

    FX rows: EUR/LKR, a pair no other test stores (checked as a precondition, never committed: the
    ``session`` fixture rolls back). Stored EUR/LKR means 1 EUR = rate LKR, so LKR→EUR divides.
    """

    ADJ_DAY = date(2019, 3, 1)
    REPORT_DAY = date(2019, 6, 28)

    @pytest.mark.asyncio
    async def test_foreign_adjustment_only_holding_is_valued_at_its_historical_cost(self, session, test_user, broker_with_access):
        """An LKR asset received by an ADJUSTMENT-in of 10 units at 3000 LKR on 2019-03-01, when 1 EUR
        was 150 LKR: its cost is 30000 / 150 = 200 EUR. On 2019-06-28 (1 EUR = 120 LKR) it is still
        worth its 200 EUR cost: ESTIMATED_AT_COST, no price, gain 0, no missing pair.

        Before J-17: LAST_TRADE_PRICE at the adjustment's 3000 LKR converted at the report day's rate —
        current price 25 EUR, current value 250, gain 50 (an exchange-rate "gain" on an asset that was
        never priced).
        """
        broker, _ = broker_with_access
        stored = (await session.execute(select(FxRate.id).where(FxRate.base == "EUR", FxRate.quote == "LKR"))).all()
        assert stored == [], f"precondition broken: {len(stored)} EUR/LKR rate(s) stored by someone else — this case needs a pair nobody stores"
        asset = Asset(display_name=f"AtCost LKR {uuid4().hex[:12]}", currency="LKR", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        session.add_all(
            [
                FxRate(date=self.ADJ_DAY, base="EUR", quote="LKR", rate=Decimal("150"), source="TEST_J17"),
                FxRate(date=self.REPORT_DAY, base="EUR", quote="LKR", rate=Decimal("120"), source="TEST_J17"),
                Transaction(
                    broker_id=broker.id,
                    asset_id=asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=self.ADJ_DAY,
                    quantity=Decimal("10"),
                    amount=Decimal("0"),
                    currency=None,
                    cost_basis_override=Decimal("3000"),
                    cost_basis_currency="LKR",
                ),
            ]
        )
        await session.flush()

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, target_currency_override="EUR", date_to=self.REPORT_DAY)

        rows = [holding for holding in summary.holdings if holding.asset_id == asset.id]
        assert len(rows) == 1, f"expected one holding of asset {asset.id}, got {rows}"
        holding = rows[0]
        observed = {
            "valuation_source": holding.valuation_source,
            "current_value": holding.current_value,
            "current_price": holding.current_price,
            "gain_loss": holding.gain_loss,
            "valuation_effective_unit_price": holding.valuation_effective_unit_price,
            "valuation_reference_date": holding.valuation_reference_date,
            "missing_fx_pair": holding.missing_fx_pair,
        }
        assert observed == {
            "valuation_source": "ESTIMATED_AT_COST",
            "current_value": Decimal("200"),
            "current_price": None,
            "gain_loss": Decimal("0"),
            "valuation_effective_unit_price": None,
            "valuation_reference_date": None,
            "missing_fx_pair": None,
        }
        assert summary.net_worth.amount == Decimal("200")
        assert asset.id not in {item.asset_id for item in summary.missing_price_assets}


class TestValuedAtCostDataQuality:
    """J-17: the data-quality report lists the holdings valued at cost on the report's last day under
    a new warning, ``VALUED_AT_COST`` (``dataQuality.valuedAtCost``, params ``count`` and
    ``as_of_date``, group ``valued_at_cost``, CTA ``navigate_asset`` like TRANSACTION_IMPLIED).

    Same grace as TRANSACTION_IMPLIED (``TRANSACTION_IMPLIED_GRACE_DAYS``), counted from the asset's
    first acquisition — here its only one, an ADJUSTMENT: an asset at cost has no BUY or SELL, so the
    BUY/SELL first position date cannot anchor it. Same rule for manual assets: an asset without a
    provider assignment is not listed (its cost is its intended value); an asset with one is listed
    once the grace has passed. A holding at cost is in neither TRANSACTION_IMPLIED nor MISSING_PRICE.

    Each test owns its user, broker and asset (flushed, rolled back by ``session``), and proves through
    the holding row that on ``V`` the asset is valued at cost before reading any verdict, so an absent
    listing can only come from the rule. ``V`` is fixed: the grace is measured from ``date_to``.
    """

    V = date(2025, 6, 30)

    def _day(self, days_before_v: int) -> date:
        return self.V - timedelta(days=days_before_v)

    async def _seed_adjustment(self, session, broker: Broker, asset: Asset, *, days_before_v: int) -> None:
        """ADJUSTMENT-in of 10 units of ``asset`` at 20 EUR on V − ``days_before_v``: no cash, no quote, no BUY/SELL."""
        session.add(
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.ADJUSTMENT,
                date=self._day(days_before_v),
                quantity=Decimal("10"),
                amount=Decimal("0"),
                currency="EUR",
                cost_basis_override=Decimal("20"),
                cost_basis_currency="EUR",
            )
        )
        await session.flush()

    async def _summary(self, session, user: User):
        return await PortfolioService(session).get_summary(user_id=user.id, date_to=self.V)

    @staticmethod
    def _listed_ids(summary, code: str) -> set[int]:
        issue = next((issue for issue in summary.data_quality.issues if issue.code == code), None)
        return set(issue.affected_asset_ids) if issue is not None else set()

    @staticmethod
    def _assert_at_cost_on_v(summary, asset_id: int) -> None:
        rows = [holding for holding in summary.holdings if holding.asset_id == asset_id]
        assert len(rows) == 1, f"expected exactly one open holding of asset {asset_id}, got {rows}"
        assert (rows[0].valuation_source, rows[0].current_value) == ("ESTIMATED_AT_COST", Decimal("200")), f"barrier: on V the asset must be valued at its 200 EUR cost, got {(rows[0].valuation_source, rows[0].current_value)}"

    @staticmethod
    def _record_valued_at_cost_entries(monkeypatch) -> list:
        """The VALUED_AT_COST entries ``get_summary`` hands the data-quality report, one item per call (None: none).

        The entries are not in the summary (only the issue's ids and names are), so they are read where they are
        handed over; the real report is still built from them.
        """
        calls: list = []
        build = DerivedViewsBuilder.build_data_quality_report

        def recording(self, **kwargs):
            calls.append(kwargs.get("valued_at_cost_assets_dto"))
            return build(self, **kwargs)

        monkeypatch.setattr(DerivedViewsBuilder, "build_data_quality_report", recording)
        return calls

    @pytest.mark.asyncio
    async def test_provider_asset_at_cost_past_the_grace_is_listed_as_valued_at_cost(self, session, test_user, broker_with_access, test_asset_with_provider, monkeypatch):
        """Provider asset at cost since V−20 (> 14 days): one VALUED_AT_COST warning listing it, with
        the issue's full shape; not in TRANSACTION_IMPLIED, not in MISSING_PRICE. Its entry dates the
        position from its first acquisition, the ADJUSTMENT of V−20.

        Before J-17: no VALUED_AT_COST code; the asset was LAST_TRADE_PRICE (its ADJUSTMENT was a price)
        and listed under TRANSACTION_IMPLIED. (J-17's first version dated the entry None: its first
        position date counted BUY/SELL only.)
        """
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_adjustment(session, broker, asset, days_before_v=20)
        handed_over = self._record_valued_at_cost_entries(monkeypatch)

        summary = await self._summary(session, test_user)

        self._assert_at_cost_on_v(summary, asset.id)
        issue = next((issue for issue in summary.data_quality.issues if issue.code == "VALUED_AT_COST"), None)
        assert issue is not None, f"no VALUED_AT_COST issue among {[i.code for i in summary.data_quality.issues]}"
        assert {
            "domain": issue.domain,
            "severity": issue.severity,
            "message_i18n_key": issue.message_i18n_key,
            "message_params": issue.message_params,
            "count": issue.count,
            "affected_asset_ids": issue.affected_asset_ids,
            "affected_asset_names": issue.affected_asset_names,
            "cta_action": issue.cta_action,
            "cta_target": issue.cta_target,
            "group_key": issue.group_key,
        } == {
            "domain": IssueDomain.PORTFOLIO,
            "severity": IssueSeverity.WARNING,
            "message_i18n_key": "dataQuality.valuedAtCost",
            "message_params": {"count": 1, "as_of_date": self.V.isoformat()},
            "count": 1,
            "affected_asset_ids": [asset.id],
            "affected_asset_names": [asset.display_name],
            "cta_action": "navigate_asset",
            "cta_target": str(asset.id),
            "group_key": "valued_at_cost",
        }
        assert handed_over, "get_summary built no data-quality report"
        entries = handed_over[-1] or []
        assert [(entry.asset_id, entry.broker_id, entry.first_position_date) for entry in entries] == [(asset.id, broker.id, self._day(20))]
        assert asset.id not in self._listed_ids(summary, "TRANSACTION_IMPLIED")
        assert asset.id not in self._listed_ids(summary, "MISSING_PRICE")
        assert asset.id not in {item.asset_id for item in summary.missing_price_assets}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("days_before_v", "listed"),
        [
            pytest.param(5, False, id="within-grace"),
            pytest.param(TRANSACTION_IMPLIED_GRACE_DAYS, False, id="last-day-of-grace"),
            pytest.param(TRANSACTION_IMPLIED_GRACE_DAYS + 1, True, id="first-day-past-grace"),
        ],
    )
    async def test_provider_asset_at_cost_follows_the_transaction_implied_grace(self, session, test_user, broker_with_access, test_asset_with_provider, days_before_v, listed):
        """The grace of TRANSACTION_IMPLIED, counted from the asset's first acquisition — here its only
        one, the ADJUSTMENT (an asset at cost has no BUY or SELL by definition): listed only past
        ``TRANSACTION_IMPLIED_GRACE_DAYS`` days. Never in TRANSACTION_IMPLIED.

        Before J-17: LAST_TRADE_PRICE (the barrier fails), and listed under TRANSACTION_IMPLIED whatever
        its age — that grace counted from the first BUY/SELL, which an adjustment-only asset does not
        have. (J-17's first version counted the at-cost grace from the BUY/SELL date too, so it listed
        the asset at once: ``within-grace`` and ``last-day-of-grace`` were red there.)
        """
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_adjustment(session, broker, asset, days_before_v=days_before_v)

        summary = await self._summary(session, test_user)

        self._assert_at_cost_on_v(summary, asset.id)
        listed_now = asset.id in self._listed_ids(summary, "VALUED_AT_COST")
        assert listed_now is listed, f"asset {asset.id}, at cost since {self._day(days_before_v)} (its only acquisition): listed={listed_now} under VALUED_AT_COST on {self.V}, expected {listed} (grace {TRANSACTION_IMPLIED_GRACE_DAYS} days from the first acquisition)"
        assert asset.id not in self._listed_ids(summary, "TRANSACTION_IMPLIED")
        assert asset.id not in self._listed_ids(summary, "MISSING_PRICE")

    @pytest.mark.asyncio
    async def test_manual_asset_at_cost_is_not_listed(self, session, test_user, broker_with_access, test_asset):
        """An asset without a provider assignment, at cost since V−20: its cost is its intended value,
        so nothing is listed — no VALUED_AT_COST, no TRANSACTION_IMPLIED, no MISSING_PRICE.

        Before J-17: LAST_TRADE_PRICE (the barrier fails); nothing listed either (manual assets were
        already suppressed from TRANSACTION_IMPLIED).
        """
        broker, _ = broker_with_access
        await self._seed_adjustment(session, broker, test_asset, days_before_v=20)
        assigned = (await session.execute(select(AssetProviderAssignment.id).where(AssetProviderAssignment.asset_id == test_asset.id))).all()
        assert assigned == [], "precondition: the asset has no provider assignment"

        summary = await self._summary(session, test_user)

        self._assert_at_cost_on_v(summary, test_asset.id)
        for code in ("VALUED_AT_COST", "TRANSACTION_IMPLIED", "MISSING_PRICE"):
            assert test_asset.id not in self._listed_ids(summary, code), f"manual asset {test_asset.id} listed under {code}"


# =============================================================================
# TestTransferShareMismatchDataQuality (J-43)
# =============================================================================


class TestTransferShareMismatchDataQuality:
    """J-43 — a linked internal pair between two brokers the user owns at different shares, end to end.

    Each leg counts at its own broker's share, so moving 1000 EUR from a broker owned at 1 to one owned at 0.5 turns 500
    of the user's money into a loss (D-MF4 = a: the gap is a result, never capital). The data-quality report is the
    user's only explanation of it: one INFO issue ``TRANSFER_SHARE_MISMATCH`` counting the pairs and one string per pair
    in ``share_mismatch_warnings`` naming both legs — from both report builders of ``portfolio_service``
    (``get_summary``'s, and ``get_report``'s own when the summary is not requested) — and the engine's result carries
    the pair as a ``ShareMismatch``. At equal shares nothing is reported.

    The pair is same-day on purpose: on HEAD 252835dce the classifier does not even warn for it (J-43a), and no warning
    of any date leaves the classifier (J-43b). Each test owns its user and its two brokers (flushed, rolled back by
    ``session``), so the counts are the counts of what it wrote; a barrier first proves the pair is in the scope at the
    shares the case claims. ``ShareMismatch`` is read from ``models`` when the test runs.
    """

    D = date(2025, 3, 10)  # the deposit and both legs of the transfer
    V = date(2025, 3, 20)  # the valuation day

    async def _owned_broker(self, session, user: User, share: str) -> Broker:
        broker = Broker(name=f"PfBroker_J43_{uuid4().hex[:12]}")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal(share)))
        await session.flush()
        return broker

    async def _same_day_transfer(self, session, user: User, *, sender_share: str, receiver_share: str) -> tuple[Transaction, Transaction]:
        """5000 EUR deposited on D at a sender owned at ``sender_share``, then 1000 EUR moved the same day to a receiver
        owned at ``receiver_share``: a CASH_TRANSFER pair linked both ways (both legs flushed first: the foreign key of
        ``related_transaction_id`` is deferred). Returns the two legs, the one sent first."""
        sender = await self._owned_broker(session, user, sender_share)
        receiver = await self._owned_broker(session, user, receiver_share)
        session.add(Transaction(broker_id=sender.id, type=TransactionType.DEPOSIT, date=self.D, amount=Decimal("5000"), currency="EUR"))
        sent = Transaction(broker_id=sender.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=self.D, quantity=Decimal("0"), amount=Decimal("-1000"), currency="EUR")
        received = Transaction(broker_id=receiver.id, asset_id=None, type=TransactionType.CASH_TRANSFER, date=self.D, quantity=Decimal("0"), amount=Decimal("1000"), currency="EUR")
        session.add_all([sent, received])
        await session.flush()
        sent.related_transaction_id = received.id
        received.related_transaction_id = sent.id
        await session.flush()
        return sent, received

    @staticmethod
    def _mismatch_problems(where: str, data_quality, legs: tuple[Transaction, Transaction]) -> list[str]:
        """What keeps ``data_quality`` from reporting exactly the one pair ``legs``: one INFO TRANSFER_SHARE_MISMATCH
        issue counting 1, and one string naming both legs (the rest of its text is not pinned)."""
        if data_quality is None:
            return [f"{where}: no data quality"]
        problems: list[str] = []
        issues = [(issue.severity, issue.count, issue.message_params) for issue in data_quality.issues if issue.code == "TRANSFER_SHARE_MISMATCH"]
        if issues != [(IssueSeverity.INFO, 1, {"count": 1})]:
            problems.append(f"{where}: TRANSFER_SHARE_MISMATCH issues {issues}, expected one INFO counting 1; the report carries {[issue.code for issue in data_quality.issues]}")
        leg_ids = {leg.id for leg in legs}
        strings = data_quality.share_mismatch_warnings
        if len(strings) != 1 or not leg_ids <= {int(number) for number in re.findall(r"\d+", strings[0])}:
            problems.append(f"{where}: share_mismatch_warnings {strings}, expected one string naming both legs {sorted(leg_ids)}")
        return problems

    @pytest.mark.asyncio
    async def test_summary_reports_a_same_day_transfer_between_different_shares(self, session, test_user):
        """Red (J-43a + J-43b). Sender at 1, receiver at 0.5: the net worth is 4000 + 1000 x 0.5 = 4500 (barrier), and the
        summary's data quality carries one TRANSFER_SHARE_MISMATCH issue counting 1 and one string naming both legs.

        HEAD: neither — no issue, ``share_mismatch_warnings == []``: the classifier does not warn for a same-day pair,
        and nothing takes its warnings out of the engine."""
        legs = await self._same_day_transfer(session, test_user, sender_share="1", receiver_share="0.5")

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, target_currency_override="EUR", date_to=self.V)

        assert summary.net_worth.amount == Decimal("4500"), f"barrier: each leg at its broker's share, got {summary.net_worth.amount}"
        problems = self._mismatch_problems("get_summary", summary.data_quality, legs)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("include_summary", [True, False], ids=["summary_builds_it", "report_builds_it"])
    async def test_report_reports_it_from_either_builder(self, session, test_user, include_summary):
        """Red (J-43a + J-43b). The same pair through ``get_report`` over D..V: with the summary, the report's data quality
        is the summary's; without it, ``get_report`` builds its own (the second ``build_data_quality_report`` call of
        portfolio_service.py). Either way one issue counting 1 and one string naming both legs. Barrier: the engine's
        states start on D, so it replayed these rows.

        HEAD: neither, from either builder."""
        legs = await self._same_day_transfer(session, test_user, sender_share="1", receiver_share="0.5")
        _portfolio_l2_cache.clear()

        report = await PortfolioService(session).get_report(
            user_id=test_user.id,
            query=PortfolioReportQuery(
                target_currency="EUR",
                include_summary=include_summary,
                include_history=False,
                include_allocation_history=False,
                include_positions_contribution=False,
                date_range={"start": self.D.isoformat(), "end": self.V.isoformat()},
            ),
        )

        assert report.metadata.computed_date_from == self.D, f"barrier: the engine replayed this user's rows from D, got {report.metadata.computed_date_from}"
        problems = self._mismatch_problems(f"get_report(include_summary={include_summary})", report.data_quality, legs)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_engine_result_carries_the_pair_as_a_share_mismatch(self, session, test_user):
        """Red (J-43b). ``PortfolioCalculationEngine.calculate`` returns the pair as one ShareMismatch: the legs' ids lower
        first, their brokers and shares (the engine's ``broker_shares``: 1 for the sender, 0.5 for the receiver) in that
        order, dated D.

        HEAD: AttributeError — ``models`` has no ShareMismatch, PortfolioCalculationResult no ``share_mismatches``."""
        sent, received = await self._same_day_transfer(session, test_user, sender_share="1", receiver_share="0.5")
        share_of = {sent.broker_id: Decimal("1"), received.broker_id: Decimal("0.5")}
        first, second = sorted((sent, received), key=lambda leg: leg.id)

        result = await portfolio_engine_module.PortfolioCalculationEngine(session).calculate(user_id=test_user.id, date_to=self.V, target_currency="EUR")

        expected = portfolio_models_module.ShareMismatch(tx_ids=(first.id, second.id), broker_ids=(first.broker_id, second.broker_id), shares=(share_of[first.broker_id], share_of[second.broker_id]), date=self.D)
        assert result.share_mismatches == [expected]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("share", "net_worth"), [("1", "5000"), ("0.5", "2500")], ids=["both_whole", "both_half"])
    async def test_equal_shares_report_nothing(self, session, test_user, share, net_worth):
        """Guard (green on HEAD and after J-43). The same transfer between two brokers owned at the same share — whole,
        or half each — is no mismatch: no TRANSFER_SHARE_MISMATCH issue and no string. Barrier first: the net worth is
        the 5000 deposited, at that share."""
        await self._same_day_transfer(session, test_user, sender_share=share, receiver_share=share)

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, target_currency_override="EUR", date_to=self.V)

        assert summary.net_worth.amount == Decimal(net_worth), f"barrier: the pair is in the scope at share {share}, got {summary.net_worth.amount}"
        data_quality = summary.data_quality
        assert data_quality is not None
        assert [issue.code for issue in data_quality.issues if issue.code == "TRANSFER_SHARE_MISMATCH"] == []
        assert data_quality.share_mismatch_warnings == []


# =============================================================================
# TestStalePriceDataQuality
# =============================================================================


class TestStalePriceDataQuality:
    """STALE_PRICE ("prezzi non aggiornati") — decision D8 (30/09), R2 step 13 item 9.

    The engine already knows, per open position, whether its market price has been
    carried forward for more than ``STALE_PRICE_THRESHOLD_DAYS`` (7) days
    (``DailyPositionState.valuation_stale``), and ``build_data_quality_report`` already
    renders STALE_PRICE from ``stale_prices_dto``. But ``get_summary`` never passes that
    argument — not since the engine rewrite 77b976ebc — so the banner never appears.

    The approved rule: at ``date_to`` an asset is flagged when ALL of these hold —
      * it has an open position (quantity above dust);
      * that position is valued at a MARKET price, not at a trade price;
      * that market price is carried forward more than 7 days;
      * the asset has a provider assignment.
    One ``StalePriceAsset`` per asset (never per broker), ``stale_days`` counted from the
    carried price date to the valuation date, and the CTA is ``sync_asset_prices``.

    Each test owns its user, broker(s), asset and prices — flushed, then rolled back by
    the ``session`` fixture — so the portfolio under test is exactly what the test wrote;
    that is what makes the exact assertions below legitimate. Dates are relative to
    ``date.today()``: staleness is measured against the calendar, so a fixed date would
    only test the day it was written. Every negative case first proves, through the
    holding row, that its position is valued the way the case claims — an absence
    assertion without that barrier would also pass on a portfolio that never held
    anything.
    """

    @pytest.fixture(autouse=True)
    def _pin_today(self):
        """Read the calendar once per test: seeding, ``date_to`` and the expected ages
        then agree even if the test straddles midnight."""
        self.today = date.today()

    async def _seed_prices(self, session, asset: Asset, *days_ago: int) -> None:
        """EUR market quotes ``days_ago`` before today, closes 100, 101, … in the given order."""
        for index, days in enumerate(days_ago):
            close = Decimal(100 + index)
            session.add(PriceHistory(asset_id=asset.id, date=self.today - timedelta(days=days), open=close, high=close, low=close, close=close, volume=Decimal("1"), currency="EUR", source_plugin_key="manual_test"))
        await session.flush()

    async def _seed_position(self, session, broker: Broker, asset: Asset, *, bought_days_ago: int, sold_days_ago: int | None = None) -> None:
        """Fund ``broker``, BUY 10 units at 100 EUR, and optionally SELL all of them."""
        bought = self.today - timedelta(days=bought_days_ago)
        rows = [
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=bought, amount=Decimal("10000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=bought, quantity=Decimal("10"), amount=Decimal("-1000"), currency="EUR"),
        ]
        if sold_days_ago is not None:
            rows.append(Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=self.today - timedelta(days=sold_days_ago), quantity=Decimal("-10"), amount=Decimal("1000"), currency="EUR"))
        session.add_all(rows)
        await session.flush()

    async def _summary(self, session, user: User, date_to: date | None = None):
        return await PortfolioService(session).get_summary(user_id=user.id, date_to=date_to or self.today)

    @staticmethod
    def _stale_issue(summary):
        return next((issue for issue in summary.data_quality.issues if issue.code == IssueCode.STALE_PRICE), None)

    @staticmethod
    def _only_holding(summary, asset_id: int):
        rows = [holding for holding in summary.holdings if holding.asset_id == asset_id]
        assert len(rows) == 1, f"expected exactly one open holding of asset {asset_id}, got {rows}"
        return rows[0]

    @classmethod
    def _assert_not_flagged(cls, summary) -> None:
        issue = cls._stale_issue(summary)
        assert issue is None, f"unexpected STALE_PRICE issue: {issue}"
        assert summary.data_quality.stale_prices == []

    @pytest.mark.asyncio
    async def test_provider_asset_with_ten_day_old_market_price_is_flagged(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Case 1 — the defect. An open position of a provider-priced asset whose last
        quote is 10 days old is flagged once, with its carried date, its age in days and a
        «Sincronizza» CTA. Red until ``get_summary`` passes ``stale_prices_dto``."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        today = self.today
        await self._seed_position(session, broker, asset, bought_days_ago=40)
        await self._seed_prices(session, asset, 40, 30, 20, 10)

        summary = await self._summary(session, test_user)

        holding = self._only_holding(summary, asset.id)
        assert holding.valuation_source == "MARKET_PRICE"
        assert holding.valuation_reference_date == today - timedelta(days=10)

        issue = self._stale_issue(summary)
        assert issue is not None, f"no STALE_PRICE issue; the report carries {[i.code for i in summary.data_quality.issues]}"
        assert issue.severity == IssueSeverity.WARNING
        assert issue.message_i18n_key == "dataQuality.stalePrice"
        assert issue.message_params["count"] == 1
        assert issue.count == 1
        assert issue.affected_asset_ids == [asset.id]
        assert issue.affected_asset_names == [asset.display_name]
        assert issue.cta_action == "sync_asset_prices"
        assert summary.data_quality.stale_prices == [StalePriceAsset(asset_id=asset.id, name=asset.display_name, last_price_date=today - timedelta(days=10), stale_days=10)]

    @pytest.mark.asyncio
    async def test_stale_price_alone_reports_carried_forward_status(self, session, test_user, broker_with_access, test_asset_with_provider):
        """D8 §3 — a stale quote with nothing worse in the report makes the summary's
        data quality ``carried_forward`` (derived by the schema) and lists the asset in
        ``stale_prices``. Red today: ``stale_prices`` is never filled, so the status
        reads ``ok``."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_position(session, broker, asset, bought_days_ago=40)
        await self._seed_prices(session, asset, 40, 30, 20, 10)

        dq = (await self._summary(session, test_user)).data_quality

        # "Nothing worse": each of these would make the status PARTIAL instead.
        assert dq.missing_price_assets == []
        assert dq.missing_fx_pairs == []
        assert dq.incomplete_nav_dates == []
        assert asset.id in {stale.asset_id for stale in dq.stale_prices}
        assert dq.data_quality_status == DataQualityStatus.CARRIED_FORWARD

    @pytest.mark.asyncio
    async def test_market_price_exactly_seven_days_old_is_not_stale(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Case 2 — control on the threshold: stale means carried *more than* 7 days, so a
        quote exactly 7 days old is still current."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        today = self.today
        await self._seed_position(session, broker, asset, bought_days_ago=40)
        await self._seed_prices(session, asset, 40, 30, 20, 7)

        summary = await self._summary(session, test_user)

        holding = self._only_holding(summary, asset.id)
        assert holding.valuation_source == "MARKET_PRICE"
        assert holding.valuation_reference_date == today - timedelta(days=7)
        self._assert_not_flagged(summary)

    @pytest.mark.asyncio
    async def test_fresh_market_price_is_not_flagged(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Case 3 — control: a quote carried for 2 days is ordinary (weekends do that)."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        today = self.today
        await self._seed_position(session, broker, asset, bought_days_ago=40)
        await self._seed_prices(session, asset, 40, 30, 20, 2)

        summary = await self._summary(session, test_user)

        holding = self._only_holding(summary, asset.id)
        assert holding.valuation_source == "MARKET_PRICE"
        assert holding.valuation_reference_date == today - timedelta(days=2)
        self._assert_not_flagged(summary)

    @pytest.mark.asyncio
    async def test_manual_asset_with_stale_market_price_is_not_flagged(self, session, test_user, broker_with_access, test_asset):
        """Case 4 — control on the provider condition: a manual asset (no provider
        assignment) whose market price is 10 days old is exactly as stale as case 1 for
        the engine, but there is nothing to sync, so it is never flagged."""
        broker, _ = broker_with_access
        asset = test_asset
        today = self.today
        assignment = (await session.execute(select(AssetProviderAssignment.id).where(AssetProviderAssignment.asset_id == asset.id))).first()
        assert assignment is None, "precondition: the manual asset must have no provider assignment"
        await self._seed_position(session, broker, asset, bought_days_ago=40)
        await self._seed_prices(session, asset, 40, 30, 20, 10)

        summary = await self._summary(session, test_user)

        holding = self._only_holding(summary, asset.id)
        assert holding.valuation_source == "MARKET_PRICE"
        assert holding.valuation_reference_date == today - timedelta(days=10)
        self._assert_not_flagged(summary)

    @pytest.mark.asyncio
    async def test_position_sold_before_date_to_is_not_flagged(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Case 5 — control on the open-position condition: the rule is evaluated at
        ``date_to``, and a position fully sold before it has no price to be stale.

        Barrier: the day before the sale the same holding was open and valued at a
        market price already carried 9 days — the only thing that changes by today is
        that the position is closed."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        today = self.today
        await self._seed_position(session, broker, asset, bought_days_ago=40, sold_days_ago=5)
        await self._seed_prices(session, asset, 40, 30, 20, 15)

        before_sale = await self._summary(session, test_user, date_to=today - timedelta(days=6))
        summary = await self._summary(session, test_user)

        holding = self._only_holding(before_sale, asset.id)
        assert holding.valuation_source == "MARKET_PRICE"
        assert holding.valuation_reference_date == today - timedelta(days=15)
        assert [h for h in summary.holdings if h.asset_id == asset.id] == []
        self._assert_not_flagged(summary)

    @pytest.mark.asyncio
    async def test_trade_priced_provider_asset_is_left_to_transaction_implied(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Case 6 — control on the MARKET_PRICE condition: a provider asset with no quote
        at all, bought 20 days ago, is valued at its trade price. The engine marks that
        valuation stale too (20 days > 7), but it is TRANSACTION_IMPLIED's case — the
        missing quote is already reported there — and must not be reported twice."""
        broker, _ = broker_with_access
        asset = test_asset_with_provider
        await self._seed_position(session, broker, asset, bought_days_ago=20)

        summary = await self._summary(session, test_user)

        holding = self._only_holding(summary, asset.id)
        assert holding.valuation_source == "LAST_TRADE_PRICE"
        implied = next((issue for issue in summary.data_quality.issues if issue.code == IssueCode.TRANSACTION_IMPLIED), None)
        assert implied is not None and asset.id in implied.affected_asset_ids, "barrier: past the 14-day grace the asset must be reported as valued at cost"
        self._assert_not_flagged(summary)

    @pytest.mark.asyncio
    async def test_asset_held_at_two_brokers_is_one_stale_entry(self, session, test_user, broker_with_access, test_asset_with_provider):
        """Case 7 — aggregation: one asset held at two brokers is one stale price, so one
        ``StalePriceAsset`` and one affected id, not one per broker. Red today because
        nothing is reported at all; a per-broker fix would be red with two entries."""
        broker, _ = broker_with_access
        second = Broker(name=f"PfBroker_stale_{uuid4().hex[:12]}")
        session.add(second)
        await session.flush()
        session.add(BrokerUserAccess(broker_id=second.id, user_id=test_user.id, role=UserRole.OWNER, share_percentage=Decimal("1.0")))
        await session.flush()
        asset = test_asset_with_provider
        today = self.today
        await self._seed_position(session, broker, asset, bought_days_ago=40)
        await self._seed_position(session, second, asset, bought_days_ago=35)
        await self._seed_prices(session, asset, 40, 30, 20, 10)

        summary = await self._summary(session, test_user)

        holdings = [h for h in summary.holdings if h.asset_id == asset.id]
        assert {h.broker_id for h in holdings} == {broker.id, second.id}
        assert {(h.valuation_source, h.valuation_reference_date) for h in holdings} == {("MARKET_PRICE", today - timedelta(days=10))}

        entries = [stale for stale in summary.data_quality.stale_prices if stale.asset_id == asset.id]
        assert entries == [StalePriceAsset(asset_id=asset.id, name=asset.display_name, last_price_date=today - timedelta(days=10), stale_days=10)]
        issue = self._stale_issue(summary)
        assert issue is not None
        assert issue.affected_asset_ids == [asset.id]
        assert issue.count == 1
        assert issue.message_params["count"] == 1


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
    async def test_summary_maps_adjustment_only_holding_at_cost(self, session, test_user, broker_with_access, test_asset):
        """J-17: a holding whose only acquisition is a priced ADJUSTMENT (5 at 20 EUR, then a 2:1 split)
        and that has no quote, BUY or SELL is valued at its book cost: ESTIMATED_AT_COST, value 100,
        no price at all (current, effective and reference empty), gain 0, not a missing price.

        Before J-17: LAST_TRADE_PRICE at the adjustment's 20 EUR restated through the split — current
        price 10, effective 10 EUR, reference 2025-01-02 at 20 EUR, split_adjusted True (same value 100).
        """
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
        assert holding.valuation_source == "ESTIMATED_AT_COST"
        assert holding.current_price is None
        assert holding.current_value == Decimal("100")
        assert holding.gain_loss == Decimal("0")
        assert holding.valuation_effective_unit_price is None
        assert holding.valuation_effective_currency is None
        assert holding.valuation_reference_date is None
        assert holding.valuation_reference_unit_price is None
        assert holding.valuation_reference_currency is None
        assert holding.missing_fx_pair is None
        assert test_asset.id not in {asset.asset_id for asset in summary.missing_price_assets}
        assert IssueCode.MISSING_PRICE not in {issue.code for issue in summary.data_quality.issues}

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
    async def test_implicit_date_rollover_and_explicit_same_day_use_distinct_l2_keys(
        self,
        session,
        test_user,
        broker_with_access,
        monkeypatch,
        request,
    ):
        """Cache identity preserves raw date_to intent plus its effective date."""
        broker, _ = broker_with_access
        first_day = date(2037, 5, 10)
        second_day = first_day + timedelta(days=1)
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=first_day - timedelta(days=2),
                amount=Decimal("750"),
                currency="EUR",
            )
        )
        await session.flush()
        _portfolio_l2_cache.clear()
        portfolio_engine_module._portfolio_blob_cache.clear()
        request.addfinalizer(_portfolio_l2_cache.clear)
        request.addfinalizer(portfolio_engine_module._portfolio_blob_cache.clear)

        class MutableToday(date):
            current = first_day

            @classmethod
            def today(cls):
                return cls.current

        monkeypatch.setattr(
            portfolio_service_module,
            "date_type",
            MutableToday,
        )
        monkeypatch.setattr(
            portfolio_engine_module,
            "date_type",
            MutableToday,
        )

        observed_keys = []
        original_get = _portfolio_l2_cache.get

        def capture_get(key):
            observed_keys.append(key)
            return original_get(key)

        monkeypatch.setattr(_portfolio_l2_cache, "get", capture_get)

        engine_calls = {"count": 0}
        original_calculate = portfolio_engine_module.PortfolioCalculationEngine.calculate

        async def counting_calculate(engine_self, *args, **kwargs):
            engine_calls["count"] += 1
            return await original_calculate(engine_self, *args, **kwargs)

        monkeypatch.setattr(
            portfolio_engine_module.PortfolioCalculationEngine,
            "calculate",
            counting_calculate,
        )

        service = PortfolioService(session)
        implicit_query = PortfolioReportQuery(
            broker_ids=[broker.id],
            target_currency="EUR",
            include_summary=False,
            include_history=False,
            include_allocation_history=False,
            include_breakdown=False,
            include_positions_contribution=False,
        )
        explicit_query = PortfolioReportQuery(
            broker_ids=[broker.id],
            target_currency="EUR",
            date_range={"end": str(first_day)},
            include_summary=False,
            include_history=False,
            include_allocation_history=False,
            include_breakdown=False,
            include_positions_contribution=False,
        )

        implicit_first = await service.get_report(
            user_id=test_user.id,
            query=implicit_query,
        )
        assert implicit_first.metadata.requested_date_to is None
        assert implicit_first.metadata.computed_date_to == first_day

        explicit_same_day = await service.get_report(
            user_id=test_user.id,
            query=explicit_query,
        )
        assert explicit_same_day.metadata.requested_date_to == first_day
        assert explicit_same_day.metadata.computed_date_to == first_day
        assert engine_calls["count"] == 2
        assert len(observed_keys) == 2
        assert observed_keys[0] != observed_keys[1]

        MutableToday.current = second_day
        implicit_second = await service.get_report(
            user_id=test_user.id,
            query=implicit_query,
        )

        assert implicit_second.metadata.requested_date_to is None
        assert implicit_second.metadata.computed_date_to == second_day
        assert engine_calls["count"] == 3
        assert len(observed_keys) == 3
        assert len(set(observed_keys)) == 3

    @pytest.mark.asyncio
    async def test_layer2_uses_exact_shared_fx_identity_for_summaryless_reports_and_never_falls_back_stale(
        self,
        session,
        test_user,
        broker_with_access,
        monkeypatch,
        request,
    ):
        """Every report shape uses the shared FX identity verbatim in its L2 key.

        Stable identity -> hit. Changed identity -> fresh engine call; a fresh
        failure propagates instead of returning the stale prior report.
        """
        broker, _ = broker_with_access
        report_date = date(2035, 4, 30)
        session.add(
            Transaction(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=report_date - timedelta(days=1),
                amount=Decimal("750"),
                currency="EUR",
            )
        )
        await session.flush()
        _portfolio_l2_cache.clear()
        portfolio_engine_module._portfolio_blob_cache.clear()
        request.addfinalizer(_portfolio_l2_cache.clear)
        request.addfinalizer(portfolio_engine_module._portfolio_blob_cache.clear)

        identity = {"value": "shared-fx-identity-a"}
        identity_calls: list[tuple[object, set[int], str, date]] = []

        async def shared_identity(db, scope_broker_ids, target_currency, date_to):
            identity_calls.append((db, set(scope_broker_ids), target_currency, date_to))
            return identity["value"]

        monkeypatch.setattr(
            portfolio_engine_module,
            "compute_portfolio_fx_cache_identity",
            shared_identity,
        )

        observed_keys = []
        original_get = _portfolio_l2_cache.get

        def capture_get(key):
            observed_keys.append(key)
            return original_get(key)

        monkeypatch.setattr(_portfolio_l2_cache, "get", capture_get)

        engine_calls = {"count": 0, "fail": False}
        original_calculate = portfolio_engine_module.PortfolioCalculationEngine.calculate

        async def controlled_calculate(engine_self, *args, **kwargs):
            engine_calls["count"] += 1
            if engine_calls["fail"]:
                raise RuntimeError("fresh FX identity calculation failed")
            return await original_calculate(engine_self, *args, **kwargs)

        monkeypatch.setattr(
            portfolio_engine_module.PortfolioCalculationEngine,
            "calculate",
            controlled_calculate,
        )

        service = PortfolioService(session)
        query = PortfolioReportQuery(
            broker_ids=[broker.id],
            target_currency="EUR",
            date_range={"start": "2035-04-01", "end": str(report_date)},
            include_summary=False,
            include_history=False,
            include_allocation_history=False,
            include_breakdown=False,
            include_positions_contribution=False,
        )

        first = await service.get_report(user_id=test_user.id, query=query)
        second = await service.get_report(user_id=test_user.id, query=query)

        assert second.model_dump() == first.model_dump()
        assert engine_calls["count"] == 1
        assert len(observed_keys) == 2
        assert observed_keys[0] == observed_keys[1]
        assert observed_keys[0][-2] == "shared-fx-identity-a"
        assert observed_keys[0][-1] == "no_yoc"
        assert len(identity_calls) == 3
        assert all(call[0] is session for call in identity_calls)
        assert all(call[1:] == ({broker.id}, "EUR", report_date) for call in identity_calls)

        identity["value"] = "shared-fx-identity-b"
        engine_calls["fail"] = True
        with pytest.raises(RuntimeError, match="fresh FX identity calculation failed"):
            await service.get_report(user_id=test_user.id, query=query)

        assert engine_calls["count"] == 2
        assert observed_keys[-1][-2] == "shared-fx-identity-b"
        assert observed_keys[-1][-1] == "no_yoc"
        assert observed_keys[-1] != observed_keys[0]

    @pytest.mark.asyncio
    async def test_layer2_identity_changes_when_linked_split_material_changes(
        self,
        session,
        test_user,
        broker_with_access,
        test_asset,
        monkeypatch,
        request,
    ):
        """AssetEvent split ratio is a material L2 dependency even without summary."""
        broker, _ = broker_with_access
        report_date = date(2036, 12, 31)
        split_event = AssetEvent(
            asset_id=test_asset.id,
            date=date(2036, 6, 1),
            type=AssetEventType.SPLIT,
            value=Decimal("2"),
            currency="EUR",
        )
        session.add(split_event)
        await session.flush()
        assert split_event.id is not None
        session.add_all(
            [
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date(2035, 1, 1),
                    quantity=Decimal("10"),
                    amount=Decimal("-100"),
                    currency="EUR",
                ),
                Transaction(
                    broker_id=broker.id,
                    asset_id=test_asset.id,
                    asset_event_id=split_event.id,
                    type=TransactionType.ADJUSTMENT,
                    date=split_event.date,
                    quantity=Decimal("10"),
                    amount=Decimal("0"),
                    currency="EUR",
                ),
            ]
        )
        await session.flush()
        _portfolio_l2_cache.clear()
        portfolio_engine_module._portfolio_blob_cache.clear()
        request.addfinalizer(_portfolio_l2_cache.clear)
        request.addfinalizer(portfolio_engine_module._portfolio_blob_cache.clear)

        observed_keys = []
        original_get = _portfolio_l2_cache.get

        def capture_get(key):
            observed_keys.append(key)
            return original_get(key)

        monkeypatch.setattr(_portfolio_l2_cache, "get", capture_get)

        engine_calls = {"count": 0}
        original_calculate = portfolio_engine_module.PortfolioCalculationEngine.calculate

        async def counting_calculate(engine_self, *args, **kwargs):
            engine_calls["count"] += 1
            return await original_calculate(engine_self, *args, **kwargs)

        monkeypatch.setattr(
            portfolio_engine_module.PortfolioCalculationEngine,
            "calculate",
            counting_calculate,
        )

        service = PortfolioService(session)
        query = PortfolioReportQuery(
            broker_ids=[broker.id],
            target_currency="EUR",
            date_range={"start": "2036-01-01", "end": str(report_date)},
            include_summary=False,
            include_history=False,
            include_allocation_history=False,
            include_breakdown=False,
            include_positions_contribution=False,
        )

        await service.get_report(user_id=test_user.id, query=query)
        await service.get_report(user_id=test_user.id, query=query)
        assert engine_calls["count"] == 1
        assert observed_keys[0] == observed_keys[1]

        split_event.value = Decimal("3")
        await session.flush()

        await service.get_report(user_id=test_user.id, query=query)
        assert engine_calls["count"] == 2
        assert observed_keys[-1] != observed_keys[0]
        assert observed_keys[-1][-1] != observed_keys[0][-1]

    @pytest.mark.asyncio
    async def test_get_report_narrower_date_to_not_corrupted_by_wider_blob_cache(self, session, test_user, broker_with_access, test_asset):
        """Regression test for dashboard KPI cards showing 0-delta for a custom date range.

        Root cause: the L1 portfolio "blob" cache (financial_math/portfolio/engine.py) is keyed by
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

    @pytest.mark.asyncio
    async def test_get_report_income_history_flag_gates_section_and_busts_l2_cache(self, session, test_user, broker_with_access):
        """G1c wiring: PortfolioReportQuery.include_income_history gates
        PortfolioReportResponse.income_history and metadata.included_features, and
        the flag is part of the L2 cache key (_portfolio_l2_cache) — flipping ONLY
        this flag between two otherwise-identical calls must never return the
        first call's cached (flag=False) report for the second (flag=True) call.
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2025, 8, 1), amount=Decimal("1000"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 8, 5), amount=Decimal("40"), currency="EUR"),
            ]
        )
        await session.flush()
        _portfolio_l2_cache.clear()

        service = PortfolioService(session)
        base_kwargs = {
            "broker_ids": [broker.id],
            "include_summary": True,
            "include_history": False,
            "include_allocation_history": False,
            "date_range": {"start": "2025-08-01", "end": "2025-08-31"},
        }

        off = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**base_kwargs, include_income_history=False))
        assert off.income_history is None
        assert "income_history" not in off.metadata.included_features

        on = await service.get_report(user_id=test_user.id, query=PortfolioReportQuery(**base_kwargs, include_income_history=True))
        assert on.income_history is not None, "must recompute, not reuse the flag=False L2 cache entry"
        assert "income_history" in on.metadata.included_features
        assert [p.date for p in on.income_history.points] == [date(2025, 8, 5)]
        assert on.income_history.points[0].dividend.amount == Decimal("40")
        assert on.income_history.points[0].interest.amount == Decimal("0")
        # Reconciles with summary.period_income for the identical (date_from, date_to] window.
        assert on.summary.period_income.amount == Decimal("40")


# =============================================================================
# G1c — SIGNED PERSONAL INCOME HISTORY (get_income_history + reconciliation)
# =============================================================================


class TestGetIncomeHistory:
    """PortfolioService.get_income_history() — a pure transaction scan (no engine
    run) over DIVIDEND/INTEREST transactions, signed (plan §4.4): a legacy
    negative correction reduces its bucket instead of being abs()'d into it.

    ``sum(dividend) + sum(interest)`` across every point must reproduce
    ``PortfolioSummary.period_income`` exactly for the same scope/window — the
    two are independently computed (a pure tx scan vs. an engine-result-derived
    accumulator) so this reconciliation is a real cross-check, not a tautology.
    """

    @pytest.mark.asyncio
    async def test_golden_scenario_reconciles_with_summary_period_income(self, session, test_user, broker_with_access):
        """DEPOSIT 1000 (day1, not income); DIVIDEND 50 (day10); DIVIDEND -20 (day15,
        a legacy correction); INTEREST 5 (day20) — all broker-level (asset_id=None).

        Expected points: 3 sparse entries (day1 is a DEPOSIT, never a point).
        sum(dividend)+sum(interest) = 50 + (-20) + 5 = 35, and this MUST equal
        get_summary()'s period_income for the identical (date_from=None,
        date_to=2025-01-31] window.
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2025, 1, 1), amount=Decimal("1000"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 1, 10), amount=Decimal("50"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 1, 15), amount=Decimal("-20"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2025, 1, 20), amount=Decimal("5"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        history = await service.get_income_history(user_id=test_user.id, date_from=None, date_to=date(2025, 1, 31))

        assert [p.date for p in history.points] == [date(2025, 1, 10), date(2025, 1, 15), date(2025, 1, 20)], "sparse: no point for the DEPOSIT-only day1"
        by_date = {p.date: p for p in history.points}
        assert by_date[date(2025, 1, 10)].dividend.amount == Decimal("50")
        assert by_date[date(2025, 1, 10)].interest.amount == Decimal("0")
        assert by_date[date(2025, 1, 15)].dividend.amount == Decimal("-20"), "legacy negative correction must be signed, never abs()'d"
        assert by_date[date(2025, 1, 15)].interest.amount == Decimal("0")
        assert by_date[date(2025, 1, 20)].dividend.amount == Decimal("0")
        assert by_date[date(2025, 1, 20)].interest.amount == Decimal("5")
        assert history.missing_fx_pairs == []

        total = sum((p.dividend.amount + p.interest.amount for p in history.points), Decimal("0"))
        assert total == Decimal("35"), f"50 + (-20) + 5 = 35, got {total}"

        summary = await service.get_summary(user_id=test_user.id, date_from=None, date_to=date(2025, 1, 31))
        assert summary.period_income is not None
        assert summary.period_income.amount == Decimal("35"), f"get_summary().period_income must reconcile exactly with the income-history sum, got {summary.period_income.amount}"

        # Third independent cross-check: get_positions_contribution() must also
        # surface this -20 correction (never silently drop it) via its
        # UnallocatedContribution row — all three transactions are broker-level
        # (asset_id=None) and net to the same signed total.
        contribution = await service.get_positions_contribution(user_id=test_user.id, date_from=None, date_to=date(2025, 1, 31))
        unalloc_matches = [u for u in contribution.unallocated if u.broker_id == broker.id]
        assert len(unalloc_matches) == 1, f"expected exactly one unallocated row for this test's broker, got {len(unalloc_matches)}"
        assert unalloc_matches[0].unallocated_income == Decimal("35"), f"get_positions_contribution()'s unallocated_income must also reconcile to 35 (50-20+5), got {unalloc_matches[0].unallocated_income}"

    @pytest.mark.asyncio
    async def test_pure_positive_regression_matches_hand_arithmetic(self, session, test_user, broker_with_access):
        """No correction anywhere — locks in that the ordinary path is numerically
        unaffected, and that same-date DIVIDEND rows from independent transactions
        are grouped/summed into one point (plan: "groups by (date, type)")."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 1), amount=Decimal("30"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 1), amount=Decimal("45"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2025, 2, 15), amount=Decimal("12"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        history = await service.get_income_history(user_id=test_user.id, date_from=None, date_to=date(2025, 2, 28))

        assert [p.date for p in history.points] == [date(2025, 2, 1), date(2025, 2, 15)]
        by_date = {p.date: p for p in history.points}
        assert by_date[date(2025, 2, 1)].dividend.amount == Decimal("75"), "30 + 45 = 75, two same-date DIVIDEND rows grouped into one point"
        assert by_date[date(2025, 2, 15)].interest.amount == Decimal("12")
        assert history.missing_fx_pairs == []

    @pytest.mark.asyncio
    async def test_date_from_boundary_is_exclusive_start_inclusive_end(self, session, test_user, broker_with_access):
        """Canonical (date_from, date_to] boundary: a transaction dated exactly on
        date_from is excluded; one dated on date_to is included."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 5), amount=Decimal("11"), currency="EUR"),  # == date_from -> excluded
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 6), amount=Decimal("22"), currency="EUR"),  # inside window
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 10), amount=Decimal("33"), currency="EUR"),  # == date_to -> included
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        history = await service.get_income_history(user_id=test_user.id, date_from=date(2025, 3, 5), date_to=date(2025, 3, 10))

        assert [p.date for p in history.points] == [date(2025, 3, 6), date(2025, 3, 10)], "date_from itself excluded, date_to included"

    @pytest.mark.asyncio
    async def test_missing_fx_pair_excluded_from_sums_never_zeroed(self, session, test_user, broker_with_access):
        """A DIVIDEND/INTEREST in a currency with no configured FX rate/route must be
        excluded from the sums (not silently substituted with 0) and its pair
        reported in missing_fx_pairs — while OTHER same-date/other-date transactions
        still contribute normally.

        PGK (Papua New Guinea Kina) is used deliberately: not one of this codebase's
        configured mock FX pairs (EUR/USD, GBP/EUR, USD/CHF — see populate_mock_data.py
        and TestPortfolioFxCacheIdentity's own choice of obscure pairs for the same
        reason), so "this conversion genuinely has no rate" is true by construction.
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 5, 1), amount=Decimal("100"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 5, 1), amount=Decimal("500"), currency="PGK"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2025, 5, 10), amount=Decimal("200"), currency="PGK"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        history = await service.get_income_history(user_id=test_user.id, date_from=None, date_to=date(2025, 5, 31))

        assert history.missing_fx_pairs == ["PGK/EUR"], "deduplicated despite 2 failed PGK conversions"
        # day 1: the EUR dividend still contributes; the PGK one is excluded, not zeroed into it.
        # day 10: its ONLY transaction failed conversion -> the whole date is omitted (sparse), not a zero point.
        assert [p.date for p in history.points] == [date(2025, 5, 1)]
        assert history.points[0].dividend.amount == Decimal("100")
        assert history.points[0].interest.amount == Decimal("0")


# =============================================================================
# G1c — get_positions_contribution(): signed accumulation + positive-only filter fixes
# =============================================================================


class TestPositionsContributionSignedIncome:
    """The 3 independent per-plan filter fixes in get_positions_contribution()
    (plan §4.4): a legacy negative-only DIVIDEND/INTEREST correction must still
    surface — never be silently dropped by a stale `> 0` / `<= 0` gate that
    predates signed income. FEE/TAX `> 0` gates are explicitly unchanged
    (out of scope) and are not touched by these tests.
    """

    @pytest.mark.asyncio
    async def test_asset_linked_negative_net_income_surfaces_as_position_row(self, session, test_user, test_asset, broker_with_access):
        """Asset with DIVIDEND activity only (no BUY/SELL ever) netting to a
        NEGATIVE income total. Regression lock for two of the five fixes:
        - `if income == 0 and fees == 0: continue` (was `<= 0`): income=-40 would
          have been wrongly dropped by the old `<= 0` gate (income<=0 AND fees<=0
          both true for a pure negative correction).
        - `period_income=income if income else None` (was `income if income > 0
          else None`): -40 would have rendered as None (no income at all) instead
          of a visible negative correction.
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 1), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=broker.id, asset_id=test_asset.id, type=TransactionType.DIVIDEND, date=date(2025, 2, 5), amount=Decimal("-50"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        contribution = await service.get_positions_contribution(user_id=test_user.id, date_from=date(2025, 1, 31), date_to=date(2025, 2, 28))

        matches = [p for p in contribution.positions if p.broker_id == broker.id and p.asset_id == test_asset.id]
        assert len(matches) == 1, f"expected exactly one position row for this test's (broker, asset), got {len(matches)}"
        row = matches[0]
        assert row.period_income == Decimal("-40"), f"10 + (-50) = -40, got {row.period_income}"
        assert row.period_pnl == Decimal("-40"), "income(-40) - fees(0) = -40"
        assert row.is_fully_sold is True
        assert not any(u.broker_id == broker.id for u in contribution.unallocated), "asset-linked income must never leak into UnallocatedContribution"

    @pytest.mark.asyncio
    async def test_unallocated_negative_net_income_surfaces_not_dropped(self, session, test_user, broker_with_access):
        """Broker-level (asset_id=None) DIVIDEND activity netting to a NEGATIVE
        total. Regression lock for the remaining three of the five fixes:
        - `if inc or (fee and fee > 0):` (was `if (inc and inc > 0) or (fee and fee > 0):`)
        - `unallocated_income=inc if inc else None` (was `inc if inc and inc > 0 else None`)
        - the "Unallocated income" other_effects entry's `if inc:` (was `if inc and inc > 0:`)
        A pure `inc=-40, fee=0` broker would have been excluded from `unallocated`
        (and its `other_effects` row) entirely under the old all-positive gates.
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 1), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2025, 3, 5), amount=Decimal("-50"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        contribution = await service.get_positions_contribution(user_id=test_user.id, date_from=date(2025, 2, 28), date_to=date(2025, 3, 31))

        unalloc_matches = [u for u in contribution.unallocated if u.broker_id == broker.id]
        assert len(unalloc_matches) == 1, f"expected exactly one unallocated row for this test's broker, got {len(unalloc_matches)}"
        unalloc = unalloc_matches[0]
        assert unalloc.unallocated_income == Decimal("-40"), f"10 + (-50) = -40, got {unalloc.unallocated_income}"
        assert unalloc.unallocated_fees_taxes is None

        income_effects = [e for e in contribution.other_effects if e.broker_id == broker.id and e.category == "Income"]
        assert len(income_effects) == 1, f"expected exactly one 'Unallocated income' other_effects row for this test's broker, got {len(income_effects)}"
        assert income_effects[0].period_pnl == Decimal("-40")
        assert income_effects[0].description == "Unallocated income"

    @pytest.mark.asyncio
    async def test_fee_only_positive_gates_are_unchanged(self, session, test_user, broker_with_access):
        """Guard against scope creep: FEE/TAX `> 0` comparisons were deliberately
        left untouched by this plan. A broker with FEE only (no income at all)
        must behave exactly as before — fees are always accumulated via abs(), so
        they can never be negative, and the row must still surface normally."""
        broker, _ = broker_with_access
        session.add(
            Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2025, 6, 1), amount=Decimal("-15"), currency="EUR"),
        )
        await session.flush()

        service = PortfolioService(session)
        contribution = await service.get_positions_contribution(user_id=test_user.id, date_from=date(2025, 5, 31), date_to=date(2025, 6, 30))

        unalloc_matches = [u for u in contribution.unallocated if u.broker_id == broker.id]
        assert len(unalloc_matches) == 1
        assert unalloc_matches[0].unallocated_fees_taxes == Decimal("15"), "FEE is reported as a positive magnitude, unaffected by the signed-income fix"
        assert unalloc_matches[0].unallocated_income is None
        cost_effects = [e for e in contribution.other_effects if e.broker_id == broker.id and e.category == "Cost"]
        assert len(cost_effects) == 1
        assert cost_effects[0].period_pnl == Decimal("-15")


# =============================================================================
# BATCH 2 — SHARED SIGNED TRANSACTION SCAN (_signed_transaction_sums_by_date)
# =============================================================================
#
# get_income_history's original body was extracted into the private
# _signed_transaction_sums_by_date and is now shared by three public methods that
# differ only in which tx_types they scan and how they combine the per-type sums:
#
#   get_income_history   DIVIDEND/INTEREST kept separate
#   get_cost_history     FEE+TAX summed into ONE signed "cost"
#   get_deposit_history  DEPOSIT alone
#
# The three behaviours that live IN the shared scan — FX-missing tracking, F2
# OWNER-share scaling, and the canonical (date_from, date_to] boundary — are
# therefore worth exercising through the NEW callers rather than through the
# private helper directly: the helper is an implementation detail, while "a FEE in
# an unconvertible currency must not silently become a zero cost" is the contract a
# consumer actually depends on. get_income_history's own coverage of the same three
# (TestGetIncomeHistory above) is left untouched and must keep passing verbatim —
# that IS the refactor's regression gate.


async def _make_scan_broker(session, user: User, role: str, share: Decimal | None) -> Broker:
    """One broker with one access row of the given role/share, no transactions.

    Mirrors TestRoleAwareShareScaling._make_broker_with_role, minus its DEPOSIT (which
    would land inside get_deposit_history's own subject matter and confuse the numbers).
    """
    broker = Broker(name=f"PfBroker_Scan_{role}_{share}_{utcnow().timestamp()}")
    session.add(broker)
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=role, share_percentage=share))
    await session.flush()
    return broker


class TestGetCostHistory:
    """PortfolioService.get_cost_history() — signed FEE+TAX, combined per date."""

    @pytest.mark.asyncio
    async def test_fee_and_tax_are_summed_into_one_signed_cost_per_date(self, session, test_user, broker_with_access):
        """The dimension is "Fees & taxes", one figure — a FEE and a TAX on the same
        date collapse into a single point, not two. And the sign is the RAW
        Transaction.amount sign: costs stay negative, they are never flipped to a
        positive magnitude (unlike get_positions_contribution's unallocated_fees_taxes,
        which reports a magnitude by design — the two conventions coexist deliberately).
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 1, 10), amount=Decimal("-12"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.TAX, date=date(2026, 1, 10), amount=Decimal("-30"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 1, 20), amount=Decimal("-5"), currency="EUR"),
                # A DIVIDEND on a cost date must not leak in — the scan is tx_type-filtered.
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2026, 1, 20), amount=Decimal("99"), currency="EUR"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, date_from=None, date_to=date(2026, 1, 31))

        assert [p.date for p in history.points] == [date(2026, 1, 10), date(2026, 1, 20)], "one point per date, FEE+TAX merged"
        by_date = {p.date: p for p in history.points}
        assert by_date[date(2026, 1, 10)].cost.amount == Decimal("-42"), f"-12 (FEE) + -30 (TAX) = -42, got {by_date[date(2026, 1, 10)].cost.amount}"
        assert by_date[date(2026, 1, 20)].cost.amount == Decimal("-5"), "the same-date DIVIDEND must not contribute"
        assert history.missing_fx_pairs == []

    @pytest.mark.asyncio
    async def test_positive_fee_correction_keeps_its_sign(self, session, test_user, broker_with_access):
        """Signed fidelity runs both ways: a legacy positive FEE row (a refund/correction)
        must be reported as positive and net against the same date's negative rows, never
        abs()'d into another -N."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 2, 5), amount=Decimal("-40"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 2, 5), amount=Decimal("15"), currency="EUR"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, date_from=None, date_to=date(2026, 2, 28))

        assert [p.date for p in history.points] == [date(2026, 2, 5)]
        assert history.points[0].cost.amount == Decimal("-25"), "-40 + 15 = -25; an abs()-based scan would have produced -55"

    @pytest.mark.asyncio
    async def test_date_boundary_is_exclusive_start_inclusive_end(self, session, test_user, broker_with_access):
        """The canonical (date_from, date_to] window, inherited from the shared scan."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 3, 5), amount=Decimal("-11"), currency="EUR"),  # == date_from -> excluded
                Transaction(broker_id=broker.id, type=TransactionType.TAX, date=date(2026, 3, 6), amount=Decimal("-22"), currency="EUR"),  # inside
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 3, 10), amount=Decimal("-33"), currency="EUR"),  # == date_to -> included
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 3, 11), amount=Decimal("-44"), currency="EUR"),  # after date_to -> excluded
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, date_from=date(2026, 3, 5), date_to=date(2026, 3, 10))

        assert [p.date for p in history.points] == [date(2026, 3, 6), date(2026, 3, 10)], "date_from itself excluded, date_to included"
        assert sum(p.cost.amount for p in history.points) == Decimal("-55")

    @pytest.mark.asyncio
    async def test_missing_fx_pair_excluded_from_sums_never_zeroed(self, session, test_user, broker_with_access):
        """Same contract as income: an unconvertible cost is EXCLUDED and its pair
        reported, rather than silently contributing 0 — a zeroed cost would read as
        "this day was free", which is a different and wrong statement.

        PGK (Papua New Guinea Kina) is deliberately not one of this codebase's configured
        mock FX pairs, same choice and same reason as TestGetIncomeHistory's own FX test.
        """
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 4, 1), amount=Decimal("-10"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.TAX, date=date(2026, 4, 1), amount=Decimal("-500"), currency="PGK"),
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 4, 10), amount=Decimal("-200"), currency="PGK"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, date_from=None, date_to=date(2026, 4, 30))

        assert history.missing_fx_pairs == ["PGK/EUR"], "deduplicated despite 2 failed PGK conversions"
        assert [p.date for p in history.points] == [date(2026, 4, 1)], "04-10's only row failed conversion -> the whole date is omitted, not zeroed"
        assert history.points[0].cost.amount == Decimal("-10"), "the EUR fee still contributes in full"

    @pytest.mark.asyncio
    async def test_scales_by_owner_share_and_never_by_role(self, session, test_user):
        """F2, inherited from the shared scan: a 30%-OWNER broker's costs are scaled
        exactly once, while an EDITOR broker's costs are full despite the schema-mandated
        share_percentage=0 that its role carries."""
        owner_broker = await _make_scan_broker(session, test_user, "OWNER", Decimal("0.3"))
        editor_broker = await _make_scan_broker(session, test_user, "EDITOR", Decimal("0"))
        session.add_all(
            [
                Transaction(broker_id=owner_broker.id, type=TransactionType.FEE, date=date(2026, 5, 10), amount=Decimal("-100"), currency="EUR"),
                Transaction(broker_id=editor_broker.id, type=TransactionType.TAX, date=date(2026, 5, 10), amount=Decimal("-40"), currency="EUR"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, date_from=None, date_to=date(2026, 5, 31))

        assert [p.date for p in history.points] == [date(2026, 5, 10)], "both brokers' costs land on one date -> one grouped point"
        assert history.points[0].cost.amount == Decimal("-70"), f"-30 (30% of -100) + -40 (full EDITOR) = -70, got {history.points[0].cost.amount}"

    @pytest.mark.asyncio
    async def test_zero_share_owner_contributes_nothing_but_the_date_still_reports(self, session, test_user):
        """A 0%-OWNER is a valid configuration (F2), and 0 * -100 = 0 is a genuine
        zero, not a missing value. The scan writes the date key either way, so the point
        exists with amount 0 — distinguishable from the FX-missing case above, which
        omits the date entirely."""
        broker = await _make_scan_broker(session, test_user, "OWNER", Decimal("0"))
        session.add(Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 6, 1), amount=Decimal("-100"), currency="EUR"))
        await session.flush()

        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, broker_ids=[broker.id], date_from=None, date_to=date(2026, 6, 30))

        assert [p.date for p in history.points] == [date(2026, 6, 1)]
        assert history.points[0].cost.amount == Decimal("0")

    @pytest.mark.asyncio
    async def test_user_with_no_broker_access_gets_an_empty_series(self, session, test_user):
        """The early return before the scan even runs."""
        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, broker_ids=[999999])

        assert history.points == []
        assert history.missing_fx_pairs == []


class TestGetDepositHistory:
    """PortfolioService.get_deposit_history() — the third caller of the shared scan."""

    @pytest.mark.asyncio
    async def test_same_date_deposits_are_grouped_and_other_types_excluded(self, session, test_user, broker_with_access):
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 7, 1), amount=Decimal("1000"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 7, 1), amount=Decimal("250"), currency="EUR"),
                # Neither of these is a DEPOSIT: a withdrawal is not a negative deposit here,
                # and the dimension is deliberately "money put in", not net external flow.
                Transaction(broker_id=broker.id, type=TransactionType.WITHDRAWAL, date=date(2026, 7, 1), amount=Decimal("-400"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 7, 15), amount=Decimal("75"), currency="EUR"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_deposit_history(user_id=test_user.id, date_from=None, date_to=date(2026, 7, 31))

        assert [p.date for p in history.points] == [date(2026, 7, 1), date(2026, 7, 15)]
        by_date = {p.date: p for p in history.points}
        assert by_date[date(2026, 7, 1)].deposit.amount == Decimal("1250"), "1000 + 250; the same-date WITHDRAWAL must not net against it"
        assert by_date[date(2026, 7, 15)].deposit.amount == Decimal("75")
        assert history.missing_fx_pairs == []

    @pytest.mark.asyncio
    async def test_date_boundary_is_exclusive_start_inclusive_end(self, session, test_user, broker_with_access):
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 8, 5), amount=Decimal("11"), currency="EUR"),  # == date_from -> excluded
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 8, 6), amount=Decimal("22"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 8, 10), amount=Decimal("33"), currency="EUR"),  # == date_to -> included
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_deposit_history(user_id=test_user.id, date_from=date(2026, 8, 5), date_to=date(2026, 8, 10))

        assert [p.date for p in history.points] == [date(2026, 8, 6), date(2026, 8, 10)]

    @pytest.mark.asyncio
    async def test_missing_fx_pair_excluded_from_sums_never_zeroed(self, session, test_user, broker_with_access):
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 9, 1), amount=Decimal("100"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 9, 1), amount=Decimal("900"), currency="PGK"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_deposit_history(user_id=test_user.id, date_from=None, date_to=date(2026, 9, 30))

        assert history.missing_fx_pairs == ["PGK/EUR"]
        assert [p.date for p in history.points] == [date(2026, 9, 1)]
        assert history.points[0].deposit.amount == Decimal("100"), "the PGK deposit is excluded, never added as 0 or at a 1:1 fallback rate"

    @pytest.mark.asyncio
    async def test_scales_by_owner_share_and_never_by_role(self, session, test_user):
        owner_broker = await _make_scan_broker(session, test_user, "OWNER", Decimal("0.3"))
        editor_broker = await _make_scan_broker(session, test_user, "EDITOR", Decimal("0"))
        session.add_all(
            [
                Transaction(broker_id=owner_broker.id, type=TransactionType.DEPOSIT, date=date(2026, 10, 10), amount=Decimal("1000"), currency="EUR"),
                Transaction(broker_id=editor_broker.id, type=TransactionType.DEPOSIT, date=date(2026, 10, 10), amount=Decimal("40"), currency="EUR"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_deposit_history(user_id=test_user.id, date_from=None, date_to=date(2026, 10, 31))

        assert [p.date for p in history.points] == [date(2026, 10, 10)]
        assert history.points[0].deposit.amount == Decimal("340"), f"300 (30% of 1000) + 40 (full EDITOR) = 340, got {history.points[0].deposit.amount}"

    @pytest.mark.asyncio
    async def test_user_with_no_broker_access_gets_an_empty_series(self, session, test_user):
        history = await PortfolioService(session).get_deposit_history(user_id=test_user.id, broker_ids=[999999])

        assert history.points == []


class TestSharedScanCallersAreIndependent:
    """The three callers pass different tx_types into one shared scan. A regression that
    widened or leaked a type set would be invisible in any single-caller test, so this
    checks the partition on ONE dataset containing every relevant type at once.
    """

    @pytest.mark.asyncio
    async def test_one_dataset_partitions_cleanly_across_income_cost_and_deposit(self, session, test_user, broker_with_access):
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date(2026, 11, 2), amount=Decimal("500"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2026, 11, 2), amount=Decimal("60"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2026, 11, 2), amount=Decimal("7"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.FEE, date=date(2026, 11, 2), amount=Decimal("-3"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.TAX, date=date(2026, 11, 2), amount=Decimal("-9"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.WITHDRAWAL, date=date(2026, 11, 2), amount=Decimal("-50"), currency="EUR"),
            ]
        )
        await session.flush()

        service = PortfolioService(session)
        kwargs = {"user_id": test_user.id, "broker_ids": [broker.id], "date_from": None, "date_to": date(2026, 11, 30)}
        income = await service.get_income_history(**kwargs)
        cost = await service.get_cost_history(**kwargs)
        deposit = await service.get_deposit_history(**kwargs)

        assert income.points[0].dividend.amount == Decimal("60")
        assert income.points[0].interest.amount == Decimal("7"), "INTEREST must not be swallowed by the FEE/TAX caller"
        assert cost.points[0].cost.amount == Decimal("-12"), "-3 + -9; no DIVIDEND/INTEREST/DEPOSIT leakage"
        assert deposit.points[0].deposit.amount == Decimal("500"), "DEPOSIT alone; the WITHDRAWAL is in none of the three"


class TestGetIncomeHistoryRefactorRegression:
    """The refactor's one genuine behavioural surface, not already pinned by
    TestGetIncomeHistory above.

    The ORIGINAL built its date list from ``set(dividend_by_date) | set(interest_by_date)``
    — two defaultdicts written by ``+=``, so a date whose bucket NETS to exactly zero
    still had a key and still produced a point. The refactor collects dates from a single
    ``sums_by_date`` mapping instead. That is equivalent only because the inner
    accumulation is likewise unconditional; a future "skip zero sums" micro-optimisation
    in the shared scan would silently start dropping these days, and every existing income
    test would stay green because none of them nets a bucket to zero.
    """

    @pytest.mark.asyncio
    async def test_a_date_whose_bucket_nets_to_zero_still_emits_a_point(self, session, test_user, broker_with_access):
        """+50 and -50 DIVIDEND on the same date: the day HAPPENED (two real corrections
        cancelling out) and must be reported as a zero, which is a different statement
        from the date being absent (which means "no income activity at all")."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2026, 12, 3), amount=Decimal("50"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2026, 12, 3), amount=Decimal("-50"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2026, 12, 4), amount=Decimal("8"), currency="EUR"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_income_history(user_id=test_user.id, broker_ids=[broker.id], date_from=None, date_to=date(2026, 12, 31))

        assert [p.date for p in history.points] == [date(2026, 12, 3), date(2026, 12, 4)], "the net-zero date must still be a point"
        by_date = {p.date: p for p in history.points}
        assert by_date[date(2026, 12, 3)].dividend.amount == Decimal("0")
        assert by_date[date(2026, 12, 3)].interest.amount == Decimal("0")
        assert by_date[date(2026, 12, 4)].interest.amount == Decimal("8")

    @pytest.mark.asyncio
    async def test_points_stay_sorted_by_date(self, session, test_user, broker_with_access):
        """The original sorted a set of dates; the refactor sorts ``sums_by_date.items()``
        (tuples). Both are date-ordered because keys are unique — but the tuple form would
        attempt to compare the dict values on a tie, so this pins that dates, inserted out
        of order, still come back ascending."""
        broker, _ = broker_with_access
        session.add_all(
            [
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2027, 1, 20), amount=Decimal("3"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.INTEREST, date=date(2027, 1, 2), amount=Decimal("1"), currency="EUR"),
                Transaction(broker_id=broker.id, type=TransactionType.DIVIDEND, date=date(2027, 1, 11), amount=Decimal("2"), currency="EUR"),
            ]
        )
        await session.flush()

        history = await PortfolioService(session).get_income_history(user_id=test_user.id, broker_ids=[broker.id], date_from=None, date_to=date(2027, 1, 31))

        dates = [p.date for p in history.points]
        assert dates == sorted(dates) == [date(2027, 1, 2), date(2027, 1, 11), date(2027, 1, 20)]
