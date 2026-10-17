"""MF-D4 (workstream MF), the ledger half: a SPLIT asset event stored with an invalid ratio counts as missing, never raises.

Measured before the cure (HEAD 4c767685f), on the ledger below with the SPLIT's ratio stored as 0, -2 or a value that
reads back as None (a stored ±inf: ``RealDecimal`` reads it as no value, W-B58):

* ``PortfolioCalculationEngine.calculate`` raises ``ValueError("SPLIT AssetEvent … must have a positive finite ratio")``
  (``financial_math/portfolio/engine.py``, step 3b), so ``PortfolioService.get_summary`` and ``get_report`` raise and
  ``GET /portfolio/summary`` / ``POST /portfolio/report`` answer 500 for that user;
* the lots analysis (``LotsAnalysisService`` → ``FifoLotEngine._apply_split``) applies the ratio and raises:
  ``DivisionByZero`` for 0, ``AssertionError("Lot cost invariant violated")`` for -2, ``ValueError`` (``_require_decimal``)
  for None (measured on the FIFO engine alone, ``test_portfolio_engine/test_invalid_split_ratio.py``);
* Yield on Cost already treats such a broker as invalid (``yield_on_cost._index_split_records``): unavailable,
  ``INVALID_SPLIT``. Unchanged by this lot: its test here is a parity pin, green before and after.

The contract (option a, the developer's decision through the coordinator, agreed with J). The event's linked ADJUSTMENT
rows stay the split's rescale — still in ``split_linked_tx_ids``: the position's cost is kept, they are never in-kind
capital, never ``missing_cost_basis`` — and only the ratio is dropped:

* no ``SplitRecord`` in the split history, so a price observed before the split is not restated by it (the holding's
  last-trade mark keeps the BUY's unit price, ``valuation_split_adjusted`` False);
* ``PortfolioCalculationResult.invalid_split_events == [InvalidSplitEvent(event_id, asset_id, date)]``, one per event
  (an event linked on two brokers is one), by event id;
* the data-quality report of the summary and of the report (with or without the summary) holds one WARNING
  ``INVALID_SPLIT_RATIO`` naming the asset (count = assets, not events), and no ``MISSING_COST_BASIS``;
* the lots analysis skips that SPLIT: no SPLIT row, no ADJUSTMENT_IN (the row is still split-linked), the lots not
  rescaled, nothing raised;
* guards: the same ledger with a ratio of 2 keeps its split effect (restated mark, rescaled lot) and gets no warning.

The ledger, per broker, all in EUR: DEPOSIT 1000 on D0, BUY 10 for 1000 on D1 (100 a unit), then on SPLIT_DAY a SPLIT
event of the asset and its linked ADJUSTMENT of +10 — costless, or carrying a cost basis of 50 a unit (a cost the rescale
ignores: unlinked, that row would add 500 of cost and of in-kind capital, which is what makes the "still split-linked"
assertions discriminate). No price row: the holding is valued at its last trade, the BUY's, which the split history
restates when it holds the split. Read as of END. Yield on Cost needs a dividend before the split and a year of history:
its ledger is its own (BUY 2024-01-01, DIVIDEND 2025-05-01, SPLIT 2025-06-01, as ``test_yield_on_cost.py``).

The stored rows bypass the write path on purpose (X-R47 refuses a new SPLIT of 0 or below): ``AssetEvent`` and
``Transaction`` are added through the session, as every engine test seeds them; a ratio that reads as None is stored as
SQLite's ``Inf`` by a raw ``UPDATE`` (``RealDecimal`` refuses to write it), and a precondition reads it back as None.

A call that raises where the contract answers fails its test naming the exception (red, never an error). Every name of
the cure (``InvalidSplitEvent``, ``invalid_split_events``, the issue code) is read when the test runs, so the module
collects before the cure, and the guards run.

Isolation: WRITE-SCOPED, the services default. Each test owns its user, broker(s) and asset, named with a uuid, and writes
only through a session that is rolled back: nothing is committed, so nothing is left behind. Everything is read by the
test's own ids — the positions by (asset, broker), the issue's assets are the only asset its user holds — and nothing
counts a collection the test does not own. The portfolio caches (L1 blob, L2 report) are keyed by the user and by the
transactions' ids and ``updated_at``, so a rolled-back neighbour's entry never answers here. No price, FX rate or network.
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

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.models as portfolio_models
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import IssueDomain, IssueSeverity, PortfolioReportQuery, YieldOnCostStatus, YieldOnCostUnavailableReason
from backend.app.services.financial_math.average_cost import CostEffect
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.yield_on_cost import YieldOnCostPositionInput, calculate_yield_on_cost_for_positions
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.app.services.portfolio_service import PortfolioService

EUR = "EUR"
D0 = date(2025, 1, 2)  # DEPOSIT 1000
D1 = date(2025, 1, 3)  # BUY 10 for 1000
SPLIT_DAY = date(2025, 1, 8)  # the SPLIT event and its linked ADJUSTMENT +10
LATER_SPLIT_DAY = date(2025, 1, 9)  # a second SPLIT event, for the «count = assets» case
END = date(2025, 1, 10)
DEPOSIT = Decimal("1000")
BOUGHT = Decimal("10")
PAID = Decimal("1000")
BUY_UNIT_PRICE = Decimal("100")

INVALID_SPLIT_RATIO = "INVALID_SPLIT_RATIO"
MISSING_COST_BASIS = "MISSING_COST_BASIS"

#: The stored ratios that count as missing. None: a value that reads back as None, stored as SQLite's Inf (see module
#: docstring). As text, the way they are written.
INVALID_RATIOS = [
    pytest.param("0", id="zero"),
    pytest.param("-2", id="negative"),
    pytest.param(None, id="stored-inf-reads-none"),
]
#: The split row's cost basis: none (what the Auto mode stores), or 50 a unit (ignored by a rescale, 500 of cost and of
#: in-kind capital if the row were not split-linked).
SPLIT_ROW_COST_BASES = [pytest.param(None, id="costless-row"), pytest.param("50", id="priced-row")]


# =============================================================================
# FIXTURES & LEDGER
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as db:
        yield db
        await db.rollback()


@dataclass(frozen=True)
class _Book:
    user_id: int
    broker_ids: tuple[int, ...]
    asset_id: int
    asset_name: str
    event_ids: tuple[int, ...]
    #: (broker_id, transaction id) of every split-linked ADJUSTMENT
    split_rows: tuple[tuple[int, int], ...]


async def _owned_scope(session: AsyncSession, label: str, *, brokers: int = 1) -> tuple[int, list[int], int, str]:
    """A user of the test's own, OWNER at 100 % of ``brokers`` brokers of its own, and an EUR stock of its own."""
    tag = uuid4().hex
    user = User(username=f"mfd4_{label}_{tag}", email=f"mfd4_{label}_{tag}@test.invalid", hashed_password="not-used", is_active=True)
    broker_rows = [Broker(name=f"MF-D4 {label} {index} {tag}") for index in range(brokers)]
    asset = Asset(display_name=f"MF-D4 {label} {tag}", currency=EUR, asset_type=AssetType.STOCK)
    session.add_all([user, *broker_rows, asset])
    await session.flush()
    session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in broker_rows])
    await session.flush()
    return user.id, [broker.id for broker in broker_rows], asset.id, asset.display_name


