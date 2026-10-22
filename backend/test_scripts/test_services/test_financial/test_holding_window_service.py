"""
MF-H (workstream MF, lot H) — the holding window on the Dashboard: a stock split keeps the date of the lots it rescales.

Two figures read the holding window of a position at one broker, its quantity stream (BUY, SELL, ADJUSTMENT,
TRANSFER) replayed FIFO:

* ``PortfolioService.get_summary``: each holding's ``oldest_open_lot_date``;
* ``PortfolioService.get_positions_contribution``: each row's ``oldest_open_lot_date``, and its ``annualized_return``
  over ``max(date_from, oldest open lot) → date_to``; a fully sold row annualizes its realized return over its
  closed-position window (first opening → last close).

Since MF-H both come from ``financial_math.holding_window``, where the ADJUSTMENT linked to a SPLIT asset event
rescales every open lot and keeps their dates. Before MF-H (HEAD 45ae068cc) ``portfolio_service._oldest_open_lot_date``
read that ADJUSTMENT as any other: a forward split's +q opened a lot dated at the split, a reverse split's −q consumed
the oldest lots.

Every scenario: one user owning its brokers — 100 % but in MF-A10's co-owned cases — and one EUR asset, bought on BUY_DAY = 2024-03-01, closes on
AS_OF = 2024-12-31, the Dashboard read in EUR as of AS_OF over a period from PERIOD_FROM = 2024-01-01 (before any
row, so the window starts at the oldest open lot: AS_OF − BUY_DAY = 305 days, AS_OF − MIDDLE_DAY = 211).

Red on HEAD, green after:

- TestForwardSplit — BUY 10 for 1000, SPLIT 2:1 on MIDDLE_DAY (2024-06-03, ADJUSTMENT +10), SELL 15 for 900 on
  LATE_DAY (2024-09-02), close 70: 5 held at a cost of 250 (the split keeps the cost: 50 a unit), worth 350. The
  open lot is the BUY's: BUY_DAY. HEAD: MIDDLE_DAY, the split's own lot. The row's annualized return is
  (1 + 250 / 250)^(365 / 305) − 1 (P&L 100 unrealized + 150 realized over the end cost); HEAD ran it over 211 days;
- TestReverseSplit — BUY 10 for 1000 on BUY_DAY, BUY 10 for 1200 on MIDDLE_DAY, SPLIT 1:2 on LATE_DAY (ADJUSTMENT
  −10), close 250: 10 held, lots of 5 and 5, at a cost of 2200, worth 2500. The oldest lot is BUY_DAY's. HEAD:
  MIDDLE_DAY (the −10 consumed the first BUY). Annualized: (1 + 0.1364)^(365 / 305) − 1, with
  300 / 2200 = 0.13636… rounded to 0.1364 as the service rounds it; HEAD: over 211 days.

Green on HEAD and after:

- TestSplitThenFullSale — BUY 10 for 1000, SPLIT 2:1 (ADJUSTMENT +10) on MIDDLE_DAY, SELL 20 for 1200 on LATE_DAY:
  nothing open; the closed-position window is BUY_DAY → LATE_DAY (185 days) for a realized 200 on a deployed 1000;
- TestNotASplit — the control of TestForwardSplit: the same +10 linked to a PRICE_ADJUSTMENT event (cost basis 50 a
  unit) is an acquisition, so it opens a lot of MIDDLE_DAY and the SELL 15 empties BUY_DAY's: MIDDLE_DAY either way;
- TestTransferIn — D-MF2 (a): 10 bought at broker A on BUY_DAY leave on MIDDLE_DAY and reach broker B on
  ARRIVAL_DAY (2024-06-07, a linked TRANSFER pair): at B the oldest open lot is ARRIVAL_DAY, in both views.

MF-A7 — ``holding_window.oldest_open_lot_date`` sets aside the oldest lots that together hold the dust threshold
(0.00001) or less, the residual a sale leaves, as ``closed_position_window`` and the rows already count it as not held.
Before it (HEAD 5726486bc) the first open lot counted whatever its quantity. TestDustResidual, every amount at 100 a
unit so that no sale realizes anything, the close 120:

- red on HEAD: BUY 10 for 1000 (BUY_DAY), SELL 9.999999 for 999.9999 (MIDDLE_DAY), BUY 5 for 500 (LATE_DAY) — the
  holding and the row date from LATE_DAY (HEAD: BUY_DAY, the 0.000001 left of the first BUY), and the row annualizes
  its 100.00002 over the end cost 500.0001 (0.2000) over LATE_DAY → AS_OF (120 days), not 305; BUY 10 for 1000, SELL
  9.999999 for 1199.99988 (LATE_DAY): the row is fully sold and has no open lot (HEAD: BUY_DAY); the fallback window
  (J): 10 held since EARLY_DAY (2023-06-01, worth 1200 at PERIOD_FROM), 10 bought on BUY_DAY, an ADJUSTMENT −19.999999
  without a cost (LATE_DAY) — no base for the closed-position rule, so the general rule annualizes −200 / 1200 over the
  whole period, not from BUY_DAY, the date of the residual's lot;
- green on HEAD too: the dust-closed row still annualizes its 0.2000 over its flight time BUY_DAY → LATE_DAY; a SELL
  9.99998 leaves 0.00002, more than dust: BUY_DAY in both views and an annualized return over 305 days.

MF-A10 — ``holding_window.quantity_moves`` scales each quantity by the owner's share of the broker
(``native_cash.effective_share``), and both callers pass it: the windows read the engine's quantity, the one the rows
test against the dust threshold (``daily_state``: ``tx.quantity × share``). Before it (HEAD ab74aafbf) they read the raw
quantity: on a broker owned at s < 1 a residual in (dust, dust / s] was dust for the row and an open lot for the window.
TestCoOwnedBrokerShare, a broker the user owns at 50 % (``share_percentage`` 0.5, a fraction), SELL 9.999988 of 10:
0.000012 left, 0.000006 for the owner:

- red on HEAD: SELL at cost (MIDDLE_DAY), BUY 5 (LATE_DAY) — the holding and the row date from LATE_DAY (HEAD:
  BUY_DAY), the row's 0.2000 (50.00012 over 250.0006) over 120 days, 0.741177 (HEAD: over 305 days, 0.243821); SELL at
  120 (LATE_DAY), nothing after — fully sold on HEAD too, the closed rule now over its flight time BUY_DAY → LATE_DAY:
  99.99988 on the cost sold at the share 499.9994, 0.2000 over 185 days (HEAD: None, the general rule had no base);
  the same sale of 10 held since EARLY_DAY (start value 550) — the closed rule, 0.1000 over PERIOD_FROM → LATE_DAY
  (HEAD: the general rule, 0.0909 on the start value over 365 days);
- green on HEAD too: the same ledgers with the whole broker counted (an owner at 100 %, an editor) keep BUY_DAY's lot;
  at 50 % a SELL 9.99997 leaves 0.000015 for the owner, more than dust — BUY_DAY in both views, 305 days.

Isolation: every test owns its user, brokers and asset (unique names) and writes only through a session that is
rolled back: nothing is committed. Every amount is in EUR and read in EUR (``target_currency_override``), so no FX
rate reaches the figures. The report, WAC and engine blob caches are emptied around each test. Rows are found by the
test's own (broker id, asset id).

Reference: backend/app/services/portfolio_service.py (get_summary, get_positions_contribution),
backend/app/services/financial_math/holding_window.py.
"""

