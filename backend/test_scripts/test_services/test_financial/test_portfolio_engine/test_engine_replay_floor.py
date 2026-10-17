"""R13-SEC8-2 (MF-SEC8-2, MEDIUM, DoS) — the engine starts no range, and asks no day-by-day rate, before 1900-01-01.

The defect, engine side. ``PortfolioCalculationEngine.calculate`` started its range at the first transaction:
``actual_from = max(date_from, first_tx_date) if date_from else first_tx_date`` — with ``date_from=None`` (the
Dashboard's t=0) or the «min» sentinel (``platform/date_sentinel.py``, resolved to the first transaction's date, so at
most ``date(1, 1, 1)``) a book whose first row was stored in 1890 emitted one ``DailyPortfolioState`` per day since 1890.
``_preload_fx_rates`` asked one rate for every day of each cash interval in transit, from ``interval.start_date``.

The cure (``financial_math/portfolio/engine.py``; ``EARLIEST_RANGE_START = date(1900, 1, 1)`` in
``utils/datetime_utils.py``, written here as the literal ``FLOOR``): ``actual_from = max(EARLIEST_RANGE_START, …)``, and
the in-transit loop of ``_preload_fx_rates`` starts at ``max(interval.start_date, EARLIEST_RANGE_START)``. A movement's
own conversion, at its own date, is still asked: the rows before the floor are replayed exactly.

- ``TestTheRangeStartsAtTheFloor`` — through ``calculate`` on a private in-memory SQLite database:
  * red on HEAD 94e170ae1: with ``date_from`` None, ``date(1, 1, 1)`` or 1899-06-01, a book whose first row is dated
    1890-01-01 emits its first state on 1890-01-01 (HEAD) instead of 1900-01-01; the states run to the end without a gap,
    and the first one holds the 1890 rows (cash 600, the 10 X at their cost of 400, capital 1000 — the same numbers HEAD
    shows on 1900-01-01);
  * GREEN on HEAD and after: a ``date_from`` after the floor (1900-01-05) is kept as it is.
- ``TestTransitRatesStartAtTheFloor`` — ``_preload_fx_rates`` on a ``convert_bulk`` double (pure):
  * red on HEAD: USD cash in transit from 1890-01-02 to 2025-01-01 asks a rate for every day since 1890-01-02 (HEAD:
    3 652 days before the floor); after the cure the only days before the floor are the movements' own (1890-01-01,
    1890-01-02), and the transit's rates run from 1900-01-01 exactly to its last day;
  * GREEN on HEAD and after: a transit after the floor asks every day of its own, from its start.

Isolation. ``TestTheRangeStartsAtTheFloor`` writes only to its own in-memory database (``SQLModel.metadata.create_all``,
one per test, closed and disposed at teardown): nothing reaches the lane's database, no server, no network. Its rows
predate the write floor N74: ``PRAGMA ignore_check_constraints`` keeps a CHECK that floor may add to the schema from
refusing them, as a stored row was never refused. The book is all in EUR, so no rate is asked. The engine's blob cache
is emptied around each test (a cached blob would answer without a replay). ``TestTransitRatesStartAtTheFloor`` replaces
``convert_bulk`` on the engine module through ``monkeypatch``; its engine has no session.

Reference: backend/app/services/financial_math/portfolio/engine.py (calculate step 5, _preload_fx_rates).
"""

from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.test_scripts.test_utils import print_section, print_success

#: ``EARLIEST_RANGE_START`` (utils/datetime_utils.py) as a literal: the name is new in R13-SEC8-2.
FLOOR = date(1900, 1, 1)
OLD = date(1890, 1, 1)
END = date(1900, 1, 10)

A, B = 10, 20

# =============================================================================
# A PRIVATE DATABASE
# =============================================================================


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """This test's own in-memory database with the ORM schema: never the lane's database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            await connection.exec_driver_sql("PRAGMA ignore_check_constraints = ON")
        async with AsyncSession(engine, expire_on_commit=False) as private_session:
            yield private_session
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
def no_cached_blob(request):
    """No engine blob crosses into or out of a test: a cached blob would answer without a replay."""
    portfolio_engine_module._portfolio_blob_cache.clear()
    request.addfinalizer(portfolio_engine_module._portfolio_blob_cache.clear)


async def _book_from_1890(session: AsyncSession) -> int:
    """User U owns broker A at 100 %; on 1890-01-01 A deposits 1000 EUR and buys 10 X (a EUR stock) for 400. Returns U's id."""
    user = User(username="sec8_floor_user", email="sec8_floor_user@test.com", hashed_password="fakehash", is_active=True)
    broker = Broker(name="SEC8-2 floor broker")
    asset = Asset(display_name="SEC8-2 floor X", currency="EUR", asset_type=AssetType.STOCK)
    session.add_all([user, broker, asset])
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    session.add_all(
        [
            Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=OLD, amount=Decimal("1000"), currency="EUR"),
            Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=OLD, quantity=Decimal("10"), amount=Decimal("-400"), currency="EUR"),
        ]
    )
    await session.commit()
    return user.id


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


# =============================================================================
# calculate(): THE RANGE STARTS AT THE FLOOR
# =============================================================================