async def _store_split_event(session: AsyncSession, asset_id: int, on: date, ratio: str | None) -> int:
    """A SPLIT event of ``asset_id`` stored with ``ratio`` as is — around the write path, which refuses 0 or below.

    None stores SQLite's Inf, which ``RealDecimal`` cannot write and reads back as None; the ORM object is then
    expunged, so no later read in this session is answered from the identity map. A precondition reads the stored
    ratio back as the engine's loader will see it."""
    event = AssetEvent(asset_id=asset_id, date=on, type=AssetEventType.SPLIT, value=Decimal("1") if ratio is None else Decimal(ratio), currency=EUR)
    session.add(event)
    await session.flush()
    event_id = event.id
    if ratio is None:
        await session.execute(text("UPDATE asset_events SET value = 9e999 WHERE id = :event_id"), {"event_id": event_id})
        session.expunge(event)
    stored = (await session.execute(select(AssetEvent.value).where(AssetEvent.id == event_id))).scalar_one()
    expected = None if ratio is None else Decimal(ratio)
    assert stored == expected, f"precondition: SPLIT event {event_id} reads back with ratio {stored!r}, expected {expected!r}"
    return event_id


async def _book(
    session: AsyncSession,
    label: str,
    *,
    splits: list[tuple[date, str | None, str]],
    brokers: int = 1,
    split_row_cost_basis: str | None = None,
) -> _Book:
    """On each broker: DEPOSIT 1000 on D0, BUY 10 for 1000 on D1; for each (day, ratio, quantity) of ``splits`` one SPLIT
    event of the asset on that day, and on each broker an ADJUSTMENT of ``quantity`` linked to it, carrying
    ``split_row_cost_basis`` EUR a unit or no cost basis."""
    user_id, broker_ids, asset_id, asset_name = await _owned_scope(session, label, brokers=brokers)
    event_ids = [await _store_split_event(session, asset_id, day, ratio) for day, ratio, _quantity in splits]
    for broker_id in broker_ids:
        session.add_all(
            [
                Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=D0, amount=DEPOSIT, currency=EUR),
                Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=D1, quantity=BOUGHT, amount=-PAID, currency=EUR),
            ]
        )
    await session.flush()
    split_rows: list[tuple[int, int]] = []
    for event_id, (day, _ratio, quantity) in zip(event_ids, splits, strict=True):
        for broker_id in broker_ids:
            row = Transaction(
                broker_id=broker_id,
                asset_id=asset_id,
                asset_event_id=event_id,
                type=TransactionType.ADJUSTMENT,
                date=day,
                quantity=Decimal(quantity),
                amount=Decimal("0"),
                currency=EUR,
                cost_basis_override=None if split_row_cost_basis is None else Decimal(split_row_cost_basis),
                cost_basis_currency=None if split_row_cost_basis is None else EUR,
            )
            session.add(row)
            await session.flush()
            split_rows.append((broker_id, row.id))
    return _Book(user_id=user_id, broker_ids=tuple(broker_ids), asset_id=asset_id, asset_name=asset_name, event_ids=tuple(event_ids), split_rows=tuple(split_rows))


