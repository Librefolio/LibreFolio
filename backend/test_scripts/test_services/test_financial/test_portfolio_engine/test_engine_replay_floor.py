"""MF-PAV-L1 (was R13-SEC8-2) — the portfolio engine starts its frame on the first transaction, even before 1900, and asks the transit's rates from its start.

History. R13-SEC8-2 (MF-SEC8-2, DoS) stopped the engine at ``EARLIEST_RANGE_START = 1900-01-01``: ``actual_from =
max(date_from, first_tx_date, EARLIEST_RANGE_START)``, and the in-transit loop of ``_preload_fx_rates`` started at
``max(interval.start_date, EARLIEST_RANGE_START)``, because the engine emitted a state per day and asked a rate per day.
Since D-P4 the engine keeps segments (steps) and asks its rates as windows (``unit_rate_steps``): the cost follows the
novelties, not the days, so the floor protects nothing and hides the first rows' years. The contract of L1:

- the frame starts at ``max(date_from, first_tx_date)`` (``first_tx_date`` for ``date_from=None``), whatever the year — year
  1 included; the constant ``EARLIEST_RANGE_START`` stays for other readers and is not touched here;
- the cash in transit asks its rates from the transit's start, in ONE window to its last day, with no clamp;
- the rows before 1900 are replayed on their own dates, as they always were;
- nothing counts them: ``RowsBeforeFloor``, ``PortfolioCalculationResult.rows_before_floor`` and the data-quality warning
  built on them (never released) are gone.

- ``TestTheFrameStartsOnTheFirstRow`` — through ``calculate`` on a private in-memory SQLite database. RED on HEAD
  999f1899e (frame from 1900-01-01): with ``date_from`` None, ``date(1, 1, 1)`` or 1899-06-01, a book whose first row is
  dated 1890-01-01 emits its first state on 1890-01-01 (``date_from`` 1899-06-01: on 1899-06-01, after the first row),
  every day to the end without a gap, the first one holding the 1890 rows (cash 600, the 10 X at their cost of 400,
  capital 1000); a ``date_from`` of 1895-06-01 (after the first row, before the floor) is kept. A later 1890 row acts on
  its own date (1890-03-01). GREEN on HEAD (guard): a ``date_from`` after the floor (1900-01-05) is kept as it is.
- ``TestTransitRatesStartAtTheTransit`` — ``_preload_fx_rates`` on a ``unit_rate_steps`` double (pure). RED on HEAD: USD
  cash in transit from 1890-01-02 to 2025-01-01 asks its rates in one window from 1890-01-02 (HEAD: from 1900-01-01) to
  its last day, so with the movements' own days the days asked are the one run from 1890-01-01 to the arrival, 2025-01-02.
  GREEN on HEAD (guard): a transit after the floor asks every day of its own, from its start.
- ``TestNothingCountsTheRowsBeforeTheFloor`` — RED on HEAD: ``PortfolioCalculationResult`` has no ``rows_before_floor`` (neither
  as a field nor on a result built by ``calculate``), and ``portfolio.models`` has no ``RowsBeforeFloor``.

Isolation. ``TestTheFrameStartsOnTheFirstRow`` and the ``calculate`` test of ``TestNothingCountsTheRowsBeforeTheFloor`` write only
to their own in-memory database (``SQLModel.metadata.create_all``, one per test, closed and disposed at teardown): nothing
reaches the lane's database, no server, no network. Their rows predate the write floor N74: ``PRAGMA
ignore_check_constraints`` keeps a CHECK that floor may add to the schema from refusing them, as a stored row was never
refused. The books are all in EUR, so no rate is asked. The engine's blob cache is emptied around each test (a cached blob
would answer without a replay). ``TestTransitRatesStartAtTheTransit`` replaces ``unit_rate_steps`` on the engine module
through ``monkeypatch``; its engine has no session.

Reference: backend/app/services/financial_math/portfolio/engine.py (calculate step 5, _preload_fx_rates).
"""

import dataclasses
from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.financial_math.portfolio.models as portfolio_models
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.test_scripts.test_services._unit_steps_double import UnitStepsDouble
from backend.test_scripts.test_utils import print_section, print_success

#: The 1900 of ``EARLIEST_RANGE_START`` (utils/datetime_utils.py), as a literal: the engine no longer reads it; only the guards below do.
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
# calculate(): THE FRAME STARTS ON THE FIRST ROW
# =============================================================================