import sys
from dataclasses import dataclass
from datetime import date, timedelta
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
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import AssetPeriodContribution, PortfolioHolding
from backend.app.services.financial_math.returns import cumulative_to_annualized
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
EARLY_DAY = date(2023, 6, 1)  # before the period: a position held at its start (MF-A7's fallback window)
PERIOD_FROM = date(2024, 1, 1)  # before every other row: the window starts at the oldest open lot
BUY_DAY = date(2024, 3, 1)
MIDDLE_DAY = date(2024, 6, 3)
ARRIVAL_DAY = date(2024, 6, 7)
LATE_DAY = date(2024, 9, 2)
AS_OF = date(2024, 12, 31)

SPLIT = AssetEventType.SPLIT
PRICE_ADJUSTMENT = AssetEventType.PRICE_ADJUSTMENT

# The annualized return's rounding of the period return before annualizing (get_positions_contribution).
RETURN_STEP = Decimal("0.0001")


# =============================================================================
# HELPERS
# =============================================================================


@dataclass(frozen=True)
class _Scope:
    """One user owning its brokers — 100 % unless a test says otherwise — and the one EUR asset they hold."""

    user: User
    brokers: tuple[Broker, ...]
    asset: Asset

    @property
    def broker(self) -> Broker:
        return self.brokers[0]


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


async def _scope(session: AsyncSession, keep_alive: list[object], label: str, *, brokers: int = 1, role: UserRole = UserRole.OWNER, share: str = "1") -> _Scope:
    """The user's access to each broker: ``role`` with ``share_percentage`` = ``share``, a fraction (MF-A10: 0.5 a co-owned broker)."""
    tag = uuid4().hex[:12]
    user = User(username=f"mfh_{label}_{tag}", email=f"mfh_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker_rows = tuple(Broker(name=f"MfH {label} {index} {tag}") for index in range(brokers))
    asset = Asset(display_name=f"MfH {label} {tag}", currency=EUR, asset_type=AssetType.STOCK)
    await _persist(session, keep_alive, user, asset, *broker_rows)
    await _persist(session, keep_alive, *(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=role, share_percentage=Decimal(share)) for broker in broker_rows))
    return _Scope(user=user, brokers=broker_rows, asset=asset)


def _trade(scope: _Scope, kind: TransactionType, day: date, quantity: str, amount: str) -> Transaction:
    """A BUY (amount < 0) or SELL (quantity < 0) at the scope's first broker, in EUR."""
    return Transaction(broker_id=scope.broker.id, asset_id=scope.asset.id, type=kind, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=EUR)


async def _adjustment(session: AsyncSession, keep_alive: list[object], scope: _Scope, day: date, quantity: str, *, event_type: AssetEventType, ratio: str, cost_basis: str | None = None) -> None:
    """An ADJUSTMENT of ``quantity`` at the scope's first broker, linked to an asset event of ``event_type`` and value ``ratio``."""
    event = AssetEvent(asset_id=scope.asset.id, date=day, type=event_type, value=Decimal(ratio), currency=EUR)
    await _persist(session, keep_alive, event)
    await _persist(
        session,
        keep_alive,
        Transaction(
            broker_id=scope.broker.id,
            asset_id=scope.asset.id,
            asset_event_id=event.id,
            type=TransactionType.ADJUSTMENT,
            date=day,
            quantity=Decimal(quantity),
            amount=Decimal("0"),
            cost_basis_override=None if cost_basis is None else Decimal(cost_basis),
            cost_basis_currency=None if cost_basis is None else EUR,
        ),
    )


def _close(scope: _Scope, day: date, close: str) -> PriceHistory:
    price = Decimal(close)
    return PriceHistory(asset_id=scope.asset.id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="mf_h_test")


async def _holding(session: AsyncSession, scope: _Scope, broker: Broker) -> PortfolioHolding:
    """The scope's asset at ``broker`` in the summary as of AS_OF: one row by construction."""
    summary = await PortfolioService(session).get_summary(user_id=scope.user.id, target_currency_override=EUR, date_to=AS_OF)
    rows = [holding for holding in summary.holdings if holding.asset_id == scope.asset.id and holding.broker_id == broker.id]
    assert len(rows) == 1, f"expected one holding of asset {scope.asset.id} at broker {broker.id}, got {[(h.asset_id, h.broker_id) for h in summary.holdings]}"
    return rows[0]


