"""
MF-A (workstream MF, lot A) — the engine's snapshot at a period start: ``PortfolioCalculationEngine.calculate(period_start=D)``.

The Dashboard runs the engine from t=0 (``date_from=None``) so that every cumulative figure is right, and reads the
period's start from its daily states. Its ``position_states_start`` is the snapshot of the first frame day — with
``date_from=None``, the day of the first transaction — so it cannot give the Performance table the positions held at
the start of the period. Since MF-A ``calculate`` takes ``period_start``: ``position_states_start`` is then the
positions held at the **end** of ``period_start`` (quantity > 0, movements dated ≤ ``period_start`` included), each
valued that day, while the engine still runs from t=0. Without ``period_start`` nothing changes: the snapshot is the
first frame day's (``test_portfolio_engine_vnext.py`` and ``test_portfolio_engine/test_daily_state_builder.py`` rely
on it).

The ledger — one user owning 100 % of one broker, everything in EUR, read in EUR up to END = 2025-05-31:

- E0 = 2025-05-02: DEPOSIT 10000; BUY 10 X for 1000; ADJUSTMENT +5 W at a cost of 40 a unit (W has no price ever);
- E1 = 2025-05-06: BUY 5 Y for 500 (Y is never quoted);
- E2 = 2025-05-12: BUY 10 X for 1200, and X closes 115 the same day (the quote wins over the BUY's price);
- E3 = 2025-05-15: nothing happens;
- E4 = 2025-05-20: SELL 5 Y for 600 (Y is gone); X closes 130.

The positions held at the end of each day, by hand (quantity, market value, cost basis, valuation source):

- E0: X 10, 1000 (the BUY's 100), 1000, LAST_TRADE_PRICE; W 5, 200, 200, ESTIMATED_AT_COST;
- E2 and E3: X 20, 2300 (20 × 115), 2200, MARKET_PRICE; Y 5, 500 (the BUY's 100), 500, LAST_TRADE_PRICE; W as on E0;
- END: X 20, 2600 (20 × 130), 2200, MARKET_PRICE; W as on E0.

Green on HEAD and after (parity pins, they also prove the table above is what the engine computes today):

- TestWithoutPeriodStart — ``date_from=None``: the snapshot is E0's; ``date_from=D``: it is D's, for D in E0, E2,
  E3, END.

Red on HEAD (``TypeError``: ``calculate`` takes no ``period_start``), green after:

- TestPeriodStartSnapshot — ``date_from=None, period_start=D`` gives the table's row for D (E0, E2, E3, END), the
  same snapshot as a run with ``date_from=D``; the engine still runs from E0 (same daily states, same end positions
  as the run without ``period_start``); a ``period_start`` before the first transaction gives an empty snapshot;
- TestPeriodStartAndTheBlobCache — the blob cache keys on the range only, and a cached t=0 run answers any request
  with the same end (``blob_from <= actual_from and blob_to == actual_to``). A run with ``period_start`` must not be
  answered by a cached run without it, nor the reverse: the Dashboard calls the summary (no ``period_start``) and the
  Performance table one after the other.

Isolation: the test owns its user, broker and assets (unique names) and writes only through a session that is rolled
back: nothing is committed. Everything is EUR, so no FX rate is read. The report, WAC and engine blob caches are
emptied around each test, and between the runs a test compares (the cache would otherwise hand the second run the
first one's blob). Positions are found by the test's own asset ids.

Reference: backend/app/services/financial_math/portfolio/engine.py (calculate, the blob cache),
backend/app/services/financial_math/portfolio/daily_state.py (build, _build_position_state).
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

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import PortfolioCalculationResult, ValuationSource
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
ZERO = Decimal("0")

BEFORE = date(2025, 4, 30)  # before the first transaction
E0 = date(2025, 5, 2)
E1 = date(2025, 5, 6)
E2 = date(2025, 5, 12)
E3 = date(2025, 5, 15)  # nothing happens
E4 = date(2025, 5, 20)
END = date(2025, 5, 31)

MARKET = ValuationSource.MARKET_PRICE
TRADE = ValuationSource.LAST_TRADE_PRICE
AT_COST = ValuationSource.ESTIMATED_AT_COST

# (quantity, market value, cost basis, valuation source) by asset label, at the end of each day.
_W = ("5", "200", "200", AT_COST)
HELD_AT_END_OF: dict[date, dict[str, tuple[str, str, str, ValuationSource]]] = {
    E0: {"X": ("10", "1000", "1000", TRADE), "W": _W},
    E2: {"X": ("20", "2300", "2200", MARKET), "Y": ("5", "500", "500", TRADE), "W": _W},
    E3: {"X": ("20", "2300", "2200", MARKET), "Y": ("5", "500", "500", TRADE), "W": _W},
    END: {"X": ("20", "2600", "2200", MARKET), "W": _W},
}

SNAPSHOT_DAYS = [
    pytest.param(E0, id="first-transaction-day"),
    pytest.param(E2, id="a-day-with-a-buy-and-a-quote"),
    pytest.param(E3, id="a-day-with-nothing"),
    pytest.param(END, id="the-last-day"),
]


# =============================================================================
# HELPERS
# =============================================================================


@dataclass
class _Book:
    user: User
    broker: Broker
    assets: dict[str, Asset]


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


async def _ledger(session: AsyncSession, keep_alive: list[object]) -> _Book:
    tag = uuid4().hex[:12]
    user = User(username=f"mfa_ps_{tag}", email=f"mfa_ps_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name=f"MfA period start {tag}")
    assets = {name: Asset(display_name=f"MfA period start {name} {tag}", currency=EUR, asset_type=AssetType.STOCK) for name in ("X", "Y", "W")}
    await _persist(session, keep_alive, user, broker, *assets.values())
    await _persist(session, keep_alive, BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))

    def trade(asset: str, kind: TransactionType, day: date, quantity: str, amount: str) -> Transaction:
        return Transaction(broker_id=broker.id, asset_id=assets[asset].id, type=kind, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=EUR)

    def close(asset: str, day: date, value: str) -> PriceHistory:
        price = Decimal(value)
        return PriceHistory(asset_id=assets[asset].id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="mf_a_period_start_test")

    await _persist(
        session,
        keep_alive,
        Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=E0, quantity=ZERO, amount=Decimal("10000"), currency=EUR),
        trade("X", TransactionType.BUY, E0, "10", "-1000"),
        # In kind, no cash, no quote, no BUY or SELL: W has no price at all.
        Transaction(broker_id=broker.id, asset_id=assets["W"].id, type=TransactionType.ADJUSTMENT, date=E0, quantity=Decimal("5"), amount=ZERO, cost_basis_override=Decimal("40"), cost_basis_currency=EUR),
        trade("Y", TransactionType.BUY, E1, "5", "-500"),
        trade("X", TransactionType.BUY, E2, "10", "-1200"),
        close("X", E2, "115"),
        trade("Y", TransactionType.SELL, E4, "-5", "600"),
        close("X", E4, "130"),
    )
    return _Book(user=user, broker=broker, assets=assets)


async def _calculate(session: AsyncSession, book: _Book, **kwargs) -> PortfolioCalculationResult:
    return await PortfolioCalculationEngine(session).calculate(user_id=book.user.id, date_to=END, target_currency=EUR, **kwargs)


def _snapshot(result: PortfolioCalculationResult, book: _Book) -> dict[str, tuple[date, Decimal, Decimal | None, Decimal, str]]:
    """``position_states_start`` by asset label: (date, quantity, market value, cost basis, valuation source)."""
    labels = {asset.id: label for label, asset in book.assets.items()}
    snapshot: dict[str, tuple[date, Decimal, Decimal | None, Decimal, str]] = {}
    for ps in result.position_states_start:
        assert ps.broker_id == book.broker.id and ps.asset_id in labels, f"position ({ps.broker_id}, {ps.asset_id}) is not the test's"
        label = labels[ps.asset_id]
        assert label not in snapshot, f"two start positions for {label}"
        snapshot[label] = (ps.date, ps.quantity, ps.market_value, ps.cost_basis, str(ps.valuation_source))
    return snapshot


def _end_positions(result: PortfolioCalculationResult) -> list[tuple]:
    return sorted((ps.broker_id, ps.asset_id, ps.date, ps.quantity, ps.market_value, ps.cost_basis) for ps in result.position_states_end)


def _daily(result: PortfolioCalculationResult) -> list[tuple]:
    return [(state.date, state.nav_value, state.market_value, state.open_cost_basis, state.cumulative_external_cash_flow) for state in result.daily_states]


def _expected(day: date) -> dict[str, tuple[date, Decimal, Decimal, Decimal, str]]:
    """The positions held at the end of ``day``, from HELD_AT_END_OF, dated ``day``."""
    return {label: (day, Decimal(quantity), Decimal(value), Decimal(cost), str(source)) for label, (quantity, value, cost, source) in HELD_AT_END_OF[day].items()}


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
# Green on HEAD and after: without period_start the snapshot is the first frame day's
# =============================================================================


class TestWithoutPeriodStart:
    @pytest.mark.asyncio
    async def test_a_run_from_t0_starts_with_the_first_transaction_day(self, session, keep_alive):
        """``date_from=None``: the frame starts on E0 and so does the snapshot — X 10 at the BUY's 100, W 5 at cost."""
        print_section("MF-A engine snapshot: t=0, no period_start")
        book = await _ledger(session, keep_alive)

        result = await _calculate(session, book, date_from=None)

        assert result.daily_states[0].date == E0, "precondition: the frame starts on the first transaction"
        assert _snapshot(result, book) == _expected(E0)
        print_success("snapshot of E0")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("day", SNAPSHOT_DAYS)
    async def test_a_run_from_a_day_starts_with_the_positions_held_at_its_end(self, session, keep_alive, day):
        """``date_from=D``: the snapshot is the positions held at the end of D, each valued that day."""
        print_section(f"MF-A engine snapshot: date_from={day}")
        book = await _ledger(session, keep_alive)

        result = await _calculate(session, book, date_from=day)

        assert _snapshot(result, book) == _expected(day)
        print_success(f"snapshot of {day}")


