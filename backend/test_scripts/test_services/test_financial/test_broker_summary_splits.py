"""
MF-I2 (workstream MF, lot I2, «one split loader») — the broker summary's average cost across a stock split: a parity pin.

``BrokerService.get_summary`` (``brokers/summary.py``) gives each holding its quantity, its total and average cost
(``_holding_average_costs``: the broker's rows replayed through ``financial_math.average_cost``) and, with a close, its
value and unrealized P&L. An ADJUSTMENT linked to a SPLIT asset event is a split rescale: the pool keeps its cost and
takes the row's own quantity (``cost_movement_from_transaction(split_linked=True)`` → ``CostMovementKind.SPLIT`` →
``CostEffect.SPLIT_RESCALE``). Until MF-I2 ``_holding_average_costs`` found those rows with a join of its own; since
MF-I2 it asks ``financial_math.splits.split_linked_ids``. Nothing tested the summary across a split before this file:
the move must change no figure, and these tests say which figures.

Green on HEAD and after (every figure computed by hand; each close is chosen so that the P&L percent is exact):

- TestForwardSplit — BUY 10 for 1000 EUR; SPLIT 2:1 with a linked ADJUSTMENT +10; close 55: 20 held, total cost 1000
  (preserved), average 50, value 1100, P&L 100, 10.00 %. The same with a cost basis of 100 a unit left on the
  ADJUSTMENT — what the auto cost wrote on split-linked rows before its fix (``test_api/test_portfolio_wac.py``,
  ``TestPortfolioWACSplit``): a split ignores it, where an acquisition would have doubled the cost.
- TestReverseSplit — BUY 30 for 1500 EUR; SPLIT 1:2 with a linked ADJUSTMENT −15; close 110: 15 held, total cost
  1500, average 100, value 1650, P&L 150, 10.00 %.
- TestNotASplit — the controls that give the two above their meaning: the same ADJUSTMENT linked to a
  PRICE_ADJUSTMENT event of the same value, or linked to nothing, is no rescale. +10 without a cost basis is an
  acquisition of unknown cost (no total, no average, no P&L); +10 at 30 a unit adds 300 (1300, 65, P&L −200,
  −15.38 %); −15 is a reduction that takes its share of the cost (15 held, 750, 50, P&L 900, 120.00 %).

Isolation: every test owns its user, broker and asset (unique names) and writes only through a session that is rolled
back: nothing is committed. Everything is in EUR, so no FX rate is read (``compute_average_costs`` asks the FX service
nothing when every amount is already in the asset currency), and the summary keeps no cache. The holding is found by
the test's own asset id on the test's own broker; the summary is read ``as_of`` a fixed day after every row, so the
server's date plays no part.

Reference: backend/app/services/brokers/summary.py (get_summary, _holding_average_costs),
backend/app/services/financial_math/splits.py (split_linked_ids), backend/app/services/financial_math/average_cost.py.
"""

import sys
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

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import BRAssetHolding, BRSummary
from backend.app.schemas.common import Currency
from backend.app.services.brokers.broker_service import BrokerService
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
BUY_DAY = date(2024, 3, 1)
SPLIT_DAY = date(2024, 6, 3)  # the asset event and the ADJUSTMENT that realizes it
CLOSE_DAY = date(2024, 6, 28)
AS_OF = date(2024, 6, 30)  # the summary's day: after every row

SPLIT = AssetEventType.SPLIT
PRICE_ADJUSTMENT = AssetEventType.PRICE_ADJUSTMENT


# =============================================================================
# HELPERS
# =============================================================================


@dataclass(frozen=True)
class _Scope:
    """One user owning 100 % of one broker, and the one EUR asset that broker holds."""

    user: User
    broker: Broker
    asset: Asset


async def _persist(session: AsyncSession, *rows: object) -> None:
    """Add and flush ``rows``: never commit."""
    session.add_all(rows)
    await session.flush()