async def _row(session: AsyncSession, scope: _Scope, broker: Broker) -> AssetPeriodContribution:
    """The scope's asset at ``broker`` in the contribution PERIOD_FROM → AS_OF: one row by construction."""
    contribution = await PortfolioService(session).get_positions_contribution(user_id=scope.user.id, target_currency_override=EUR, date_from=PERIOD_FROM, date_to=AS_OF)
    rows = [row for row in contribution.positions if row.asset_id == scope.asset.id and row.broker_id == broker.id]
    assert len(rows) == 1, f"expected one row of asset {scope.asset.id} at broker {broker.id}, got {[(r.asset_id, r.broker_id) for r in contribution.positions]}"
    return rows[0]


def _annualized_from(opened: date, pnl: str, base: str) -> Decimal | None:
    """What the row must show: P&L over the end cost, rounded as the service rounds it, annualized from ``opened`` to AS_OF."""
    return cumulative_to_annualized((Decimal(pnl) / Decimal(base)).quantize(RETURN_STEP), (AS_OF - opened).days)


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
# Red on HEAD: a split keeps the date of the lots it rescales
# =============================================================================


async def _forward_split(session: AsyncSession, keep_alive: list[object], label: str) -> _Scope:
    """BUY 10 for 1000 (BUY_DAY); SPLIT 2:1, ADJUSTMENT +10 (MIDDLE_DAY); SELL 15 for 900 (LATE_DAY); close 70 (AS_OF)."""
    scope = await _scope(session, keep_alive, label)
    await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"))
    await _adjustment(session, keep_alive, scope, MIDDLE_DAY, "10", event_type=SPLIT, ratio="2")
    await _persist(session, keep_alive, _trade(scope, TransactionType.SELL, LATE_DAY, "-15", "900"), _close(scope, AS_OF, "70"))
    return scope


async def _reverse_split(session: AsyncSession, keep_alive: list[object], label: str) -> _Scope:
    """BUY 10 for 1000 (BUY_DAY); BUY 10 for 1200 (MIDDLE_DAY); SPLIT 1:2, ADJUSTMENT −10 (LATE_DAY); close 250 (AS_OF)."""
    scope = await _scope(session, keep_alive, label)
    await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"), _trade(scope, TransactionType.BUY, MIDDLE_DAY, "10", "-1200"))
    await _adjustment(session, keep_alive, scope, LATE_DAY, "-10", event_type=SPLIT, ratio="0.5")
    await _persist(session, keep_alive, _close(scope, AS_OF, "250"))
    return scope


class TestForwardSplit:
    @pytest.mark.asyncio
    async def test_the_holding_dates_from_the_buy(self, session, keep_alive):
        """The 20 units after the split are the BUY's lot; 5 of it are left: BUY_DAY (HEAD: MIDDLE_DAY, the split's lot)."""
        print_section("MF-H summary: forward split, partial sale")
        scope = await _forward_split(session, keep_alive, "fwdsum")

        holding = await _holding(session, scope, scope.broker)

        # The split was read as a split: 5 held at its preserved cost of 250 (50 a unit), worth 5 × 70.
        assert (holding.quantity, holding.current_value, holding.gain_loss) == (Decimal("5"), Decimal("350"), Decimal("100")), "precondition: the ADJUSTMENT must be a split rescale"
        assert holding.oldest_open_lot_date == BUY_DAY, f"HEAD gave {MIDDLE_DAY}, the split's date"
        print_success("oldest open lot: the BUY's date")

    @pytest.mark.asyncio
    async def test_the_contribution_row_annualizes_from_the_buy(self, session, keep_alive):
        """Unrealized 350 − 250 = 100, realized 900 − 15 × 50 = 150: P&L 250 over an end cost of 250, so 1.0000,
        annualized over BUY_DAY → AS_OF (305 days), not MIDDLE_DAY → AS_OF (211, HEAD)."""
        print_section("MF-H contribution: forward split, partial sale")
        scope = await _forward_split(session, keep_alive, "fwdrow")
        expected, head = _annualized_from(BUY_DAY, "250", "250"), _annualized_from(MIDDLE_DAY, "250", "250")
        assert expected is not None and expected != head, "precondition: the two windows must give two annualized returns"

        row = await _row(session, scope, scope.broker)

        assert (row.period_pnl, row.period_realized_gain_loss, row.start_value, row.end_value, row.period_pnl_percent, row.is_fully_sold) == (Decimal("250"), Decimal("150"), Decimal("0"), Decimal("350"), None, False), "precondition: the period the annualized return is computed from"
        assert row.oldest_open_lot_date == BUY_DAY, f"HEAD gave {MIDDLE_DAY}"
        assert row.annualized_return == expected, f"expected {expected} over {(AS_OF - BUY_DAY).days} days; HEAD gave {head} over {(AS_OF - MIDDLE_DAY).days}"
        print_success(f"annualized over {(AS_OF - BUY_DAY).days} days: {row.annualized_return}")


class TestReverseSplit:
    @pytest.mark.asyncio
    async def test_the_holding_dates_from_the_first_buy(self, session, keep_alive):
        """The split halves both lots, 5 of BUY_DAY and 5 of MIDDLE_DAY: BUY_DAY (HEAD: MIDDLE_DAY, the −10 had consumed
        the first BUY)."""
        print_section("MF-H summary: reverse split")
        scope = await _reverse_split(session, keep_alive, "revsum")

        holding = await _holding(session, scope, scope.broker)

        # The split was read as a split: 10 held at the preserved cost of 2200, worth 10 × 250.
        assert (holding.quantity, holding.current_value, holding.gain_loss) == (Decimal("10"), Decimal("2500"), Decimal("300")), "precondition: the ADJUSTMENT must be a split rescale"
        assert holding.oldest_open_lot_date == BUY_DAY, f"HEAD gave {MIDDLE_DAY}, the second BUY's date"
        print_success("oldest open lot: the first BUY's date")

    @pytest.mark.asyncio
    async def test_the_contribution_row_annualizes_from_the_first_buy(self, session, keep_alive):
        """Unrealized 2500 − 2200 = 300 over an end cost of 2200: 0.13636… → 0.1364, annualized over 305 days
        (HEAD: 211)."""
        print_section("MF-H contribution: reverse split")
        scope = await _reverse_split(session, keep_alive, "revrow")
        expected, head = _annualized_from(BUY_DAY, "300", "2200"), _annualized_from(MIDDLE_DAY, "300", "2200")
        assert expected is not None and expected != head, "precondition: the two windows must give two annualized returns"

        row = await _row(session, scope, scope.broker)

        assert (row.period_pnl, row.period_realized_gain_loss, row.start_value, row.end_value, row.period_pnl_percent, row.is_fully_sold) == (Decimal("300"), None, Decimal("0"), Decimal("2500"), None, False), "precondition: the period the annualized return is computed from"
        assert row.oldest_open_lot_date == BUY_DAY, f"HEAD gave {MIDDLE_DAY}"
        assert row.annualized_return == expected, f"expected {expected} over {(AS_OF - BUY_DAY).days} days; HEAD gave {head} over {(AS_OF - MIDDLE_DAY).days}"
        print_success(f"annualized over {(AS_OF - BUY_DAY).days} days: {row.annualized_return}")


