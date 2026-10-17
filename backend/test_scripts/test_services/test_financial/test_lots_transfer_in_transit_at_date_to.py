"""J-47 — a lots analysis keeps a TRANSFER still in transit on ``date_to`` in transit: departed, not yet arrived.

Workstream J «Numeri e analisi», release 1.3: the service-level reds and guards T1–T7 of the lot, through
``lots_analysis_service.get_lots_analysis``. The engine option is pinned in ``test_financial_math/test_fifo_replay_until.py``;
T8, the AI Export, beside the ``*.fifo_summary`` tests (``test_ai_export_portfolio_fifo_summary_in_transit.py``).

TODAY (base ``497aaa07c``) ``LotsAnalysisService._load_transactions`` cuts the ledger at ``date_to``. A transfer in transit
on that day (departure ≤ ``date_to`` < arrival) loses its arriving leg, the engine cannot pair the other one
(``FifoLotEngine._resolve_transfer_pair``) and answers TRANSFER_PAIR_MISSING — FAILED — even over both brokers of the pair
(``broker_ids`` None or [A, B]), where J-10's boundary reading does not apply: the partner sits INSIDE the scope. The
engine's transit window is [min(dates), max(dates)), so a pair whose receiving leg is dated before its giving leg is cut
the same way. The PERFORMANCE_HISTORY re-run over the accessible brokers (``broker_ids`` given, more brokers accessible)
has the same cut.

THE RULE (coordinator, 17/10; as the Dashboard, which loads the whole pair and keeps the units in transit from departure
to arrival). The service loads, by id, the partner legs of the in-scope TRANSFER rows that sit at an in-scope broker and
are dated after ``date_to``, and hands them to the ENGINE ONLY — never to the list the histories, the WAC lines and the
conversions read —; the engine replays until ``date_to`` (``replay_until``): the arrival after ``date_to`` is dropped and
the units stay IN_TRANSIT (``end_date`` None) on ``date_to``. With a single-broker scope and the partner outside it,
J-10's boundary reading still applies (``test_lots_transfer_scope_boundary.py``, R11): unchanged. An open transit has
no arrival, in the events nor in the custody history (T1–T3): today ``LotsAnalysisService._build_transfer_rows`` writes,
for a transit fragment without an end, a TRANSFER_ARRIVE on its departure day (``fragment.end_date if … else
fragment.start_date``), so dropping the engine's event alone leaves that row.

LEDGER L2 (``backend/test_scripts/test_services/_scope_boundary_books.py``): A buys 10 at 100 on 10 Jan 2025 and sends
them to B on 12 Jan; B's leg is dated 16 Jan with a cost basis of 100 a unit; closes 100, 110, 120, 125, 130, 135, 140
from 10 to 16 Jan. Read on 14 Jan the 10 units are in transit, worth 10 × 130 = 1300. U owns A and B. Dates in 2025, so
R13-SEC7-1's bound (``latest_range_end``, tomorrow) never clamps them.

Rows are written straight into the session and rolled back; each test owns its users, brokers and asset. No FX:
everything is in EUR.
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Transaction, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._scope_boundary_books import (
    L2_ARRIVAL_DAY,
    L2_BUY_DAY,
    L2_DATE_TO,
    L2_DEPARTURE_DAY,
    LedgerL2,
    grant_owner,
    new_user,
    seed_l2,
)

D = Decimal
SUMMARY = LotAnalysisType.LOT_SUMMARY
EVENTS = LotAnalysisType.EVENT_HISTORY
CUSTODY = LotAnalysisType.CUSTODY_HISTORY
GANTT = LotAnalysisType.GANTT_TOPOLOGY
PERFORMANCE = LotAnalysisType.PERFORMANCE_HISTORY
BROKER_WAC = LotAnalysisType.BROKER_WAC_HISTORY
CUMULATIVE_WAC = LotAnalysisType.CUMULATIVE_WAC_HISTORY
_READING = [SUMMARY, EVENTS, CUSTODY, GANTT]
# T3: the receiving leg is dated before the giving one; the transit window opens on 11 Jan and closes on 15 Jan.
T3_IN_DAY = date(2025, 1, 11)
T3_OUT_DAY = date(2025, 1, 15)
T3_DATE_TO = date(2025, 1, 13)  # the market says 125
T5_DATE_TO = date(2025, 1, 17)  # after the arrival: 140, carried from 16 Jan


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


# --------------------------------------------------------------------------- #
# Readings
# --------------------------------------------------------------------------- #


async def _analysis(session: AsyncSession, user: User, asset: Asset, *, broker_ids: list[int] | None, analyses: list[LotAnalysisType], date_to: date = L2_DATE_TO) -> LotsAnalysisResponse:
    return await get_lots_analysis(
        session=session,
        user_id=user.id,
        asset_id=asset.id,
        broker_ids=broker_ids,
        date_from=None,
        date_to=date_to,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=analyses,
    )


def _issue_codes(result: LotsAnalysisResponse) -> list[str]:
    """The distinct issue codes of the analysis, sorted."""
    return sorted({str(issue.code) for issue in (result.data_quality.issues if result.data_quality else [])})


def _dated_after(result: LotsAnalysisResponse, day: date) -> list[tuple]:
    """Every row of the response dated after ``day``: lots, events, custody rows, Gantt segments and history points."""
    rows: list[tuple] = []
    for lot in result.lots or []:
        rows.extend(("lot", lot.lot_id, name, value) for name, value in (("opening_date", lot.opening_date), ("closing_date", lot.closing_date)) if value is not None and value > day)
    for name in ("lot_events", "custody_history", "value_history", "return_history", "price_history", "broker_wac_history", "cumulative_wac_history", "performance_history", "income_events"):
        rows.extend((name, getattr(row, "kind", None), row.date) for row in getattr(result, name) or [] if row.date > day)
    for segment in result.gantt_segments or []:
        if segment.start_date > day or (segment.end_date is not None and segment.end_date > day):
            rows.append(("gantt", segment.fragment_id, segment.start_date, segment.end_date))
    return rows


def _reading(result: LotsAnalysisResponse, *, date_to: date) -> dict:
    """What a reader of the asset sees: status, issues, lots (custody included), Gantt, events, custody history."""
    return {
        "status": result.calculation_status,
        "issue codes": _issue_codes(result),
        "lots": [
            {
                "lot_id": lot.lot_id,
                "opening_broker_id": lot.opening_broker_id,
                "open_quantity": lot.open_quantity,
                "realized_quantity": lot.realized_quantity,
                "realized_pnl": lot.realized_pnl,
                "open_value": lot.open_value,
                "states": sorted(lot.states),
                # (custody, broker, quantity): an in-transit slice names no broker
                "current_custody": [(str(slice_.custody_type), slice_.broker_id, slice_.quantity) for slice_ in lot.current_custody],
            }
            for lot in sorted(result.lots or [], key=lambda lot: lot.lot_id)
        ],
        # (custody, broker, source, destination, quantity, start, end)
        "gantt": sorted(
            ((str(s.custody_type), s.broker_id, s.source_broker_id, s.destination_broker_id, s.quantity, s.start_date, s.end_date) for s in result.gantt_segments or []),
            key=lambda segment: (segment[5], segment[0]),
        ),
        # (date, kind, source, destination)
        "events": [(event.date, str(event.kind), event.source_broker_id, event.destination_broker_id) for event in result.lot_events or []],
        "custody history": [(event.date, str(event.kind)) for event in result.custody_history or []],
        "dated after date_to": _dated_after(result, date_to),
    }


def _in_transit(book: LedgerL2, *, departs_on: date, open_value: str) -> dict:
    """The reading of L2 while its 10 units are in transit: COMPLETE, no issue; A's BUY lot keeps its 10 units, nothing
    realized, valued at the reading day's price; one IN_TRANSIT slice of 10 (no broker); in the Gantt the A segment ends on
    the departure and the transit segment from A to B is open; the departure is an event, the arrival is not."""
    a, b = book.broker_a.id, book.broker_b.id
    return {
        "status": "COMPLETE",
        "issue codes": [],
        "lots": [
            {
                "lot_id": book.buy.id,
                "opening_broker_id": a,
                "open_quantity": D("10"),
                "realized_quantity": D("0"),
                "realized_pnl": D("0"),
                "open_value": D(open_value),
                "states": ["IN_TRANSIT", "LONG", "OPEN"],
                "current_custody": [("IN_TRANSIT", None, D("10"))],
            }
        ],
        "gantt": [("BROKER", a, None, None, D("10"), L2_BUY_DAY, departs_on), ("IN_TRANSIT", None, a, b, D("10"), departs_on, None)],
        "events": [(L2_BUY_DAY, "BUY", None, None), (departs_on, "TRANSFER_DEPART", a, b)],
        "custody history": [(L2_BUY_DAY, "BUY"), (departs_on, "TRANSFER_DEPART")],
        "dated after date_to": [],
    }


# --------------------------------------------------------------------------- #
# T1–T3: the transfer in transit on date_to, over both brokers of the pair
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_t1_a_transfer_in_transit_on_date_to_stays_in_transit_over_every_broker(session):
    """T1 — U without a filter (A and B): the pair departed on 12 Jan and arrives on 16 Jan, after ``date_to``, 14 Jan.
    COMPLETE, no issue; one lot, A's BUY: 10 open, nothing realized, worth 10 × 130 = 1300; its whole quantity IN_TRANSIT
    from A to B (one current custody slice, no broker; the Gantt's A segment ends on 12 Jan, the transit one is open);
    TRANSFER_DEPART on 12 Jan and no TRANSFER_ARRIVE, in the events and in the custody history; nothing after 14 Jan.

    Today: FAILED, issue codes [TRANSFER_PAIR_MISSING]; the BUY lot still open with its 10 units, nothing realized, worth
    1300, states [LONG, OPEN], custody one BROKER slice of 10 at A; one Gantt segment at A from 10 Jan, open; events and
    custody history only the BUY of 10 Jan; nothing dated after 14 Jan.
    """
    book = await seed_l2(session)

    result = await _analysis(session, book.owner, book.asset, broker_ids=None, analyses=_READING)

    assert _reading(result, date_to=L2_DATE_TO) == _in_transit(book, departs_on=L2_DEPARTURE_DAY, open_value="1300")


@pytest.mark.asyncio
async def test_t2_the_same_with_both_brokers_named(session):
    """T2 — T1 with ``broker_ids=[A, B]`` named explicitly: the same reading, COMPLETE, the lot IN_TRANSIT from 12 Jan.

    Today: the same as T1's — FAILED, issue codes [TRANSFER_PAIR_MISSING]; the BUY lot still open with its 10 units,
    nothing realized, worth 1300, states [LONG, OPEN], custody one BROKER slice of 10 at A; one Gantt segment at A from
    10 Jan, open; events and custody history only the BUY of 10 Jan.
    """
    book = await seed_l2(session)

    result = await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_a.id, book.broker_b.id], analyses=_READING)

    assert _reading(result, date_to=L2_DATE_TO) == _in_transit(book, departs_on=L2_DEPARTURE_DAY, open_value="1300")


@pytest.mark.asyncio
async def test_t3_a_receiving_leg_dated_before_the_giving_one_is_in_transit_from_its_own_day(session):
    """T3 — the reverse order: B's receiving leg is dated 11 Jan (cost basis 100), A's giving leg 15 Jan; U reads every
    broker on 13 Jan. The engine's window is [11 Jan, 15 Jan), so on 13 Jan the 10 units are in transit since 11 Jan:
    COMPLETE, no issue; TRANSFER_DEPART on 11 Jan (A → B), no arrival; the lot worth 10 × 125 = 1250.

    Today: FAILED, issue codes [TRANSFER_PAIR_MISSING] (B's leg without its partner, cut at 13 Jan); the BUY lot still
    open with its 10 units at A (BROKER custody), worth 1250, states [LONG, OPEN]; one Gantt segment at A, open; only the
    BUY in the events.
    """
    book = await seed_l2(session, out_day=T3_OUT_DAY, in_day=T3_IN_DAY)

    result = await _analysis(session, book.owner, book.asset, broker_ids=None, analyses=_READING, date_to=T3_DATE_TO)

    assert _reading(result, date_to=T3_DATE_TO) == _in_transit(book, departs_on=T3_IN_DAY, open_value="1250")


# --------------------------------------------------------------------------- #
# T4: PERFORMANCE_HISTORY — the owner's re-run = the co-owner's boundary reading
# --------------------------------------------------------------------------- #


def _series(result: LotsAnalysisResponse) -> list[tuple]:
    return [(point.date, point.roi, point.twrr) for point in result.performance_history or []]


@pytest.mark.asyncio
async def test_t4_the_owner_filtering_the_sender_reads_the_performance_of_the_co_owner_who_sees_it_alone(session):
    """T4 — PERFORMANCE_HISTORY on 14 Jan. U filters A (``broker_ids=[A]``) but can access B, so the service re-runs the
    FIFO over A and B; with the late leg paired the units leave A on 12 Jan and the external-transfer branch moves their
    market value out (10 × 120). W, OWNER of A only, reads every broker it sees — A — so J-10's boundary reading moves the
    same value out on the same day. The two series must be the same: same dates, every ``roi`` and ``twrr`` equal. W's is
    the reference (its analysis COMPLETE, its series with values — the precondition, green today).

    Today: the re-run cannot pair the transfer (B's leg cut at 14 Jan), so U's units never leave A: U reads roi 0.2, 0.25,
    0.3 and twrr 0.2, 0.25, 0.3 from 12 to 14 Jan, where W reads roi 0, 0, 0 and twrr 0.2, 0.2, 0.2 (10 and 11 Jan agree).
    """
    book = await seed_l2(session)
    co_owner = await new_user(session, "co_owner_of_a")
    await grant_owner(session, book.broker_a, co_owner)

    owners_result = await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_a.id], analyses=[PERFORMANCE])
    co_owners_result = await _analysis(session, co_owner, book.asset, broker_ids=None, analyses=[PERFORMANCE])
    owners, co_owners = _series(owners_result), _series(co_owners_result)

    # Precondition, green today: the reference is a COMPLETE analysis whose series has values.
    assert co_owners_result.calculation_status == "COMPLETE", _issue_codes(co_owners_result)
    assert any(roi is not None for _day, roi, _twrr in co_owners) and any(twrr is not None for _day, _roi, twrr in co_owners), co_owners
    assert owners == co_owners, f"owner    {owners}\nco-owner {co_owners}"


# --------------------------------------------------------------------------- #
# T5–T7: guards
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_t5_guard_read_after_the_arrival_the_transfer_has_arrived(session):
    """T5 — GUARD (green today and after): U reads every broker on 17 Jan, after the arrival. COMPLETE, no issue; the lot
    at B (one BROKER slice of 10), worth 10 × 140 = 1400; the Gantt goes A, transit from 12 to 16 Jan, B; TRANSFER_DEPART
    on 12 Jan and TRANSFER_ARRIVE on 16 Jan.
    """
    book = await seed_l2(session)
    a, b = book.broker_a.id, book.broker_b.id

    result = await _analysis(session, book.owner, book.asset, broker_ids=None, analyses=_READING, date_to=T5_DATE_TO)

    assert _reading(result, date_to=T5_DATE_TO) == {
        "status": "COMPLETE",
        "issue codes": [],
        "lots": [
            {
                "lot_id": book.buy.id,
                "opening_broker_id": a,
                "open_quantity": D("10"),
                "realized_quantity": D("0"),
                "realized_pnl": D("0"),
                "open_value": D("1400"),
                "states": ["LONG", "OPEN"],
                "current_custody": [("BROKER", b, D("10"))],
            }
        ],
        "gantt": [
            ("BROKER", a, None, None, D("10"), L2_BUY_DAY, L2_DEPARTURE_DAY),
            ("IN_TRANSIT", None, a, b, D("10"), L2_DEPARTURE_DAY, L2_ARRIVAL_DAY),
            ("BROKER", b, None, None, D("10"), L2_ARRIVAL_DAY, None),
        ],
        "events": [(L2_BUY_DAY, "BUY", None, None), (L2_DEPARTURE_DAY, "TRANSFER_DEPART", a, b), (L2_ARRIVAL_DAY, "TRANSFER_ARRIVE", a, b)],
        "custody history": [(L2_BUY_DAY, "BUY"), (L2_DEPARTURE_DAY, "TRANSFER_DEPART"), (L2_ARRIVAL_DAY, "TRANSFER_ARRIVE")],
        "dated after date_to": [],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("late_leg_cost", ["100", None], ids=["late-leg-with-cost", "late-leg-without-cost"])
async def test_t6_guard_the_late_leg_never_reaches_the_wac_lines(session, late_leg_cost):
    """T6 — GUARD (green today and after): U reads every broker's WAC lines on 14 Jan. The late leg goes to the engine
    only: A's line starts on 10 Jan with 10 at 100 (positive control: the lines are drawn), B has no point (B has received
    nothing yet), no point of either line is dated after 14 Jan, and no MISSING_COST_BASIS.

    The last check is the one that can see a leak. Within the window a leg dated 16 Jan changes no point (each point is
    the pool on its day), so the late leg is also written WITHOUT a cost basis (``late-leg-without-cost``): reaching the
    average-cost lines, it would make them report an acquisition of unknown cost — MISSING_COST_BASIS, as R12 of J-10.
    """
    book = await seed_l2(session, in_leg_cost=late_leg_cost)
    a, b = book.broker_a.id, book.broker_b.id

    result = await _analysis(session, book.owner, book.asset, broker_ids=None, analyses=[BROKER_WAC, CUMULATIVE_WAC])

    broker_points = result.broker_wac_history or []
    cumulative_points = result.cumulative_wac_history or []
    assert {
        "A's first point": next(((point.date, point.wac, point.pool_qty) for point in broker_points if point.broker_id == a), None),
        "first cumulative point": next(((point.date, point.wac, point.pool_qty) for point in cumulative_points), None),
        "B's points": [point.date for point in broker_points if point.broker_id == b],
        "points after date_to": [(point.broker_id, point.date) for point in broker_points if point.date > L2_DATE_TO] + [("cumulative", point.date) for point in cumulative_points if point.date > L2_DATE_TO],
        "MISSING_COST_BASIS": "MISSING_COST_BASIS" in _issue_codes(result),
    } == {
        "A's first point": (L2_BUY_DAY, D("100"), D("10")),
        "first cumulative point": (L2_BUY_DAY, D("100"), D("10")),
        "B's points": [],
        "points after date_to": [],
        "MISSING_COST_BASIS": False,
    }


def _leg_columns(leg: Transaction) -> dict:
    return {
        "type": leg.type,
        "date": leg.date,
        "quantity": leg.quantity,
        "amount": leg.amount,
        "currency": leg.currency,
        "cost_basis_override": leg.cost_basis_override,
        "cost_basis_currency": leg.cost_basis_currency,
        "related_transaction_id": leg.related_transaction_id,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["every-broker", "the-sender-with-the-accessible-re-run"])
async def test_t7_guard_the_analysis_writes_nothing_and_ends_on_date_to(session, scope):
    """T7 — GUARD (green today and after): U asks for every analysis on 14 Jan — over every broker, and filtering A,
    which adds the PERFORMANCE_HISTORY re-run over A and B. The ORM rows are never touched (both legs' columns as
    written, nothing dirty or new in the session), the metadata still ends on 14 Jan (requested and computed, the
    computed range from 10 Jan), and no row of the response is dated after 14 Jan.
    """
    book = await seed_l2(session)
    broker_ids = None if scope == "every-broker" else [book.broker_a.id]
    columns_before = {"A's leg": _leg_columns(book.out_leg), "B's leg": _leg_columns(book.in_leg)}
    assert not session.dirty and not session.new  # precondition: the book is flushed

    result = await _analysis(session, book.owner, book.asset, broker_ids=broker_ids, analyses=list(LotAnalysisType))

    metadata = result.calculation_metadata
    assert {
        "dirty": list(session.dirty),
        "new": list(session.new),
        "columns": {"A's leg": _leg_columns(book.out_leg), "B's leg": _leg_columns(book.in_leg)},
        "requested_date_to": metadata.requested_date_to,
        "computed range": (metadata.computed_date_from, metadata.computed_date_to),
        "dated after date_to": _dated_after(result, L2_DATE_TO),
    } == {
        "dirty": [],
        "new": [],
        "columns": columns_before,
        "requested_date_to": L2_DATE_TO,
        "computed range": (L2_BUY_DAY, L2_DATE_TO),
        "dated after date_to": [],
    }
