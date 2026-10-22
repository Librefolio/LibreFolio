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
- ``TestTransitRatesStartAtTheFloor`` — ``_preload_fx_rates`` on a ``unit_rate_steps`` double (pure; a ``convert_bulk``
  double before P3, «formule veloci»: the days asked one by one are now the days of the windows of one call):
  * red on HEAD: USD cash in transit from 1890-01-02 to 2025-01-01 asks a rate for every day since 1890-01-02 (HEAD:
    3 652 days before the floor); after the cure the only days before the floor are the movements' own (1890-01-01,
    1890-01-02), and the transit's rates run from 1900-01-01 exactly to its last day;
  * GREEN on HEAD and after: a transit after the floor asks every day of its own, from its start.
- MF-SEC8-2a — the rows before the floor are replayed, but the histories start on it, silently: the engine counts them
  for a WARNING of the data-quality report (``data_quality.build_data_quality_report(rows_before_floor=…)``, pinned in
  ``test_data_quality_report.py``). Red on HEAD f4a1e374f (no ``RowsBeforeFloor``, no ``rows_before_floor``):
  * ``TestRowsBeforeFloorRecord`` (pure): ``models.RowsBeforeFloor(count, earliest)``, a frozen dataclass, and
    ``PortfolioCalculationResult.rows_before_floor``, None by default;
  * ``TestTheRowsBeforeTheFloorAreCounted`` — through ``calculate``, same private database as above: two rows before
    the floor (0001-01-01 and 1890-01-01; one on 1900-01-01 is not before it) give ``RowsBeforeFloor(2, 0001-01-01)``,
    for a window after the floor too; a book from the floor on gives None; only the scope's brokers' rows count.

Isolation. ``TestTheRangeStartsAtTheFloor`` and ``TestTheRowsBeforeTheFloorAreCounted`` write only to their own in-memory
database (``SQLModel.metadata.create_all``, one per test, closed and disposed at teardown): nothing reaches the lane's
database, no server, no network. Their rows predate the write floor N74: ``PRAGMA ignore_check_constraints`` keeps a
CHECK that floor may add to the schema from refusing them, as a stored row was never refused. The books are all in EUR,
so no rate is asked. The engine's blob cache is emptied around each test (a cached blob would answer without a replay).
``TestTransitRatesStartAtTheFloor`` replaces ``unit_rate_steps`` on the engine module through ``monkeypatch``; its engine
has no session. ``TestRowsBeforeFloorRecord`` touches no database.