# =============================================================================
# Green on HEAD and after: a closed position, the non-split control, a transfer-in
# =============================================================================


class TestSplitThenFullSale:
    @pytest.mark.asyncio
    async def test_the_closed_window_runs_from_the_buy_to_the_sale(self, session, keep_alive):
        """BUY 10 for 1000, SPLIT 2:1 (+10), SELL 20 for 1200: realized 200 on a deployed 1000 = 0.2000, annualized
        over BUY_DAY → LATE_DAY (185 days). Nothing open, so no oldest open lot."""
        print_section("MF-H contribution: split then full sale")
        scope = await _scope(session, keep_alive, "closed")
        await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"))
        await _adjustment(session, keep_alive, scope, MIDDLE_DAY, "10", event_type=SPLIT, ratio="2")
        await _persist(session, keep_alive, _trade(scope, TransactionType.SELL, LATE_DAY, "-20", "1200"))
        expected = cumulative_to_annualized(Decimal("0.2000"), (LATE_DAY - BUY_DAY).days)
        assert expected is not None

        row = await _row(session, scope, scope.broker)

        assert (row.period_pnl, row.period_realized_gain_loss, row.is_fully_sold) == (Decimal("200"), Decimal("200"), True), "precondition: a fully sold position with its realized result"
        assert row.oldest_open_lot_date is None
        assert row.annualized_return == expected
        print_success(f"closed window {BUY_DAY} → {LATE_DAY}: {row.annualized_return}")


class TestNotASplit:
    @pytest.mark.asyncio
    async def test_a_plus_ten_linked_to_a_price_adjustment_opens_a_lot(self, session, keep_alive):
        """The forward-split ledger with the ADJUSTMENT +10 (cost basis 50 a unit) linked to a PRICE_ADJUSTMENT event:
        an acquisition, a lot of MIDDLE_DAY; the SELL 15 empties BUY_DAY's lot. MIDDLE_DAY in both views."""
        print_section("MF-H: +10 linked to a PRICE_ADJUSTMENT")
        scope = await _scope(session, keep_alive, "notsplit")
        await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"))
        await _adjustment(session, keep_alive, scope, MIDDLE_DAY, "10", event_type=PRICE_ADJUSTMENT, ratio="2", cost_basis="50")
        await _persist(session, keep_alive, _trade(scope, TransactionType.SELL, LATE_DAY, "-15", "900"), _close(scope, AS_OF, "70"))

        holding = await _holding(session, scope, scope.broker)
        row = await _row(session, scope, scope.broker)

        # 1000 + 10 × 50 = 1500 for 20, 75 a unit: 5 held at 375, worth 350 — not the split's 250.
        assert (holding.quantity, holding.gain_loss) == (Decimal("5"), Decimal("-25")), "precondition: the ADJUSTMENT must be an acquisition"
        assert (holding.oldest_open_lot_date, row.oldest_open_lot_date) == (MIDDLE_DAY, MIDDLE_DAY)
        print_success("not a split: the ADJUSTMENT's own lot")


class TestTransferIn:
    @pytest.mark.asyncio
    async def test_a_transfer_in_dates_at_its_arrival(self, session, keep_alive):
        """10 bought at A on BUY_DAY leave A on MIDDLE_DAY and reach B on ARRIVAL_DAY: B's lot opens on its arrival
        there (D-MF2 (a)), neither on the BUY nor on the departure. Same on HEAD."""
        print_section("MF-H: transfer-in dates at arrival")
        scope = await _scope(session, keep_alive, "transfer", brokers=2)
        broker_a, broker_b = scope.brokers
        departure = Transaction(broker_id=broker_a.id, asset_id=scope.asset.id, type=TransactionType.TRANSFER, date=MIDDLE_DAY, quantity=Decimal("-10"), amount=Decimal("0"))
        arrival = Transaction(broker_id=broker_b.id, asset_id=scope.asset.id, type=TransactionType.TRANSFER, date=ARRIVAL_DAY, quantity=Decimal("10"), amount=Decimal("0"))
        await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"), departure, arrival, _close(scope, AS_OF, "120"))
        # A linked pair references itself both ways: the ids exist only after the first flush.
        departure.related_transaction_id = arrival.id
        arrival.related_transaction_id = departure.id
        await session.flush()

        holding = await _holding(session, scope, broker_b)
        row = await _row(session, scope, broker_b)

        assert (holding.quantity, holding.current_value) == (Decimal("10"), Decimal("1200")), "precondition: the 10 units are at B"
        assert (holding.oldest_open_lot_date, row.oldest_open_lot_date) == (ARRIVAL_DAY, ARRIVAL_DAY)
        print_success("transfer-in: the arrival date")


# =============================================================================
# MF-A7: a dust residual is no open lot
# =============================================================================

DUST_SOLD = "9.999999"  # of 10: 0.000001 left, dust (0.00001 or less)
NOT_DUST_SOLD = "9.99998"  # of 10: 0.00002 left, more than dust


def _sold_at(quantity: str, unit_price: str) -> str:
    return str(Decimal(quantity) * Decimal(unit_price))