# =============================================================================
# Red on HEAD (TypeError), green after: period_start
# =============================================================================


class TestPeriodStartSnapshot:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("day", SNAPSHOT_DAYS)
    async def test_the_snapshot_is_the_positions_held_at_the_end_of_period_start(self, session, keep_alive, day):
        """``date_from=None, period_start=D``: the positions held at the end of D, valued that day."""
        print_section(f"MF-A engine snapshot: t=0, period_start={day}")
        book = await _ledger(session, keep_alive)

        result = await _calculate(session, book, date_from=None, period_start=day)

        assert result.daily_states[0].date == E0, "the engine still runs from the first transaction"
        assert _snapshot(result, book) == _expected(day)
        print_success(f"snapshot of {day} from a t=0 run")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("day", SNAPSHOT_DAYS)
    async def test_it_is_the_snapshot_of_a_run_that_starts_on_that_day(self, session, keep_alive, day):
        """The same positions, values, costs and sources as ``date_from=D`` — the snapshot a run starting there takes."""
        print_section(f"MF-A engine snapshot: period_start={day} against date_from={day}")
        book = await _ledger(session, keep_alive)

        from_day = await _calculate(session, book, date_from=day)
        _clear_portfolio_caches()
        from_t0 = await _calculate(session, book, date_from=None, period_start=day)

        assert _snapshot(from_t0, book) == _snapshot(from_day, book)
        print_success("same snapshot both ways")

    @pytest.mark.asyncio
    async def test_period_start_changes_nothing_else(self, session, keep_alive):
        """With ``period_start=E2`` the daily states and the end positions are those of the run without it."""
        print_section("MF-A engine: period_start changes only the start snapshot")
        book = await _ledger(session, keep_alive)

        without = await _calculate(session, book, date_from=None)
        _clear_portfolio_caches()
        with_period_start = await _calculate(session, book, date_from=None, period_start=E2)

        assert _daily(with_period_start) == _daily(without)
        assert _end_positions(with_period_start) == _end_positions(without)
        print_success("same daily states, same end positions")

    @pytest.mark.asyncio
    async def test_a_period_starting_before_the_first_transaction_starts_empty(self, session, keep_alive):
        """``period_start`` before E0: nothing is held at its end."""
        print_section("MF-A engine snapshot: period_start before the first transaction")
        book = await _ledger(session, keep_alive)

        result = await _calculate(session, book, date_from=None, period_start=BEFORE)

        assert result.position_states_start == []
        assert result.daily_states[0].date == E0
        print_success("empty snapshot")