# =============================================================================
# CALLS — an exception where the contract answers is the finding, reported as a failure
# =============================================================================


async def _calculate(session: AsyncSession, book: _Book):
    try:
        return await PortfolioCalculationEngine(session).calculate(user_id=book.user_id, date_to=END, target_currency=EUR)
    except Exception as exc:  # noqa: BLE001 — the contract is «never raises»: any exception is the finding
        pytest.fail(f"PortfolioCalculationEngine.calculate raised {exc!r}: the Dashboard answers 500 (MF-D4: a SPLIT with an invalid ratio counts as missing)")


async def _summary(session: AsyncSession, book: _Book):
    try:
        return await PortfolioService(session).get_summary(user_id=book.user_id, target_currency_override=EUR, date_to=END)
    except Exception as exc:  # noqa: BLE001 — as above
        pytest.fail(f"PortfolioService.get_summary raised {exc!r}: GET /portfolio/summary answers 500 (MF-D4)")


async def _report(session: AsyncSession, book: _Book, *, include_summary: bool):
    query = PortfolioReportQuery(
        target_currency=EUR,
        include_summary=include_summary,
        include_history=False,
        include_allocation_history=False,
        date_range={"start": D0.isoformat(), "end": END.isoformat()},
    )
    try:
        return await PortfolioService(session).get_report(book.user_id, query)
    except Exception as exc:  # noqa: BLE001 — as above
        pytest.fail(f"PortfolioService.get_report(include_summary={include_summary}) raised {exc!r}: POST /portfolio/report answers 500 (MF-D4)")


async def _lots(session: AsyncSession, book: _Book):
    try:
        return await get_lots_analysis(
            session=session,
            user_id=book.user_id,
            asset_id=book.asset_id,
            broker_ids=list(book.broker_ids),
            date_from=None,
            date_to=END,
            target_currency=EUR,
            selected_lot_ids=None,
            requested_analyses=["LOT_SUMMARY", "EVENT_HISTORY"],
        )
    except Exception as exc:  # noqa: BLE001 — as above
        pytest.fail(f"get_lots_analysis raised {exc!r}: POST /portfolio/lots/analysis answers 500 (MF-D4: skip a SPLIT with an invalid ratio)")


def _invalid_split_event(event_id: int, asset_id: int, on: date):
    cls = getattr(portfolio_models, "InvalidSplitEvent", None)
    if cls is None:
        pytest.fail("financial_math.portfolio.models has no InvalidSplitEvent (MF-D4)")
    return cls(event_id=event_id, asset_id=asset_id, date=on)


def _invalid_split_events(result) -> list:
    if not hasattr(result, "invalid_split_events"):
        pytest.fail("PortfolioCalculationResult has no invalid_split_events (MF-D4)")
    return list(result.invalid_split_events)


def _issues(report, code: str) -> list:
    return [issue for issue in report.issues if str(issue.code) == code]