async def _residual_then_buy(session: AsyncSession, keep_alive: list[object], label: str, sold: str, *, role: UserRole = UserRole.OWNER, share: str = "1") -> _Scope:
    """BUY 10 for 1000 (BUY_DAY); SELL ``sold`` at cost, 100 a unit (MIDDLE_DAY); BUY 5 for 500 (LATE_DAY); close 120 (AS_OF)."""
    scope = await _scope(session, keep_alive, label, role=role, share=share)
    await _persist(
        session,
        keep_alive,
        _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"),
        _trade(scope, TransactionType.SELL, MIDDLE_DAY, f"-{sold}", _sold_at(sold, "100")),
        _trade(scope, TransactionType.BUY, LATE_DAY, "5", "-500"),
        _close(scope, AS_OF, "120"),
    )
    return scope


async def _dust_closed(session: AsyncSession, keep_alive: list[object], label: str) -> _Scope:
    """BUY 10 for 1000 (BUY_DAY); SELL 9.999999 at 120 a unit, 1199.99988 (LATE_DAY): 0.000001 left."""
    scope = await _scope(session, keep_alive, label)
    await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"), _trade(scope, TransactionType.SELL, LATE_DAY, f"-{DUST_SOLD}", _sold_at(DUST_SOLD, "120")))
    return scope


class TestDustResidual:
    @pytest.mark.asyncio
    async def test_the_holding_dates_from_the_buy_after_the_residual(self, session, keep_alive):
        """The first BUY's lot keeps 0.000001, dust: the oldest lot is LATE_DAY's BUY (HEAD: BUY_DAY, the residual's)."""
        print_section("MF-A7 summary: dust residual, then a BUY")
        scope = await _residual_then_buy(session, keep_alive, "a7dustsum", DUST_SOLD)

        holding = await _holding(session, scope, scope.broker)

        assert holding.quantity == Decimal("5.000001"), "precondition: the residual and the second BUY are held"
        assert holding.oldest_open_lot_date == LATE_DAY, f"HEAD gave {BUY_DAY}, the date of the dust residual's lot"
        print_success("oldest open lot: the BUY after the residual")

    @pytest.mark.asyncio
    async def test_the_row_annualizes_from_the_buy_after_the_residual(self, session, keep_alive):
        """No start value: the end cost 500.0001 is the base of the unrealized 600.00012 − 500.0001 = 100.00002, the
        sale at cost realizes nothing — 0.2000, annualized over LATE_DAY → AS_OF (120 days), not from BUY_DAY (305, HEAD)."""
        print_section("MF-A7 contribution: dust residual, then a BUY")
        scope = await _residual_then_buy(session, keep_alive, "a7dustrow", DUST_SOLD)
        expected, head = _annualized_from(LATE_DAY, "100.00002", "500.0001"), _annualized_from(BUY_DAY, "100.00002", "500.0001")
        assert expected is not None and expected != head, "precondition: the two windows must give two annualized returns"

        row = await _row(session, scope, scope.broker)

        assert (row.period_pnl, row.period_realized_gain_loss, row.start_value, row.end_value, row.is_fully_sold) == (Decimal("100.00002"), None, Decimal("0"), Decimal("600.00012"), False), "precondition: the period the annualized return is computed from"
        assert row.oldest_open_lot_date == LATE_DAY, f"HEAD gave {BUY_DAY}"
        assert row.annualized_return == expected, f"expected {expected} over {(AS_OF - LATE_DAY).days} days; HEAD gave {head} over {(AS_OF - BUY_DAY).days}"
        print_success(f"annualized over {(AS_OF - LATE_DAY).days} days: {row.annualized_return}")

    @pytest.mark.asyncio
    async def test_a_dust_closed_row_has_no_open_lot(self, session, keep_alive):
        """0.000001 left: the row counts it as not held (fully sold), and no lot is open (HEAD: BUY_DAY's)."""
        print_section("MF-A7 contribution: dust-closed row, no open lot")
        scope = await _dust_closed(session, keep_alive, "a7closed")

        row = await _row(session, scope, scope.broker)

        assert (row.is_fully_sold, row.end_value) == (True, Decimal("0")), "precondition: the residual counts as not held"
        assert row.oldest_open_lot_date is None, f"HEAD gave {BUY_DAY}, the residual's lot"
        print_success("dust-closed row: no open lot")

    @pytest.mark.asyncio
    async def test_a_dust_closed_row_annualizes_over_its_flight_time(self, session, keep_alive):
        """The closed-position rule, as on HEAD: realized 1199.99988 − 999.9999 = 199.99998 on the cost sold 999.9999,
        0.2000 over BUY_DAY → LATE_DAY (185 days)."""
        print_section("MF-A7 contribution: dust-closed row, its flight time")
        scope = await _dust_closed(session, keep_alive, "a7flight")
        expected = cumulative_to_annualized(Decimal("0.2000"), (LATE_DAY - BUY_DAY).days)
        assert expected is not None

        row = await _row(session, scope, scope.broker)

        assert (row.period_pnl, row.period_realized_gain_loss, row.is_fully_sold) == (Decimal("199.99998"), Decimal("199.99998"), True), "precondition: a fully sold position with its realized result"
        assert row.annualized_return == expected
        print_success(f"closed window {BUY_DAY} → {LATE_DAY}: {row.annualized_return}")

    @pytest.mark.asyncio
    async def test_a_residual_above_dust_is_still_an_open_lot(self, session, keep_alive):
        """SELL 9.99998: 0.00002 is left of the first BUY, more than dust — BUY_DAY in both views, and the row's 0.2000
        (100.0004 over 500.002) annualized over 305 days. The same on HEAD."""
        print_section("MF-A7: residual above dust")
        scope = await _residual_then_buy(session, keep_alive, "a7notdust", NOT_DUST_SOLD)
        expected = _annualized_from(BUY_DAY, "100.0004", "500.002")

        holding = await _holding(session, scope, scope.broker)
        row = await _row(session, scope, scope.broker)

        assert holding.quantity == Decimal("5.00002"), "precondition: the residual and the second BUY are held"
        assert (holding.oldest_open_lot_date, row.oldest_open_lot_date) == (BUY_DAY, BUY_DAY)
        assert row.annualized_return == expected
        print_success("residual above dust: the first BUY's date")

    @pytest.mark.asyncio
    async def test_a_dust_closed_row_emptied_by_an_adjustment_out_is_a_total_loss_without_annualized_return(self, session, keep_alive):
        """J's case, as N78-1 changed it (the developer's decision, 21/10/2026). 10 held since EARLY_DAY, worth 1200 at
        PERIOD_FROM (cost 1000); BUY 10 for 1000 (BUY_DAY); an ADJUSTMENT −19.999999 without a cost (LATE_DAY) leaves
        0.000001 of the BUY_DAY lot, dust: no lot is open.

        Since N78-1 the exit realizes 0 − its cost, −1999.9999 (decision 3): the row reads P&L −2199.9999 (−200 of the
        start's unrealized gone, −1999.9999 realized), −1.8333 of the start value. The exit now counts as a disposal in the
        closed-position rule — one exit, one disposal —, so its base is the cost given up, 1999.9999: −2199.9999 / 1999.9999
        = −1.1000, a loss beyond the whole base, which ``cumulative_to_annualized`` refuses (≤ −1); the general rule's
        −1.8333 is refused alike. So no annualized return, whatever the window.

        Before N78-1 the exit realized nothing: P&L −200, realized None, no closed-position base, and the general rule
        annualized −0.1667 over the whole period (365 days, the fallback window starting with the period; on MF-A7's HEAD
        from BUY_DAY, 305 days). The fallback window of a dust-closed row is no longer reached by this book: an exit that
        is no counted disposal is needed for it (MF's rule; reported to the coordinator)."""
        print_section("MF-A7 contribution: the fallback window of a dust-closed row")
        scope = await _scope(session, keep_alive, "a7fallback")
        exit_without_cost = Transaction(broker_id=scope.broker.id, asset_id=scope.asset.id, type=TransactionType.ADJUSTMENT, date=LATE_DAY, quantity=Decimal("-19.999999"), amount=Decimal("0"))
        await _persist(
            session,
            keep_alive,
            _trade(scope, TransactionType.BUY, EARLY_DAY, "10", "-1000"),
            _close(scope, PERIOD_FROM, "120"),
            _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"),
            exit_without_cost,
        )
        closed_ratio = (Decimal("-2199.9999") / Decimal("1999.9999")).quantize(RETURN_STEP)
        assert closed_ratio <= Decimal("-1") and cumulative_to_annualized(closed_ratio, (LATE_DAY - BUY_DAY).days) is None, f"precondition: the closed-position ratio {closed_ratio} is a loss beyond its base, which no annualization reads"

        row = await _row(session, scope, scope.broker)

        observed = (row.start_value, row.end_value, row.period_pnl, row.period_realized_gain_loss, row.period_pnl_percent, row.is_fully_sold)
        assert observed == (Decimal("1200"), Decimal("0"), Decimal("-2199.9999"), Decimal("-1999.9999"), Decimal("-1.8333"), True), f"N78-1: the exit realizes 0 − its cost; (start, end, P&L, realized, P&L %, fully sold) = {observed}"
        assert row.oldest_open_lot_date is None, f"HEAD gave {BUY_DAY}"
        assert row.annualized_return is None, f"N78-1: a loss beyond the base has no annualized return; the row gives {row.annualized_return} (before N78-1: −0.1667 over the whole period)"
        print_success("dust-closed by an ADJUSTMENT-out: a total loss, no annualized return")


