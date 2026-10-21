"""Gantt §29, point 2 — a closure row of the lots analysis names the broker its units leave, not the lot's opening one.

Workstream J «Numeri e analisi», release 1.3: the service-level reds C1–C2 and guards C3–C4, through
``lots_analysis_service.get_lots_analysis``. The row builder is pinned on replay doubles by P1–P3 (``test_s29_p*``,
beside ``test_closure_rows_ignore_closures_of_unselected_lots`` in ``test_services/test_lots_analysis_pure.py``).

THE RULE (§29 point 2: the developer's yes, 19/10; the coordinator's go, 20/10). A closure row of
``LotsAnalysisResponse.lot_events`` — a SELL, a BUY that closes a short lot, an ADJUSTMENT_OUT, the exits read at the
scope's edge included — names in ``broker_id`` the broker the units leave: the broker of the fragment it closes
(``LotClosure.fragment_id`` → ``FragmentInterval.broker_id`` of ``engine_result.fragment_intervals``). A fragment id
encodes its place (``FifoLotEngine``: ``lot:{id}/origin:{broker}``, ``…/transfer:{pair}/to:{broker}``, ``…/transit``),
so one id has one broker. A fragment without a broker (in transit: the engine closes none) or an id the replay does not
hold keeps the lot's opening broker. Nothing else changes: kind, quantity, prices, P&L, proceeds, ``fragment_id``,
``scope_boundary`` and the transfer rows. The schema already says so: «Broker directly associated with this event, when
singular» (``LotTimelineEventSchema.broker_id``).

TODAY (base ``c9becf87c``) ``LotsAnalysisService._build_closure_rows`` writes ``broker_id=lot.opening_broker_id``: a lot
opened at A and moved to B shows its closures at A, where its units no longer are, while the Gantt draws the fragment
they leave at B.

LEDGER L1 (``backend/test_scripts/test_services/_scope_boundary_books.py``): A buys 10 at 100 on 10 Jan 2025 and sends
them to B on 12 Jan; B receives them on 13 Jan at a cost basis of 100 a unit and sells 4 at 150 on 15 Jan; read on
16 Jan (150, carried from 15 Jan). U owns A and B.

- C1 — RED. L1 seen whole: the SELL row names B. Today A.
- C2 — RED. L1, a broker C of U's and a TRANSFER pair B → C of 2 units on 16 Jan, read over A and B: B's leg sits at the
  scope's edge (J-10) and reads as an ADJUSTMENT-out at 150; its row (``scope_boundary`` OUT) names B. Today A.
- C3 — GUARD (green today and after). A lot bought and sold at one broker: the SELL row names it.
- C4 — GUARD (green today and after). The transfer rows keep their brokers. L1's transfer has a transit (12 → 13 Jan):
  TRANSFER_DEPART and TRANSFER_ARRIVE are both read off the transit fragment, so both name no broker, A as the source
  and B as the destination. L1 with B's leg dated 12 Jan moves without transit: its one transfer row, TRANSFER_ARRIVE,
  is read off B's fragment and names B, with no source or destination.

Each test first checks, green today, that the analysis is COMPLETE without issue and, for a closure, that the Gantt draws
the fragment it closes (``gantt_segments``, same ``fragment_id``) at the broker expected: a red fails on the row's broker
alone, and no fragment id format is pinned.

Rows are written straight into the session and rolled back; each test owns its users, brokers and asset. No FX:
everything is in EUR.
"""

from decimal import Decimal

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse, LotTimelineEventSchema
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._scope_boundary_books import (
    L1_ARRIVAL_DAY,
    L1_BUY_DAY,
    L1_DATE_TO,
    L1_DEPARTURE_DAY,
    L1_PRICES,
    L1_SALE_DAY,
    LedgerL1,
    add_prices,
    asset_row,
    link,
    new_asset,
    new_broker,
    new_user,
    seed_l1,
)

D = Decimal
EVENTS = LotAnalysisType.EVENT_HISTORY
GANTT = LotAnalysisType.GANTT_TOPOLOGY
_TRANSFER_KINDS = {"TRANSFER_DEPART", "TRANSFER_ARRIVE"}
# C2: B sends 2 of its 6 units to C on the reading day, which the analysis includes: 150, carried from 15 Jan.
_TO_C_DAY = L1_DATE_TO


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


# --------------------------------------------------------------------------- #
# Readings
# --------------------------------------------------------------------------- #


async def _analysis(session: AsyncSession, user: User, asset: Asset, *, broker_ids: list[int] | None, analyses: list[LotAnalysisType]) -> LotsAnalysisResponse:
    """The lots analysis of ``asset`` for ``user``, read on L1's reading day (16 Jan 2025), in EUR."""
    return await get_lots_analysis(
        session=session,
        user_id=user.id,
        asset_id=asset.id,
        broker_ids=broker_ids,
        date_from=None,
        date_to=L1_DATE_TO,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=analyses,
    )


def _issue_codes(result: LotsAnalysisResponse) -> list[str]:
    """The distinct issue codes of the analysis, sorted."""
    return sorted({str(issue.code) for issue in (result.data_quality.issues if result.data_quality else [])})