class TestTheRangeStartsAtTheFloor:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "date_from",
        [
            pytest.param(None, id="dashboard-t0"),
            pytest.param(date(1, 1, 1), id="min-sentinel-day-one"),
            pytest.param(date(1899, 6, 1), id="between-the-first-row-and-the-floor"),
        ],
    )
    async def test_a_book_from_1890_is_emitted_from_the_floor(self, session, date_from):
        """The first state is dated 1900-01-01 and holds the 1890 rows; HEAD: 1890-01-01."""
        print_section(f"R13-SEC8-2: calculate(date_from={date_from}) on a book from 1890")
        user_id = await _book_from_1890(session)

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_from=date_from, date_to=END, target_currency="EUR")

        dates = [state.date for state in result.daily_states]
        assert dates[:1] == [FLOOR], f"the first state is dated {dates[0] if dates else None}, {len(dates)} states"
        assert dates == _days(FLOOR, END)
        assert result.date_from == FLOOR
        first = result.daily_states[0]
        assert (first.cash_value, first.open_cost_basis, first.cumulative_external_cash_flow) == (Decimal("600"), Decimal("400"), Decimal("1000")), "the 1890 rows are in it"
        print_success(f"{len(dates)} states from {FLOOR}")

    @pytest.mark.asyncio
    async def test_a_date_from_after_the_floor_is_kept(self, session):
        """GUARD (green on HEAD too): date_from 1900-01-05 — the states run from it, the 1890 rows in them."""
        print_section("R13-SEC8-2: calculate(date_from=1900-01-05) on a book from 1890")
        user_id = await _book_from_1890(session)
        date_from = date(1900, 1, 5)

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_from=date_from, date_to=END, target_currency="EUR")

        assert [state.date for state in result.daily_states] == _days(date_from, END)
        first = result.daily_states[0]
        assert (first.cash_value, first.open_cost_basis, first.cumulative_external_cash_flow) == (Decimal("600"), Decimal("400"), Decimal("1000"))
        print_success(f"states from {date_from}")


# =============================================================================
# _preload_fx_rates: THE TRANSIT'S RATES START AT THE FLOOR
# =============================================================================


def _tx(*, id: int, broker_id: int, type: str, dt: date, amount: str, related_id: int | None = None) -> MagicMock:
    """A USD cash row as the classifier and _preload_fx_rates read it."""
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = "USD"
    tx.quantity = Decimal("0")
    tx.asset_id = None
    tx.related_transaction_id = related_id
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


async def _requested_rates(monkeypatch, txs: list[MagicMock], *, date_from: date, date_to: date) -> set[tuple[str, date]]:
    """Every ``(currency, day)`` ``_preload_fx_rates`` asks ``convert_bulk`` for, on the classified ``txs`` (scope A and B)."""
    requested: set[tuple[str, date]] = set()

    async def recording_convert_bulk(_session, conversions, raise_on_error=True):
        requested.update((amount.code, day) for amount, _to, day in conversions)
        return [None] * len(conversions), []

    monkeypatch.setattr(portfolio_engine_module, "convert_bulk", recording_convert_bulk)
    classification = ScopeAwareTransactionClassifier({A, B}, sorted(txs, key=lambda tx: (tx.date, tx.id)), {A: Decimal("1"), B: Decimal("1")}).classify()
    assert [interval.tx_type for interval in classification.in_transit_intervals] == ["cash"], "precondition: one cash interval in transit"
    await PortfolioCalculationEngine(None)._preload_fx_rates(
        classification.classified,
        classification.in_transit_intervals,
        classification.external_cash_flows,
        {},
        {},
        "EUR",
        date_from,
        date_to,
    )
    return requested


class TestTransitRatesStartAtTheFloor:
    @pytest.mark.asyncio
    async def test_cash_in_transit_since_1890_asks_its_daily_rates_from_the_floor(self, monkeypatch):
        """A deposits 1000 USD on 1890-01-01; 400 USD leave A on 1890-01-02 and reach B on 2025-01-02 (in transit to
        2025-01-01). Before the floor only the movements' own days are asked; the transit's days run from 1900-01-01 to
        2025-01-01. HEAD: every day from 1890-01-02."""
        print_section("R13-SEC8-2: _preload_fx_rates, USD in transit since 1890")
        txs = [
            _tx(id=1, broker_id=A, type="DEPOSIT", dt=OLD, amount="1000"),
            _tx(id=2, broker_id=A, type="CASH_TRANSFER", dt=date(1890, 1, 2), amount="-400", related_id=3),
            _tx(id=3, broker_id=B, type="CASH_TRANSFER", dt=date(2025, 1, 2), amount="400", related_id=2),
        ]

        requested = await _requested_rates(monkeypatch, txs, date_from=date(2025, 1, 1), date_to=date(2025, 1, 7))

        before_the_floor = sorted(day for _currency, day in requested if day < FLOOR)
        assert before_the_floor == [OLD, date(1890, 1, 2)], f"{len(before_the_floor)} days asked before the floor, from {before_the_floor[:1]}"
        assert {("USD", FLOOR), ("USD", date(2025, 1, 1))} <= requested, "the transit's rates run from the floor to its last day"
        print_success("the movements' own days, then the transit from 1900-01-01")

    @pytest.mark.asyncio
    async def test_cash_in_transit_after_the_floor_asks_every_day_of_its_own(self, monkeypatch):
        """GUARD (green on HEAD too): 400 USD leave A on 1900-01-03 and reach B on 1900-01-06: 1900-01-03 to 1900-01-05
        asked, and nothing else but the arrival's own day."""
        print_section("R13-SEC8-2: _preload_fx_rates, USD in transit after the floor")
        txs = [
            _tx(id=2, broker_id=A, type="CASH_TRANSFER", dt=date(1900, 1, 3), amount="-400", related_id=3),
            _tx(id=3, broker_id=B, type="CASH_TRANSFER", dt=date(1900, 1, 6), amount="400", related_id=2),
        ]

        requested = await _requested_rates(monkeypatch, txs, date_from=date(1900, 1, 3), date_to=date(1900, 1, 7))

        assert requested == {("USD", day) for day in _days(date(1900, 1, 3), date(1900, 1, 6))}
        print_success("1900-01-03 to 1900-01-06")