# =============================================================================
# MF-A10: the windows read the quantity at the owner's share
# =============================================================================

CO_OWNED = "0.5"  # the owner's share of a co-owned broker: BrokerUserAccess.share_percentage is a fraction
SHARE_DUST_SOLD = "9.999988"  # of 10: 0.000012 left, more than dust; 0.000006 at half, dust
SHARE_NOT_DUST_SOLD = "9.99997"  # of 10: 0.00003 left; 0.000015 at half, more than dust either way
# The whole broker counted: an owner at 100 %, or an editor — share 0 recorded, the whole broker seen (effective_share).
WHOLE_BROKER = [pytest.param(UserRole.OWNER, "1", id="owner-100"), pytest.param(UserRole.EDITOR, "0", id="editor")]


async def _sold_down(session: AsyncSession, keep_alive: list[object], label: str, sold: str, *, role: UserRole = UserRole.OWNER, share: str = "1") -> _Scope:
    """BUY 10 for 1000 (BUY_DAY); SELL ``sold`` at 120 a unit (LATE_DAY); close 120 (AS_OF)."""
    scope = await _scope(session, keep_alive, label, role=role, share=share)
    await _persist(
        session,
        keep_alive,
        _trade(scope, TransactionType.BUY, BUY_DAY, "10", "-1000"),
        _trade(scope, TransactionType.SELL, LATE_DAY, f"-{sold}", _sold_at(sold, "120")),
        _close(scope, AS_OF, "120"),
    )
    return scope