class TestTheFrameStartsOnTheFirstRow:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("date_from", "first_day"),
        [
            pytest.param(None, OLD, id="dashboard-t0"),
            pytest.param(date(1, 1, 1), OLD, id="min-sentinel-day-one"),
            pytest.param(date(1899, 6, 1), date(1899, 6, 1), id="between-the-first-row-and-the-floor"),
            pytest.param(date(1895, 6, 1), date(1895, 6, 1), id="after-the-first-row-before-the-floor"),
        ],
    )
    async def test_a_book_from_1890_is_emitted_from_its_first_row(self, session, date_from, first_day):
        """The first state is on the first row (1890-01-01) — or on ``date_from`` when that is later — and holds the 1890
        rows; the states run to the end without a gap. HEAD: the first state is on 1900-01-01 whatever ``date_from``."""
        print_section(f"MF-PAV-L1: calculate(date_from={date_from}) on a book from 1890")
        user_id = await _book_from_1890(session)

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_from=date_from, date_to=END, target_currency="EUR")

        dates = [state.date for state in result.daily_states]
        assert dates[:1] == [first_day], f"the first state is dated {dates[0] if dates else None} ({len(dates)} states): the frame starts on max(date_from, first row) = {first_day}"
        assert dates == _days(first_day, END), "the states run from the first day to the end without a gap"
        assert result.date_from == first_day, "the result's date_from is the frame's first day"
        first = result.daily_states[0]
        assert (first.cash_value, first.open_cost_basis, first.cumulative_external_cash_flow) == (Decimal("600"), Decimal("400"), Decimal("1000")), "the 1890 rows are in the first state"
        print_success(f"{len(dates)} states from {first_day}")

    @pytest.mark.asyncio
    async def test_a_row_of_1890_acts_on_its_own_date(self, session):
        """The 1890 book plus a deposit of 200 on 1890-03-01: the state of 1890-02-28 still has capital 1000, the state of
        1890-03-01 has 1200 — the rows are replayed on their own dates, from the first row. HEAD: no state before 1900-01-01."""
        print_section("MF-PAV-L1: a later 1890 row acts on its own date")
        user_id = await _book_from_1890(session)
        broker_id = (await session.execute(select(Broker.id).where(Broker.name == "SEC8-2 floor broker"))).scalar_one()
        session.add(Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=date(1890, 3, 1), amount=Decimal("200"), currency="EUR"))
        await session.commit()

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_from=None, date_to=END, target_currency="EUR")

        by_day = {state.date: state for state in result.daily_states}
        assert {day: by_day.get(day) and by_day[day].cumulative_external_cash_flow for day in (date(1890, 2, 28), date(1890, 3, 1))} == {date(1890, 2, 28): Decimal("1000"), date(1890, 3, 1): Decimal("1200")}, "the deposit of 1890-03-01 acts on 1890-03-01"
        print_success("capital 1000 on 1890-02-28, 1200 on 1890-03-01")

    @pytest.mark.asyncio
    async def test_a_date_from_after_the_floor_is_kept(self, session):
        """GUARD (green on HEAD too): date_from 1900-01-05 — the states run from it, the 1890 rows in them."""
        print_section("MF-PAV-L1: calculate(date_from=1900-01-05) on a book from 1890")
        user_id = await _book_from_1890(session)
        date_from = date(1900, 1, 5)

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_from=date_from, date_to=END, target_currency="EUR")

        assert [state.date for state in result.daily_states] == _days(date_from, END)
        first = result.daily_states[0]
        assert (first.cash_value, first.open_cost_basis, first.cumulative_external_cash_flow) == (Decimal("600"), Decimal("400"), Decimal("1000"))
        print_success(f"states from {date_from}")


# =============================================================================
# _preload_fx_rates: THE TRANSIT'S RATES START AT THE TRANSIT
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


async def _requested_rates(monkeypatch, txs: list[MagicMock], *, date_from: date, date_to: date) -> tuple[set[tuple[str, date]], UnitStepsDouble]:
    """Every ``(currency, day)`` ``_preload_fx_rates`` asks a rate for, on the classified ``txs`` (scope A and B): the days
    of the windows of its one ``unit_rate_steps`` call (P3; the ``convert_bulk`` items before); and the double, whose
    windows the tests read too. It answers no rate, as the ``convert_bulk`` double answered None."""
    steps = UnitStepsDouble(value=None)
    monkeypatch.setattr(portfolio_engine_module, "unit_rate_steps", steps)
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
    return {(currency, day) for currency, _target, day in steps.asked_keys()}, steps