def _position_end(result, book: _Book, broker_id: int):
    positions = [position for position in result.position_states_end if position.asset_id == book.asset_id and position.broker_id == broker_id]
    assert len(positions) == 1, f"the end positions of asset {book.asset_id} on broker {broker_id}: {positions}"
    return positions[0]


def _assert_the_split_rows_stay_the_rescale(result, book: _Book, *, quantity: Decimal) -> None:
    """The split-linked rows are still the rescale: each position holds ``quantity`` at its BUY's cost, every split row is a
    SPLIT_RESCALE step, nothing of unknown cost, and the capital baseline stays the deposits on every day."""
    for broker_id in book.broker_ids:
        average_cost = result.average_costs[(book.asset_id, broker_id)]
        assert average_cost.quantity == quantity, f"broker {broker_id}: the position holds {average_cost.quantity}, the rows say {quantity}"
        assert average_cost.cost_report == PAID, f"broker {broker_id}: the position's cost is {average_cost.cost_report}, the BUY's is {PAID}: a split row moved it"
        assert average_cost.unknown_cost_movement_ids == (), f"broker {broker_id}: rows of unknown cost {average_cost.unknown_cost_movement_ids}: a split row became an acquisition (MISSING_COST_BASIS)"
        for row_broker_id, row_id in book.split_rows:
            if row_broker_id == broker_id:
                step = average_cost.step_for(row_id)
                assert step is not None and step.effect == CostEffect.SPLIT_RESCALE, f"split row {row_id}: {step and step.effect}, expected {CostEffect.SPLIT_RESCALE}"
        assert _position_end(result, book, broker_id).quantity == quantity
    capital = {state.cumulative_external_cash_flow for state in result.daily_states}
    assert capital == {DEPOSIT * len(book.broker_ids)}, f"capital baseline over the period: {sorted(capital)}; a split row is never in-kind capital"


# =============================================================================
# 1. ENGINE — the event counts as missing, never raises
# =============================================================================


class TestEngineCountsAnInvalidSplitAsMissing:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("split_row_cost_basis", SPLIT_ROW_COST_BASES)
    @pytest.mark.parametrize("ratio", INVALID_RATIOS)
    async def test_the_event_is_recorded_and_its_row_stays_the_rescale(self, session, ratio, split_row_cost_basis):
        """Red today (ValueError): the engine answers; the event is recorded; its row is still the split's rescale; the
        quantity follows the row; and the BUY's price is not restated by a ratio nobody knows."""
        book = await _book(session, "engine", splits=[(SPLIT_DAY, ratio, "10")], split_row_cost_basis=split_row_cost_basis)

        result = await _calculate(session, book)

        assert _invalid_split_events(result) == [_invalid_split_event(book.event_ids[0], book.asset_id, SPLIT_DAY)]
        _assert_the_split_rows_stay_the_rescale(result, book, quantity=BOUGHT + Decimal("10"))
        position = _position_end(result, book, book.broker_ids[0])
        assert position.valuation_split_adjusted is False, "no SplitRecord: nothing restates the BUY's price"
        assert position.valuation_effective_unit_price == BUY_UNIT_PRICE

    @pytest.mark.asyncio
    async def test_one_event_linked_on_two_brokers_is_recorded_once(self, session):
        """Red today (ValueError): a SPLIT linked by a row on each of two brokers is one InvalidSplitEvent; each row stays
        its broker's rescale."""
        book = await _book(session, "engine-shared", splits=[(SPLIT_DAY, "0", "10")], brokers=2)

        result = await _calculate(session, book)

        assert _invalid_split_events(result) == [_invalid_split_event(book.event_ids[0], book.asset_id, SPLIT_DAY)]
        _assert_the_split_rows_stay_the_rescale(result, book, quantity=BOUGHT + Decimal("10"))

    @pytest.mark.asyncio
    async def test_two_invalid_events_of_one_asset_are_two_records_by_event_id(self, session):
        """Red today (ValueError): two invalid SPLITs of one asset are two records, ordered by event id."""
        book = await _book(session, "engine-two", splits=[(SPLIT_DAY, "0", "10"), (LATER_SPLIT_DAY, "-2", "20")])

        result = await _calculate(session, book)

        assert _invalid_split_events(result) == [
            _invalid_split_event(book.event_ids[0], book.asset_id, SPLIT_DAY),
            _invalid_split_event(book.event_ids[1], book.asset_id, LATER_SPLIT_DAY),
        ]
        _assert_the_split_rows_stay_the_rescale(result, book, quantity=BOUGHT + Decimal("30"))