class TestCoOwnedBrokerShare:
    """A broker the user owns at 50 %: the engine counts half of every quantity (``daily_state``: ``tx.quantity × share``),
    and so do the windows since MF-A10. HEAD ab74aafbf read the raw quantity: a residual of 0.000012 — 0.000006 for the
    owner — was dust for the row and an open lot for the window."""

    @pytest.mark.asyncio
    async def test_the_holding_dates_from_the_buy_after_a_residual_dust_at_the_share(self, session, keep_alive):
        """BUY 10, SELL 9.999988, BUY 5 at half: 0.000006 left of the first BUY's lot, dust — the oldest lot is LATE_DAY's
        BUY (HEAD: BUY_DAY, the raw 0.000012 more than dust)."""
        print_section("MF-A10 summary: co-owned broker, residual dust at the share")
        scope = await _residual_then_buy(session, keep_alive, "a10sum", SHARE_DUST_SOLD, share=CO_OWNED)

        holding = await _holding(session, scope, scope.broker)

        assert holding.quantity == Decimal("2.500006"), "precondition: the engine holds half of the residual and of the second BUY"
        assert holding.oldest_open_lot_date == LATE_DAY, f"HEAD gave {BUY_DAY}, the date of the lot holding 0.000006 for the owner"
        print_success("oldest open lot: the BUY after the residual")

    @pytest.mark.asyncio
    async def test_the_row_annualizes_from_the_buy_after_a_residual_dust_at_the_share(self, session, keep_alive):
        """The same ledger at half: no start value, so the end cost 250.0006 (0.0006 of the residual, 250 of the BUY) is
        the base of the unrealized 300.00072 − 250.0006 = 50.00012; the sale at cost realizes nothing — 0.2000,
        annualized over LATE_DAY → AS_OF (120 days), not from BUY_DAY (305, HEAD)."""
        print_section("MF-A10 contribution: co-owned broker, residual dust at the share")
        scope = await _residual_then_buy(session, keep_alive, "a10row", SHARE_DUST_SOLD, share=CO_OWNED)
        expected, head = _annualized_from(LATE_DAY, "50.00012", "250.0006"), _annualized_from(BUY_DAY, "50.00012", "250.0006")
        assert expected is not None and expected != head, "precondition: the two windows must give two annualized returns"

        row = await _row(session, scope, scope.broker)

        assert (row.period_pnl, row.period_realized_gain_loss, row.start_value, row.end_value, row.is_fully_sold) == (Decimal("50.00012"), None, Decimal("0"), Decimal("300.00072"), False), "precondition: the period at the owner's share"
        assert row.oldest_open_lot_date == LATE_DAY, f"HEAD gave {BUY_DAY}"
        assert row.annualized_return == expected, f"expected {expected} over {(AS_OF - LATE_DAY).days} days; HEAD gave {head} over {(AS_OF - BUY_DAY).days}"
        print_success(f"annualized over {(AS_OF - LATE_DAY).days} days: {row.annualized_return}")

    @pytest.mark.asyncio
    async def test_a_row_closed_at_dust_over_the_share_annualizes_over_its_flight_time(self, session, keep_alive):
        """BUY 10 for 1000, SELL 9.999988 at 120 at half: 0.000006 left, so the row is fully sold, on HEAD too. Realized
        599.99928 − 499.9994 = 99.99988 on the cost sold at the owner's share, 499.9994 (the engine's): 0.2000 over its
        flight time BUY_DAY → LATE_DAY (185 days). HEAD: the raw 0.000012 never closed the window, so the closed rule gave
        None and the general rule — no start value, no end cost — None."""
        print_section("MF-A10 contribution: co-owned broker, closed at dust over the share")
        scope = await _sold_down(session, keep_alive, "a10closed", SHARE_DUST_SOLD, share=CO_OWNED)
        expected = cumulative_to_annualized((Decimal("99.99988") / Decimal("499.9994")).quantize(RETURN_STEP), (LATE_DAY - BUY_DAY).days)
        assert expected is not None

        row = await _row(session, scope, scope.broker)

        assert (row.period_pnl, row.period_realized_gain_loss, row.start_value, row.end_value, row.is_fully_sold) == (Decimal("99.99988"), Decimal("99.99988"), Decimal("0"), Decimal("0"), True), "precondition: a row fully sold at the owner's share"
        assert row.annualized_return == expected, f"expected {expected} over {(LATE_DAY - BUY_DAY).days} days; HEAD gave None"
        assert row.oldest_open_lot_date is None, f"HEAD gave {BUY_DAY}"
        print_success(f"closed window {BUY_DAY} → {LATE_DAY}: {row.annualized_return}")

    @pytest.mark.asyncio
    async def test_the_closed_rule_replaces_the_general_rule_of_a_row_held_at_the_start(self, session, keep_alive):
        """10 held since EARLY_DAY for 1000, worth 1100 at PERIOD_FROM; SELL 9.999988 at 120 (LATE_DAY). At half: start
        value 550, P&L −50 of unrealized + 99.99988 realized = 49.99988 on the cost sold 499.9994, 0.1000 over
        PERIOD_FROM → LATE_DAY (245 days). HEAD: no close, so the general rule, 49.99988 over the start value 550 =
        0.0909 over the whole period (365 days)."""
        print_section("MF-A10 contribution: co-owned broker, closed rule over the general rule")
        scope = await _scope(session, keep_alive, "a10start", share=CO_OWNED)
        await _persist(
            session,
            keep_alive,
            _trade(scope, TransactionType.BUY, EARLY_DAY, "10", "-1000"),
            _close(scope, PERIOD_FROM, "110"),
            _trade(scope, TransactionType.SELL, LATE_DAY, f"-{SHARE_DUST_SOLD}", _sold_at(SHARE_DUST_SOLD, "120")),
        )
        expected = cumulative_to_annualized((Decimal("49.99988") / Decimal("499.9994")).quantize(RETURN_STEP), (LATE_DAY - PERIOD_FROM).days)
        head = cumulative_to_annualized((Decimal("49.99988") / Decimal("550")).quantize(RETURN_STEP), (AS_OF - PERIOD_FROM).days)
        assert expected is not None and head is not None and expected != head, "precondition: the two rules must give two annualized returns"

        row = await _row(session, scope, scope.broker)

        assert (row.start_value, row.end_value, row.period_pnl, row.period_realized_gain_loss, row.is_fully_sold) == (Decimal("550"), Decimal("0"), Decimal("49.99988"), Decimal("99.99988"), True), "precondition: a row held at the start, fully sold at the owner's share"
        assert row.annualized_return == expected, f"expected {expected} over {(LATE_DAY - PERIOD_FROM).days} days; HEAD gave {head} over {(AS_OF - PERIOD_FROM).days}"
        assert row.oldest_open_lot_date is None, f"HEAD gave {EARLY_DAY}"
        print_success(f"closed window {PERIOD_FROM} → {LATE_DAY}: {row.annualized_return}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role, share", WHOLE_BROKER)
    async def test_the_whole_broker_keeps_the_residual_lot(self, session, keep_alive, role, share):
        """The same ledgers with the whole broker counted: 0.000012 is more than dust, as on HEAD. After BUY 5 the lot of
        BUY_DAY is the oldest, in both views, and the row's 0.2000 (100.00024 over 500.0012) runs over 305 days; with
        nothing bought after the sale the row is still held, its lot BUY_DAY's."""
        print_section(f"MF-A10: the whole broker ({role.value}, share {share})")
        then_buy = await _residual_then_buy(session, keep_alive, "a10whole", SHARE_DUST_SOLD, role=role, share=share)
        sold_down = await _sold_down(session, keep_alive, "a10wholeclosed", SHARE_DUST_SOLD, role=role, share=share)
        expected = _annualized_from(BUY_DAY, "100.00024", "500.0012")

        holding = await _holding(session, then_buy, then_buy.broker)
        row = await _row(session, then_buy, then_buy.broker)
        closed_row = await _row(session, sold_down, sold_down.broker)

        assert (holding.quantity, row.period_pnl, row.is_fully_sold) == (Decimal("5.000012"), Decimal("100.00024"), False), "precondition: the engine counts the whole broker"
        assert (holding.oldest_open_lot_date, row.oldest_open_lot_date) == (BUY_DAY, BUY_DAY)
        assert row.annualized_return == expected
        assert (closed_row.is_fully_sold, closed_row.oldest_open_lot_date) == (False, BUY_DAY)
        print_success("whole broker: the first BUY's lot")

    @pytest.mark.asyncio
    async def test_a_residual_above_dust_at_the_share_is_still_an_open_lot(self, session, keep_alive):
        """SELL 9.99997 at half: 0.000015 is left of the first BUY's lot, more than dust — BUY_DAY in both views, and the
        row's 0.2000 (50.0003 over 250.0015) annualized over 305 days. The same on HEAD."""
        print_section("MF-A10: residual above dust at the share")
        scope = await _residual_then_buy(session, keep_alive, "a10notdust", SHARE_NOT_DUST_SOLD, share=CO_OWNED)
        expected = _annualized_from(BUY_DAY, "50.0003", "250.0015")

        holding = await _holding(session, scope, scope.broker)
        row = await _row(session, scope, scope.broker)

        assert (holding.quantity, row.period_pnl, row.is_fully_sold) == (Decimal("2.500015"), Decimal("50.0003"), False), "precondition: the engine holds half of the residual and of the second BUY"
        assert (holding.oldest_open_lot_date, row.oldest_open_lot_date) == (BUY_DAY, BUY_DAY)
        assert row.annualized_return == expected
        print_success("residual above dust at the share: the first BUY's date")