async def _ledger(
    session: AsyncSession,
    label: str,
    *,
    bought: str,
    paid: str,
    adjusted: str,
    event_type: AssetEventType | None,
    ratio: str,
    cost_basis: str | None,
    close: str,
) -> _Scope:
    """BUY ``bought`` units for ``paid`` EUR on BUY_DAY; on SPLIT_DAY an ADJUSTMENT of ``adjusted`` units linked to an
    asset event of ``event_type`` and value ``ratio`` (to nothing when ``event_type`` is None), carrying ``cost_basis``
    EUR a unit or no cost basis; the asset closes at ``close`` on CLOSE_DAY."""
    tag = uuid4().hex[:12]
    user = User(username=f"mfi2_{label}_{tag}", email=f"mfi2_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"MfI2 {label} {tag}")
    asset = Asset(display_name=f"MfI2 {label} {tag}", currency=EUR, asset_type=AssetType.STOCK)
    await _persist(session, user, broker, asset)
    await _persist(session, BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))

    event_id: int | None = None
    if event_type is not None:
        event = AssetEvent(asset_id=asset.id, date=SPLIT_DAY, type=event_type, value=Decimal(ratio), currency=EUR)
        await _persist(session, event)
        event_id = event.id

    price = Decimal(close)
    await _persist(
        session,
        Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal(bought), amount=-Decimal(paid), currency=EUR),
        Transaction(
            broker_id=broker.id,
            asset_id=asset.id,
            asset_event_id=event_id,
            type=TransactionType.ADJUSTMENT,
            date=SPLIT_DAY,
            quantity=Decimal(adjusted),
            amount=Decimal("0"),
            cost_basis_override=None if cost_basis is None else Decimal(cost_basis),
            cost_basis_currency=None if cost_basis is None else EUR,
        ),
        PriceHistory(asset_id=asset.id, date=CLOSE_DAY, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="mf_i2_test"),
    )
    return _Scope(user=user, broker=broker, asset=asset)


async def _summary_holding(session: AsyncSession, scope: _Scope) -> tuple[BRSummary, BRAssetHolding]:
    """The summary of the scope's broker, read by its owner as of AS_OF, and the holding of the scope's asset."""
    summary = await BrokerService(session).get_summary(scope.broker.id, user_id=scope.user.id, as_of=AS_OF)
    assert summary is not None, "the summary of the test's own broker, read by its owner"
    # The broker belongs to the test and holds only the test's asset: one holding by construction.
    assert [holding.asset_id for holding in summary.holdings] == [scope.asset.id], f"holdings {[holding.asset_id for holding in summary.holdings]}, expected only asset {scope.asset.id}"
    return summary, summary.holdings[0]


def _cost_view(holding: BRAssetHolding) -> dict:
    return {
        "quantity": holding.quantity,
        "total_cost": holding.total_cost,
        "average_cost_per_unit": holding.average_cost_per_unit,
        "current_value": holding.current_value,
        "unrealized_pnl": holding.unrealized_pnl,
        "unrealized_pnl_percent": holding.unrealized_pnl_percent,
    }


def _eur(amount: str | None) -> Currency | None:
    return None if amount is None else Currency(code=EUR, amount=Decimal(amount))


def _expected(quantity: str, total_cost: str | None, average: str | None, value: str, pnl: str | None, percent: str | None) -> dict:
    """The cost view a holding must show, every amount in EUR; None where the cost is unknown."""
    return {
        "quantity": Decimal(quantity),
        "total_cost": _eur(total_cost),
        "average_cost_per_unit": None if average is None else Decimal(average),
        "current_value": _eur(value),
        "unrealized_pnl": _eur(pnl),
        "unrealized_pnl_percent": None if percent is None else Decimal(percent),
    }


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


# =============================================================================
# Green on HEAD and after: a split rescales the pool, its cost preserved
# =============================================================================