# =============================================================================
# 2. SERVICE — summary and report answer, with the warning naming the asset
# =============================================================================


def _assert_one_warning_names_the_asset(data_quality, book: _Book) -> None:
    issues = _issues(data_quality, INVALID_SPLIT_RATIO)
    codes = [str(issue.code) for issue in data_quality.issues]
    assert len(issues) == 1, f"expected one {INVALID_SPLIT_RATIO} issue, the report has {codes}"
    issue = issues[0]
    # The user holds one asset, the test's own: the issue's lists are entirely the test's.
    assert issue.domain == IssueDomain.PORTFOLIO
    assert issue.severity == IssueSeverity.WARNING
    assert issue.group_key == "invalid_split_ratio"
    assert issue.message_i18n_key == "dataQuality.invalidSplitRatio"
    assert issue.message_params == {"count": 1}
    assert issue.affected_asset_ids == [book.asset_id]
    assert issue.affected_asset_names == [book.asset_name]
    assert issue.cta_action == "navigate_asset"
    assert issue.cta_target == str(book.asset_id)
    assert _issues(data_quality, MISSING_COST_BASIS) == [], f"the split row is still the rescale, never of unknown cost: {codes}"


class TestPortfolioServiceReportsTheAsset:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("ratio", INVALID_RATIOS)
    async def test_the_summary_answers_with_the_warning(self, session, ratio):
        """Red today (ValueError → 500): the summary answers, its data quality holds one INVALID_SPLIT_RATIO warning
        naming the asset, and the holding follows the rows (20)."""
        book = await _book(session, "summary", splits=[(SPLIT_DAY, ratio, "10")])

        summary = await _summary(session, book)

        _assert_one_warning_names_the_asset(summary.data_quality, book)
        holdings = [holding for holding in summary.holdings if holding.asset_id == book.asset_id]
        assert [holding.quantity for holding in holdings] == [BOUGHT + Decimal("10")]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("include_summary", [pytest.param(True, id="with-summary"), pytest.param(False, id="without-summary")])
    @pytest.mark.parametrize("ratio", INVALID_RATIOS)
    async def test_the_report_answers_with_the_warning(self, session, ratio, include_summary):
        """Red today (ValueError → 500): POST /portfolio/report's service answers, by either of its two data-quality
        paths (the summary's, or its own when the summary is not asked), with the warning; and the body serialises."""
        book = await _book(session, "report", splits=[(SPLIT_DAY, ratio, "10")])

        report = await _report(session, book, include_summary=include_summary)

        assert report.data_quality is not None
        _assert_one_warning_names_the_asset(report.data_quality, book)
        body = report.model_dump(mode="json")
        assert [issue["affected_asset_ids"] for issue in body["data_quality"]["issues"] if issue["code"] == INVALID_SPLIT_RATIO] == [[book.asset_id]]

    @pytest.mark.asyncio
    async def test_two_invalid_events_of_one_asset_count_one_asset(self, session):
        """Red today (ValueError → 500): the warning counts assets, not events — two invalid SPLITs of one asset, count 1."""
        book = await _book(session, "summary-two", splits=[(SPLIT_DAY, "0", "10"), (LATER_SPLIT_DAY, None, "20")])

        summary = await _summary(session, book)

        _assert_one_warning_names_the_asset(summary.data_quality, book)


# =============================================================================
# 3. LOTS — the SPLIT is skipped, the lots not rescaled
# =============================================================================


class TestLotsAnalysisSkipsAnInvalidSplit:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("ratio", INVALID_RATIOS)
    async def test_the_lot_is_not_rescaled_and_nothing_raises(self, session, ratio):
        """Red today (DivisionByZero for 0, AssertionError «Lot cost invariant violated» for -2, ValueError for None): the
        analysis answers; the BUY's lot is the only one and keeps 10 at 100; the split row is neither a SPLIT nor an
        ADJUSTMENT_IN row."""
        book = await _book(session, "lots", splits=[(SPLIT_DAY, ratio, "10")])
        split_row_id = book.split_rows[0][1]

        result = await _lots(session, book)

        assert result.lots is not None
        # The test's own asset on its own broker: the lots are entirely the test's.
        assert [(lot.original_quantity, lot.open_quantity, lot.opening_unit_price, lot.original_cost) for lot in result.lots] == [(BOUGHT, BOUGHT, BUY_UNIT_PRICE, PAID)]
        assert result.lot_events is not None
        row_events = [str(row.kind) for row in result.lot_events if row.transaction_id == split_row_id]
        assert row_events == [], f"the split row became {row_events}: it is skipped (no SPLIT, and still split-linked, no ADJUSTMENT_IN)"