Reference: backend/app/services/financial_math/portfolio/engine.py (calculate step 5, _preload_fx_rates).
"""

import dataclasses
from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.financial_math.portfolio.models as portfolio_models
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.test_scripts.test_services._unit_steps_double import UnitStepsDouble
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

        requested, steps = await _requested_rates(monkeypatch, txs, date_from=date(2025, 1, 1), date_to=date(2025, 1, 7))

        before_the_floor = sorted(day for _currency, day in requested if day < FLOOR)
        assert before_the_floor == [OLD, date(1890, 1, 2)], f"{len(before_the_floor)} days asked before the floor, from {before_the_floor[:1]}"
        assert {("USD", FLOOR), ("USD", date(2025, 1, 1))} <= requested, "the transit's rates run from the floor to its last day"
        assert (FLOOR, date(2025, 1, 1)) in steps.only_call()[("USD", "EUR")], "P3: the transit is one window, from the floor to its last day"
        assert steps.runs() == {("USD", "EUR"): [(OLD, date(1890, 1, 2)), (FLOOR, date(2025, 1, 2))]}, "the movements' days, then the floor to the arrival"
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

        requested, steps = await _requested_rates(monkeypatch, txs, date_from=date(1900, 1, 3), date_to=date(1900, 1, 7))

        assert requested == {("USD", day) for day in _days(date(1900, 1, 3), date(1900, 1, 6))}
        assert (date(1900, 1, 3), date(1900, 1, 5)) in steps.only_call()[("USD", "EUR")], "P3: the transit is one window, from its start"
        print_success("1900-01-03 to 1900-01-06")


# =============================================================================
# MF-SEC8-2a: calculate() COUNTS THE SCOPE'S ROWS BEFORE THE FLOOR
# =============================================================================

#: ``date.min``: the oldest day a stored row can carry (the calendar has no day before it).
DAY_ONE = date(1, 1, 1)


def _rows_before_floor_record() -> type:
    record = getattr(portfolio_models, "RowsBeforeFloor", None)
    if record is None:
        pytest.fail("financial_math.portfolio.models has no RowsBeforeFloor (MF-SEC8-2a): the engine has nowhere to count the rows dated before 1900")
    return record


def _rows_before_floor_of(result) -> object:
    """``result.rows_before_floor``, failing the test (never erroring) on a result that has no such field."""
    if not hasattr(result, "rows_before_floor"):
        pytest.fail("PortfolioCalculationResult has no rows_before_floor (MF-SEC8-2a): the report cannot warn that the histories start on 1900-01-01")
    return result.rows_before_floor


async def _owner_of(session: AsyncSession, *broker_names: str) -> tuple[int, list[int], int]:
    """User U owning each named broker at 100 %, and X, a EUR stock. Returns (U's id, the brokers' ids in order, X's id)."""
    user = User(username="sec8_2a_user", email="sec8_2a_user@test.com", hashed_password="fakehash", is_active=True)
    brokers = [Broker(name=name) for name in broker_names]
    asset = Asset(display_name="SEC8-2a X", currency="EUR", asset_type=AssetType.STOCK)
    session.add_all([user, *brokers, asset])
    await session.flush()
    session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers])
    return user.id, [broker.id for broker in brokers], asset.id


def _deposit(broker_id: int, day: date, amount: str = "1000") -> Transaction:
    return Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=day, amount=Decimal(amount), currency="EUR")


def _buy(broker_id: int, asset_id: int, day: date) -> Transaction:
    """10 X for 400 EUR."""
    return Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=day, quantity=Decimal("10"), amount=Decimal("-400"), currency="EUR")


class TestRowsBeforeFloorRecord:
    """Pure: the record the engine fills and the data-quality report reads."""

    def test_it_is_a_frozen_dataclass_of_count_and_earliest(self):
        """Red on HEAD f4a1e374f (no RowsBeforeFloor). Frozen, compared by value: it travels in the blob cache with the
        result, shared by every caller of that blob."""
        record = _rows_before_floor_record()
        assert dataclasses.is_dataclass(record), f"RowsBeforeFloor is {record!r}, not a dataclass"
        assert [field.name for field in dataclasses.fields(record)] == ["count", "earliest"]
        value = record(count=2, earliest=DAY_ONE)
        assert value == record(count=2, earliest=DAY_ONE)
        assert value != record(count=2, earliest=OLD)
        with pytest.raises(dataclasses.FrozenInstanceError):
            value.count = 3  # type: ignore[misc]

    def test_a_result_has_none_by_default(self):
        """Red on HEAD (no field). A result built without it — the early returns of ``calculate``, an empty scope — says
        "none" rather than lacking the field."""
        result = portfolio_models.PortfolioCalculationResult(daily_states=[])
        assert _rows_before_floor_of(result) is None