class TestForwardSplit:
    """BUY 10 for 1000 EUR (100 a unit); SPLIT 2:1 on SPLIT_DAY, realized by an ADJUSTMENT +10; close 55."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "cost_basis",
        [
            pytest.param(None, id="no-cost-basis"),
            # An acquisition at 100 a unit would add 1000: 2000 for 20, average 100.
            pytest.param("100", id="a-stale-cost-basis-is-ignored"),
        ],
    )
    async def test_a_forward_split_doubles_the_quantity_and_halves_the_average_cost(self, session, cost_basis):
        """20 held at a total cost of 1000, preserved: average 1000 / 20 = 50; value 20 × 55 = 1100, P&L 100, 100 / 1000 → 10.00 %."""
        print_section(f"MF-I2 broker summary: forward split, cost basis {cost_basis}")
        scope = await _ledger(session, "fwd", bought="10", paid="1000", adjusted="10", event_type=SPLIT, ratio="2", cost_basis=cost_basis, close="55")

        summary, holding = await _summary_holding(session, scope)

        assert _cost_view(holding) == _expected("20", "1000", "50", "1100", "100", "10.00")
        assert summary.missing_fx_pairs == []
        print_success("10 @ 100 → 20 @ 50, total cost 1000 preserved")


class TestReverseSplit:
    """BUY 30 for 1500 EUR (50 a unit); SPLIT 1:2 on SPLIT_DAY, realized by an ADJUSTMENT −15; close 110."""

    @pytest.mark.asyncio
    async def test_a_reverse_split_halves_the_quantity_and_doubles_the_average_cost(self, session):
        """15 held at a total cost of 1500, preserved: average 1500 / 15 = 100; value 15 × 110 = 1650, P&L 150, 150 / 1500 → 10.00 %."""
        print_section("MF-I2 broker summary: reverse split")
        scope = await _ledger(session, "rev", bought="30", paid="1500", adjusted="-15", event_type=SPLIT, ratio="0.5", cost_basis=None, close="110")

        summary, holding = await _summary_holding(session, scope)

        assert _cost_view(holding) == _expected("15", "1500", "100", "1650", "150", "10.00")
        assert summary.missing_fx_pairs == []
        print_success("30 @ 50 → 15 @ 100, total cost 1500 preserved")


# =============================================================================
# Green on HEAD and after: the same ADJUSTMENT, not linked to a SPLIT, is no rescale
# =============================================================================

NOT_A_SPLIT_LINK = [
    # Same asset, date and value as the split, only the type of the event differs.
    pytest.param(PRICE_ADJUSTMENT, id="linked-to-a-price-adjustment"),
    pytest.param(None, id="unlinked"),
]


class TestNotASplit:
    """The controls of the two classes above: the same ledgers, the ADJUSTMENT linked to a non-SPLIT event or to nothing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("event_type", NOT_A_SPLIT_LINK)
    @pytest.mark.parametrize(
        ("cost_basis", "expected"),
        [
            # 10 bought + 10 of unknown cost: the cost of the 20 held is not known, so neither is the P&L.
            pytest.param(None, (None, None, None, None), id="no-cost-basis-is-an-unknown-cost"),
            # 1000 + 10 × 30 = 1300 for 20: average 65; 1100 − 1300 = −200, −200 / 1300 = −15.384… → −15.38 %.
            pytest.param("30", ("1300", "65", "-200", "-15.38"), id="cost-basis-30-is-an-acquisition"),
        ],
    )
    async def test_a_positive_adjustment_not_linked_to_a_split_is_an_acquisition(self, session, event_type, cost_basis, expected):
        """BUY 10 for 1000, ADJUSTMENT +10, close 55: 20 held and worth 1100 as after the split, but its cost is not 1000."""
        print_section(f"MF-I2 broker summary: +10 linked to {event_type}, cost basis {cost_basis}")
        scope = await _ledger(session, "acq", bought="10", paid="1000", adjusted="10", event_type=event_type, ratio="2", cost_basis=cost_basis, close="55")

        summary, holding = await _summary_holding(session, scope)

        total, average, pnl, percent = expected
        assert _cost_view(holding) == _expected("20", total, average, "1100", pnl, percent)
        assert summary.missing_fx_pairs == [], "an unknown cost basis is not a missing rate"
        print_success(f"+10 is an acquisition: total cost {total}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("event_type", NOT_A_SPLIT_LINK)
    async def test_a_negative_adjustment_not_linked_to_a_split_is_a_reduction(self, session, event_type):
        """BUY 30 for 1500, ADJUSTMENT −15, close 110: the 15 removed take 750 with them — 15 held at 750, average 50;
        value 1650, P&L 900, 900 / 750 → 120.00 %."""
        print_section(f"MF-I2 broker summary: −15 linked to {event_type}")
        scope = await _ledger(session, "red", bought="30", paid="1500", adjusted="-15", event_type=event_type, ratio="0.5", cost_basis=None, close="110")

        summary, holding = await _summary_holding(session, scope)

        assert _cost_view(holding) == _expected("15", "750", "50", "1650", "900", "120.00")
        assert summary.missing_fx_pairs == []
        print_success("−15 is a reduction: total cost halved to 750")