def _rows_of(result: LotsAnalysisResponse, transaction_id: int) -> list[LotTimelineEventSchema]:
    """The event history's rows of ``transaction_id``, by date and lot (the asset is the test's own: every row is the test's)."""
    return sorted((row for row in result.lot_events or [] if row.transaction_id == transaction_id), key=lambda row: (row.date, row.lot_id))


def _closure_setting(result: LotsAnalysisResponse, rows: list[LotTimelineEventSchema]) -> dict:
    """What a closure test stands on, green today: the analysis' status and issues, and, for each row, the brokers the
    Gantt draws the fragment it closes at — every segment of that ``fragment_id``, one place."""
    return {
        "status": result.calculation_status,
        "issue codes": _issue_codes(result),
        "brokers of the closed fragments": [{segment.broker_id for segment in result.gantt_segments or [] if segment.fragment_id == row.fragment_id} for row in rows],
    }


def _closure_reading(row: LotTimelineEventSchema) -> dict:
    """What §29 point 2 reads of a closure row: what identifies it, its edge label, and the broker it names."""
    return {
        "lot_id": row.lot_id,
        "transaction_id": row.transaction_id,
        "date": row.date,
        "kind": str(row.kind),
        "quantity": row.quantity,
        "scope_boundary": row.scope_boundary,
        "broker_id": row.broker_id,
    }


def _transfer_rows(result: LotsAnalysisResponse) -> list[tuple]:
    """(kind, date, broker, source, destination) of every transfer row of the event history, by date and kind."""
    rows = [(str(row.kind), row.date, row.broker_id, row.source_broker_id, row.destination_broker_id) for row in result.lot_events or [] if str(row.kind) in _TRANSFER_KINDS]
    return sorted(rows, key=lambda row: (row[1], row[0]))


# --------------------------------------------------------------------------- #
# C1–C2: a lot moved before it closes
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_s29_c1_a_sale_after_a_transfer_names_the_broker_it_sells_from(session):
    """§29 point 2, C1 — RED until the cure. U sees L1 whole (``broker_ids=None``: A and B), so A → B is a real transfer:
    A's lot reaches B on 13 Jan, and B's SELL of 4 on 15 Jan closes them from the fragment the Gantt draws at B. Its row
    names B — kind SELL, 4 units of A's lot, no edge label.

    Today: A, the lot's opening broker.
    """
    book = await seed_l1(session)

    result = await _analysis(session, book.owner, book.asset, broker_ids=None, analyses=[EVENTS, GANTT])

    rows = _rows_of(result, book.sell.id)
    # Precondition, green today (J-10's R3): COMPLETE without issue; the sale closes one fragment, which the Gantt draws at B.
    assert _closure_setting(result, rows) == {"status": "COMPLETE", "issue codes": [], "brokers of the closed fragments": [{book.broker_b.id}]}
    assert [_closure_reading(row) for row in rows] == [
        {"lot_id": book.buy.id, "transaction_id": book.sell.id, "date": L1_SALE_DAY, "kind": "SELL", "quantity": D("4"), "scope_boundary": None, "broker_id": book.broker_b.id},
    ]


@pytest.mark.asyncio
async def test_s29_c2_an_exit_at_the_scope_edge_names_the_broker_the_units_leave(session):
    """§29 point 2, C2 — RED until the cure. L1, plus a broker C of U's and a TRANSFER pair B → C of 2 units on 16 Jan:
    B's leg −2, C's +2 at a cost basis of 100 a unit, linked both ways — same asset, opposite signs, same quantity, so the
    pair pairs back. U reads A and B (``broker_ids=[A, B]``): A → B stays a real transfer, while B's leg, whose partner
    sits at C outside the scope, reads as an ADJUSTMENT-out at the market of 16 Jan (150, carried from 15 Jan) and closes
    2 units of A's lot from the fragment the Gantt draws at B. Its row — ADJUSTMENT_OUT, ``scope_boundary`` OUT — names
    B, the broker the units leave (never C: the partner is never named, R13-SEC7).

    Today: A, the lot's opening broker.
    """
    book = await seed_l1(session)
    broker_c = await new_broker(session, "C", book.owner)
    to_c_out = asset_row(book.broker_b, book.asset, TransactionType.TRANSFER, _TO_C_DAY, "-2")
    to_c_in = asset_row(broker_c, book.asset, TransactionType.TRANSFER, _TO_C_DAY, "2", cost="100")
    session.add_all([to_c_out, to_c_in])
    await session.flush()
    await link(session, to_c_out, to_c_in)

    result = await _analysis(session, book.owner, book.asset, broker_ids=[book.broker_a.id, book.broker_b.id], analyses=[EVENTS, GANTT])

    rows = _rows_of(result, to_c_out.id)
    # Precondition, green today (J-10's R2 and R10): the pair B → C pairs back, so the analysis is COMPLETE without issue
    # (no TRANSFER_PAIR_MISSING), and B's leg closes one fragment, which the Gantt draws at B.
    assert _closure_setting(result, rows) == {"status": "COMPLETE", "issue codes": [], "brokers of the closed fragments": [{book.broker_b.id}]}
    assert [_closure_reading(row) for row in rows] == [
        {"lot_id": book.buy.id, "transaction_id": to_c_out.id, "date": _TO_C_DAY, "kind": "ADJUSTMENT_OUT", "quantity": D("2"), "scope_boundary": "OUT", "broker_id": book.broker_b.id},
    ]