class TestTheRowsBeforeTheFloorAreCounted:
    """MF-SEC8-2a, through ``calculate`` on this test's own in-memory database (same isolation as
    ``TestTheRangeStartsAtTheFloor``). ``result.rows_before_floor`` is ``RowsBeforeFloor(count, earliest)`` over the
    scope's transactions dated before 1900-01-01 — whatever the requested window, since they are all replayed — and None
    when there is none. A row on the floor itself is not before it.

    Red on HEAD f4a1e374f: the result has no ``rows_before_floor`` (and ``models`` no ``RowsBeforeFloor``); the replay
    itself runs on HEAD, a row on ``date.min`` included (measured).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_from", [pytest.param(None, id="dashboard-t0"), pytest.param(date(1900, 1, 5), id="window-after-the-floor")])
    async def test_two_rows_before_the_floor_are_counted_with_the_earliest(self, session, date_from):
        """A deposits 1000 on 0001-01-01 and buys 10 X on 1890-01-01, then deposits 50 on 1900-01-01 (the floor: not
        before it) and 70 on 1900-01-03. Barrier: the replay ran, the old rows in it. Then two rows, the earliest on
        0001-01-01 — for a window after the floor too: the count is the scope's, not the window's."""
        print_section(f"MF-SEC8-2a: rows before the floor, calculate(date_from={date_from})")
        user_id, (broker_a,), asset_id = await _owner_of(session, "SEC8-2a A")
        session.add_all([_deposit(broker_a, DAY_ONE), _buy(broker_a, asset_id, OLD), _deposit(broker_a, FLOOR, "50"), _deposit(broker_a, date(1900, 1, 3), "70")])
        await session.commit()

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_from=date_from, date_to=END, target_currency="EUR")

        assert result.daily_states, "precondition: the replay emitted states"
        assert result.daily_states[-1].cumulative_external_cash_flow == Decimal("1120"), "precondition: every deposit is replayed, the 0001-01-01 one included"
        assert _rows_before_floor_of(result) == _rows_before_floor_record()(count=2, earliest=DAY_ONE)
        print_success("RowsBeforeFloor(count=2, earliest=0001-01-01)")

    @pytest.mark.asyncio
    async def test_a_book_from_the_floor_on_has_none(self, session):
        """A deposits 1000 on 1900-01-01 exactly and buys 10 X on 1900-01-02: nothing before the floor, None — not a
        record counting 0."""
        print_section("MF-SEC8-2a: a book from the floor on")
        user_id, (broker_a,), asset_id = await _owner_of(session, "SEC8-2a A")
        session.add_all([_deposit(broker_a, FLOOR), _buy(broker_a, asset_id, date(1900, 1, 2))])
        await session.commit()

        result = await PortfolioCalculationEngine(session).calculate(user_id=user_id, date_to=END, target_currency="EUR")

        assert [state.date for state in result.daily_states][:1] == [FLOOR], "precondition: the replay emitted states from the floor"
        assert _rows_before_floor_of(result) is None
        print_success("rows_before_floor is None")

    @pytest.mark.asyncio
    async def test_only_the_scope_s_rows_are_counted(self, session):
        """U owns A (a deposit on 0001-01-01, a BUY on 1890-01-01) and B (a deposit on 1850-06-01, one on 1900-01-03).
        Scope B: one row, on 1850-06-01 — A's rows are not in B's histories, so they are not B's warning. The whole
        scope: three, the earliest on 0001-01-01."""
        print_section("MF-SEC8-2a: rows before the floor, per scope")
        user_id, (broker_a, broker_b), asset_id = await _owner_of(session, "SEC8-2a A", "SEC8-2a B")
        session.add_all([_deposit(broker_a, DAY_ONE), _buy(broker_a, asset_id, OLD), _deposit(broker_b, date(1850, 6, 1)), _deposit(broker_b, date(1900, 1, 3))])
        await session.commit()
        engine = PortfolioCalculationEngine(session)
        record = _rows_before_floor_record()

        only_b = await engine.calculate(user_id=user_id, broker_ids=[broker_b], date_to=END, target_currency="EUR")
        both = await engine.calculate(user_id=user_id, date_to=END, target_currency="EUR")

        assert (_rows_before_floor_of(only_b), _rows_before_floor_of(both)) == (record(count=1, earliest=date(1850, 6, 1)), record(count=3, earliest=DAY_ONE))
        print_success("B: 1 from 1850-06-01; A and B: 3 from 0001-01-01")