class TestTransitRatesStartAtTheTransit:
    @pytest.mark.asyncio
    async def test_cash_in_transit_since_1890_asks_its_rates_in_one_window_from_its_start(self, monkeypatch):
        """A deposits 1000 USD on 1890-01-01; 400 USD leave A on 1890-01-02 and reach B on 2025-01-02 (in transit to
        2025-01-01). The transit is ONE window of ``unit_rate_steps``, 1890-01-02 to 2025-01-01; with the movements' own
        days (1890-01-01, 1890-01-02, the arrival 2025-01-02) the days asked are one run, 1890-01-01 to 2025-01-02. HEAD:
        the window starts on 1900-01-01 and the days before it are the movements' only."""
        print_section("MF-PAV-L1: _preload_fx_rates, USD in transit since 1890")
        txs = [
            _tx(id=1, broker_id=A, type="DEPOSIT", dt=OLD, amount="1000"),
            _tx(id=2, broker_id=A, type="CASH_TRANSFER", dt=date(1890, 1, 2), amount="-400", related_id=3),
            _tx(id=3, broker_id=B, type="CASH_TRANSFER", dt=date(2025, 1, 2), amount="400", related_id=2),
        ]

        requested, steps = await _requested_rates(monkeypatch, txs, date_from=date(2025, 1, 1), date_to=date(2025, 1, 7))

        windows = steps.only_call()[("USD", "EUR")]
        assert [window for window in windows if window[0] < window[1]] == [(date(1890, 1, 2), date(2025, 1, 1))], f"the transit is one window, from its start to its last day; windows {windows[:4]}"
        assert {("USD", date(1890, 1, 2)), ("USD", date(2025, 1, 1))} <= requested, "the rates run from the transit's start to its last day"
        assert steps.runs() == {("USD", "EUR"): [(OLD, date(2025, 1, 2))]}, "the movements' days and the transit make one run, from the first row to the arrival"
        print_success("one window, 1890-01-02 to 2025-01-01")

    @pytest.mark.asyncio
    async def test_cash_in_transit_after_the_floor_asks_every_day_of_its_own(self, monkeypatch):
        """GUARD (green on HEAD too): 400 USD leave A on 1900-01-03 and reach B on 1900-01-06: 1900-01-03 to 1900-01-06
        asked, and nothing else."""
        print_section("MF-PAV-L1: _preload_fx_rates, USD in transit after the floor")
        txs = [
            _tx(id=2, broker_id=A, type="CASH_TRANSFER", dt=date(1900, 1, 3), amount="-400", related_id=3),
            _tx(id=3, broker_id=B, type="CASH_TRANSFER", dt=date(1900, 1, 6), amount="400", related_id=2),
        ]

        requested, steps = await _requested_rates(monkeypatch, txs, date_from=date(1900, 1, 3), date_to=date(1900, 1, 7))

        assert requested == {("USD", day) for day in _days(date(1900, 1, 3), date(1900, 1, 6))}
        assert (date(1900, 1, 3), date(1900, 1, 5)) in steps.only_call()[("USD", "EUR")], "the transit is one window, from its start"
        print_success("1900-01-03 to 1900-01-06")


# =============================================================================
# NOTHING COUNTS THE ROWS BEFORE THE FLOOR
# =============================================================================


class TestNothingCountsTheRowsBeforeTheFloor:
    """The engine no longer counts the rows dated before 1900: they start the history like any other (``RowsBeforeFloor``,
    ``rows_before_floor`` and the data-quality warning were never released)."""

    def test_the_models_have_no_rows_before_floor_record(self):
        """RED on HEAD: ``portfolio.models`` still defines ``RowsBeforeFloor``."""
        assert not hasattr(portfolio_models, "RowsBeforeFloor"), "financial_math.portfolio.models still has RowsBeforeFloor: the engine counts no row before 1900"

    def test_a_result_has_no_rows_before_floor_field(self):
        """RED on HEAD: ``PortfolioCalculationResult`` still has ``rows_before_floor`` (None by default)."""
        result = portfolio_models.PortfolioCalculationResult(daily_states=[])
        field_names = [field.name for field in dataclasses.fields(result)] if dataclasses.is_dataclass(result) else []
        assert not hasattr(result, "rows_before_floor") and "rows_before_floor" not in field_names, "PortfolioCalculationResult still carries rows_before_floor"

    @pytest.mark.asyncio
    async def test_a_calculated_result_has_no_rows_before_floor(self, session):
        """RED on HEAD: the result of ``calculate`` on a book from 1890 still holds a ``rows_before_floor`` record (count 2).
        Barrier: the replay ran — the 1890 rows are in the first state."""
        print_section("MF-PAV-L1: calculate() counts no row before 1900")
        user_id = await _book_from_1890(session)

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_to=END, target_currency="EUR")

        assert result.daily_states[0].cumulative_external_cash_flow == Decimal("1000"), "precondition: the replay ran, the 1890 rows in it"
        assert not hasattr(result, "rows_before_floor"), f"calculate() returned rows_before_floor={getattr(result, 'rows_before_floor', None)!r}"
        print_success("no rows_before_floor")