# --------------------------------------------------------------------------- #
# C3–C4: guards
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_s29_c3_guard_a_lot_that_never_moves_names_its_own_broker(session):
    """§29 point 2, C3 — GUARD (green today and after). One broker A of U's, an asset with L1's prices: BUY 10 at 100 on
    10 Jan, SELL 4 at 150 on 15 Jan. The lot never leaves A, so the broker of the fragment the sale closes and the lot's
    opening broker are one: the SELL row names A.
    """
    owner = await new_user(session, "owner")
    broker_a = await new_broker(session, "A", owner)
    asset = await new_asset(session, "s29-c3")
    add_prices(session, asset, L1_PRICES)
    buy = asset_row(broker_a, asset, TransactionType.BUY, L1_BUY_DAY, "10", amount="-1000")
    sell = asset_row(broker_a, asset, TransactionType.SELL, L1_SALE_DAY, "-4", amount="600")
    session.add_all([buy, sell])
    await session.flush()

    result = await _analysis(session, owner, asset, broker_ids=None, analyses=[EVENTS, GANTT])

    rows = _rows_of(result, sell.id)
    assert _closure_setting(result, rows) == {"status": "COMPLETE", "issue codes": [], "brokers of the closed fragments": [{broker_a.id}]}
    assert [_closure_reading(row) for row in rows] == [
        {"lot_id": buy.id, "transaction_id": sell.id, "date": L1_SALE_DAY, "kind": "SELL", "quantity": D("4"), "scope_boundary": None, "broker_id": broker_a.id},
    ]


async def _seed_l1_same_day(session: AsyncSession) -> LedgerL1:
    """L1 with B's leg dated 12 Jan, the day A's leaves: a same-day transfer, which the replay moves without transit."""
    owner = await new_user(session, "owner")
    broker_a = await new_broker(session, "A", owner)
    broker_b = await new_broker(session, "B", owner)
    asset = await new_asset(session, "s29-same-day")
    add_prices(session, asset, L1_PRICES)
    buy = asset_row(broker_a, asset, TransactionType.BUY, L1_BUY_DAY, "10", amount="-1000")
    out_leg = asset_row(broker_a, asset, TransactionType.TRANSFER, L1_DEPARTURE_DAY, "-10")
    in_leg = asset_row(broker_b, asset, TransactionType.TRANSFER, L1_DEPARTURE_DAY, "10", cost="100")
    sell = asset_row(broker_b, asset, TransactionType.SELL, L1_SALE_DAY, "-4", amount="600")
    session.add_all([buy, out_leg, in_leg, sell])
    await session.flush()
    await link(session, out_leg, in_leg)
    return LedgerL1(owner=owner, asset=asset, broker_a=broker_a, broker_b=broker_b, buy=buy, out_leg=out_leg, in_leg=in_leg, sell=sell)


@pytest.mark.asyncio
@pytest.mark.parametrize("transfer", ["in-transit", "same-day"])
async def test_s29_c4_guard_the_transfer_rows_keep_their_brokers(session, transfer):
    """§29 point 2, C4 — GUARD (green today and after): the cure touches the closure rows only. U sees the ledger whole
    (``broker_ids=None``), COMPLETE without issue, and the transfer rows are as ``_build_transfer_rows`` writes them:

    - ``in-transit``, L1 (12 → 13 Jan): both rows are read off the transit fragment — TRANSFER_DEPART on 12 Jan and
      TRANSFER_ARRIVE on 13 Jan name no broker, A as the source and B as the destination;
    - ``same-day``, L1 with B's leg dated 12 Jan: no transit, so the one transfer row is TRANSFER_ARRIVE on 12 Jan, read
      off B's fragment — it names B, with no source or destination.
    """
    book = await seed_l1(session) if transfer == "in-transit" else await _seed_l1_same_day(session)
    a, b = book.broker_a.id, book.broker_b.id

    result = await _analysis(session, book.owner, book.asset, broker_ids=None, analyses=[EVENTS])

    # (kind, date, broker, source, destination)
    expected_rows = {
        "in-transit": [("TRANSFER_DEPART", L1_DEPARTURE_DAY, None, a, b), ("TRANSFER_ARRIVE", L1_ARRIVAL_DAY, None, a, b)],
        "same-day": [("TRANSFER_ARRIVE", L1_DEPARTURE_DAY, b, None, None)],
    }
    assert {"status": result.calculation_status, "issue codes": _issue_codes(result), "transfer rows": _transfer_rows(result)} == {
        "status": "COMPLETE",
        "issue codes": [],
        "transfer rows": expected_rows[transfer],
    }