# =============================================================================
# B12 — a contribution read without an end date stops at today
# =============================================================================


class TestAContributionWithoutAnEndDateStopsAtToday:
    """B12: ``get_positions_contribution`` without ``date_to`` reads the day's transactions up to today, as the rest of the call does.

    ``effective_end = date_to or today`` bounds the period, the flows and the exits, but the broker's transactions were read
    with ``date_to=None``, every row of the broker, the future ones too: a SELL dated after today consumed, in the FIFO that
    gives ``oldest_open_lot_date``, a lot still open today. No production caller leaves the date out (``get_report`` always
    passes one), so the defect was latent; the tests below are the only way to reach it. Read on 22/10/2026 (base
    ``534c280c6``).
    """

    @staticmethod
    async def _row_today(session: AsyncSession, scope: _Scope, today: date) -> AssetPeriodContribution:
        """The scope's asset at its broker in the contribution from 30 days ago, with no end date: one row by construction."""
        contribution = await PortfolioService(session).get_positions_contribution(user_id=scope.user.id, target_currency_override=EUR, date_from=today - timedelta(days=30))
        rows = [row for row in contribution.positions if row.asset_id == scope.asset.id and row.broker_id == scope.broker.id]
        assert len(rows) == 1, f"expected one row of asset {scope.asset.id}, got {[(r.asset_id, r.broker_id) for r in contribution.positions]}"
        return rows[0]

    @pytest.mark.asyncio
    async def test_a_sale_dated_after_today_does_not_close_the_lot_open_today(self, session, keep_alive):
        """BUY 10 for 1000 twenty days ago, SELL 10 five days from now, close 110 today and the day of the BUY: 10 are held today,
        in the BUY's lot — ``oldest_open_lot_date`` is the BUY's date, as with an explicit ``date_to`` of today.

        RED before the cure: the future SELL was read, consumed the lot, and the row had no open lot (None)."""
        print_section("B12: a future sale, no date_to")
        today = date.today()
        buy_day = today - timedelta(days=20)
        scope = await _scope(session, keep_alive, "b12sale")
        await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, buy_day, "10", "-1000"), _trade(scope, TransactionType.SELL, today + timedelta(days=5), "-10", "1200"), _close(scope, buy_day, "100"), _close(scope, today, "110"))

        row = await self._row_today(session, scope, today)

        assert (row.end_value, row.is_fully_sold) == (Decimal("1100"), False), "precondition: the 10 units are held today, worth 10 × 110"
        assert row.oldest_open_lot_date == buy_day, f"the lot of {buy_day} is open today"
        print_success("oldest open lot: the BUY's date")

    @pytest.mark.asyncio
    async def test_guard_the_same_read_with_an_explicit_end_date_is_unchanged(self, session, keep_alive):
        """GUARD, green before and after: the same ledger read to today explicitly dates the open lot from the BUY."""
        today = date.today()
        buy_day = today - timedelta(days=20)
        scope = await _scope(session, keep_alive, "b12explicit")
        await _persist(session, keep_alive, _trade(scope, TransactionType.BUY, buy_day, "10", "-1000"), _trade(scope, TransactionType.SELL, today + timedelta(days=5), "-10", "1200"), _close(scope, buy_day, "100"), _close(scope, today, "110"))

        contribution = await PortfolioService(session).get_positions_contribution(user_id=scope.user.id, target_currency_override=EUR, date_from=today - timedelta(days=30), date_to=today)
        rows = [row for row in contribution.positions if row.asset_id == scope.asset.id and row.broker_id == scope.broker.id]

        assert [row.oldest_open_lot_date for row in rows] == [buy_day]