# =============================================================================
# 4. YIELD ON COST — parity pin, green before and after
# =============================================================================


class TestYieldOnCostParity:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("ratio", INVALID_RATIOS)
    async def test_an_invalid_split_makes_the_brokers_yoc_unavailable(self, session, ratio):
        """Green before and after: with a dividend before an invalid SPLIT, Yield on Cost is unavailable, INVALID_SPLIT
        (``_index_split_records``) — MF-D4 changes nothing there."""
        user_id, broker_ids, asset_id, _name = await _owned_scope(session, "yoc")
        broker_id = broker_ids[0]
        event_id = await _store_split_event(session, asset_id, date(2025, 6, 1), ratio)
        session.add_all(
            [
                Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=date(2024, 1, 1), quantity=Decimal("10"), amount=Decimal("-1000"), currency=EUR),
                Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.DIVIDEND, date=date(2025, 5, 1), quantity=Decimal("0"), amount=Decimal("100"), currency=EUR),
                Transaction(broker_id=broker_id, asset_id=asset_id, asset_event_id=event_id, type=TransactionType.ADJUSTMENT, date=date(2025, 6, 1), quantity=Decimal("10"), amount=Decimal("0"), currency=EUR),
            ]
        )
        await session.flush()

        calculations = await calculate_yield_on_cost_for_positions(
            session,
            user_id=user_id,
            positions=[YieldOnCostPositionInput(asset_id=asset_id, broker_id=broker_id, wac_per_unit=Decimal("50"), wac_currency=EUR)],
            target_currency=EUR,
            as_of_date=date(2025, 12, 31),
        )

        result = calculations[(asset_id, broker_id)].result
        assert (result.status, result.reason, result.value) == (YieldOnCostStatus.UNAVAILABLE, YieldOnCostUnavailableReason.INVALID_SPLIT, None)


# =============================================================================
# 5. GUARDS — the same ledger with a valid ratio keeps its split effect, no warning
# =============================================================================


class TestValidSplitParity:
    @pytest.mark.asyncio
    async def test_the_engine_keeps_the_split_record_effect(self, session):
        """Green before and after: ratio 2 — no invalid event, the row the rescale, and the BUY's 100 restated to 50."""
        book = await _book(session, "valid-engine", splits=[(SPLIT_DAY, "2", "10")])

        result = await _calculate(session, book)

        assert getattr(result, "invalid_split_events", []) == []
        _assert_the_split_rows_stay_the_rescale(result, book, quantity=BOUGHT + Decimal("10"))
        position = _position_end(result, book, book.broker_ids[0])
        assert position.valuation_split_adjusted is True
        assert position.valuation_effective_unit_price == BUY_UNIT_PRICE / Decimal("2")

    @pytest.mark.asyncio
    async def test_the_summary_and_report_have_no_invalid_split_warning(self, session):
        """Green before and after: ratio 2 — no INVALID_SPLIT_RATIO issue, nor MISSING_COST_BASIS, in either."""
        book = await _book(session, "valid-summary", splits=[(SPLIT_DAY, "2", "10")])

        summary = await _summary(session, book)
        report = await _report(session, book, include_summary=False)

        for label, data_quality in (("summary", summary.data_quality), ("report", report.data_quality)):
            codes = [str(issue.code) for issue in data_quality.issues]
            assert INVALID_SPLIT_RATIO not in codes, f"{label}: {codes}"
            assert MISSING_COST_BASIS not in codes, f"{label}: {codes}"

    @pytest.mark.asyncio
    async def test_the_lots_are_rescaled(self, session):
        """Green before and after: ratio 2 — the lot holds 20 at 50 for its 1000, and the split row is a SPLIT of 2."""
        book = await _book(session, "valid-lots", splits=[(SPLIT_DAY, "2", "10")])
        split_row_id = book.split_rows[0][1]

        result = await _lots(session, book)

        assert result.lots is not None
        assert [(lot.original_quantity, lot.open_quantity, lot.opening_unit_price, lot.original_cost) for lot in result.lots] == [(Decimal("20"), Decimal("20"), Decimal("50"), PAID)]
        assert result.lot_events is not None
        assert [(str(row.kind), row.ratio) for row in result.lot_events if row.transaction_id == split_row_id] == [("SPLIT", Decimal("2"))]