class TestPeriodStartAndTheBlobCache:
    @pytest.mark.asyncio
    async def test_a_cached_run_without_period_start_does_not_answer_for_one_with_it(self, session, keep_alive):
        """The summary's run (no ``period_start``) is cached, then the table asks for ``period_start=E2``: E2's snapshot."""
        print_section("MF-A engine cache: without, then with period_start")
        book = await _ledger(session, keep_alive)

        first = await _calculate(session, book, date_from=None)
        second = await _calculate(session, book, date_from=None, period_start=E2)

        assert _snapshot(first, book) == _expected(E0), "precondition: the first run's snapshot is E0's"
        assert _snapshot(second, book) == _expected(E2)
        print_success("E0 then E2")

    @pytest.mark.asyncio
    async def test_a_cached_run_with_period_start_does_not_answer_for_one_without_it(self, session, keep_alive):
        """The reverse order: ``period_start=E2`` first, then a run without it gets E0's snapshot."""
        print_section("MF-A engine cache: with, then without period_start")
        book = await _ledger(session, keep_alive)

        first = await _calculate(session, book, date_from=None, period_start=E2)
        second = await _calculate(session, book, date_from=None)

        assert _snapshot(first, book) == _expected(E2), "precondition: the first run's snapshot is E2's"
        assert _snapshot(second, book) == _expected(E0)
        print_success("E2 then E0")
